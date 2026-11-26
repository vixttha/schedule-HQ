"""Bounded synthetic storage comparison, not a production storage adapter."""
import argparse,json,os,platform,sqlite3,subprocess,tempfile,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

def rows(n):
    return [(f"i{i:03d}-t{t}",f"synthetic-{i:03d}-{t}") for i in range(n) for t in range(5)]
def encode(data):
    return json.dumps(data,sort_keys=True,separators=(",",":")).encode("ascii")
def json_write(path,data):
    tmp=path.with_suffix(".tmp")
    with tmp.open("wb") as f:
        f.write(encode(data));f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
def json_add(path,key,value):
    data=json.loads(path.read_bytes()) if path.exists() else {}
    if key in data:
        if data[key]!=value:raise ValueError("conflicting row")
        return "DUPLICATE"
    data[key]=value;json_write(path,data);return "ADDED"
def json_case(path,items):
    before=time.perf_counter()
    for k,v in items:
        assert json_add(path,k,v)=="ADDED"
    elapsed=time.perf_counter()-before
    snapshot=path.read_bytes();read=json.loads(snapshot)
    assert read==dict(items)
    k,v=items[0]
    assert json_add(path,k,v)=="DUPLICATE"
    try:json_add(path,k,"changed")
    except ValueError:pass
    else:raise AssertionError("conflict accepted")
    assert path.read_bytes()==snapshot
    tmp=path.with_suffix(".tmp");tmp.write_bytes(b'{"interrupted":')
    assert path.read_bytes()==snapshot
    tmp.unlink()
    restored=path.with_name(path.name+".backup");restored.write_bytes(snapshot)
    assert json.loads(restored.read_bytes())==read
    restored.write_bytes(b'{"invalid":')
    try:json_add(restored,"new","value")
    except ValueError:pass
    else:raise AssertionError("corrupt snapshot accepted")
    return {"backend":"json-snapshot","rows":len(items),"write_seconds":elapsed,"bytes":len(snapshot),
            "scope":"single writer; interrupted temporary file and restore checked; concurrent writers not supported"}
def sqlite_case(path,items):
    before=time.perf_counter()
    db=sqlite3.connect(path)
    try:
        db.execute("CREATE TABLE history (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        for k,v in items:
            db.execute("INSERT INTO history VALUES (?,?)",(k,v));db.commit()
        elapsed=time.perf_counter()-before
        assert dict(db.execute("SELECT id,payload FROM history"))==dict(items)
        k,v=items[0]
        try:db.execute("INSERT INTO history VALUES (?,?)",(k,"changed"))
        except sqlite3.IntegrityError:db.rollback()
        else:raise AssertionError("conflict accepted")
        assert db.execute("SELECT payload FROM history WHERE id=?",(k,)).fetchone()==(v,)
        db.execute("INSERT INTO history VALUES (?,?)",("interrupted","x"));db.rollback()
        assert db.execute("SELECT COUNT(*) FROM history").fetchone()==(len(items),)
        other=sqlite3.connect(path,timeout=0.05)
        try:
            db.execute("BEGIN IMMEDIATE")
            try:
                try:other.execute("INSERT INTO history VALUES (?,?)",("race","x"))
                except sqlite3.OperationalError as e:assert "locked" in str(e).lower()
                else:raise AssertionError("concurrent writer not blocked")
            finally:db.rollback()
        finally:other.close()
        restored=sqlite3.connect(path.with_name(path.name+".backup"))
        try:
            db.backup(restored)
            assert dict(restored.execute("SELECT id,payload FROM history"))==dict(items)
        finally:restored.close()
        corrupt=path.with_name(path.name+".corrupt");corrupt.write_bytes(b"not a database")
        bad=sqlite3.connect(corrupt)
        try:
            try:bad.execute("SELECT name FROM sqlite_master").fetchall()
            except sqlite3.DatabaseError:pass
            else:raise AssertionError("corrupt database accepted")
        finally:bad.close()
    finally:db.close()
    return {"backend":"sqlite-local","rows":len(items),"write_seconds":elapsed,"bytes":path.stat().st_size,
            "scope":"local serialized writers, unique constraint, rollback and backup checked; not a distributed lease"}
def pg(sql,check=True):
    return subprocess.run(["sudo","-u","postgres","psql","-X","-qAt","-v","ON_ERROR_STOP=1","-d","postgres"],
                          input=sql,text=True,capture_output=True,check=check,timeout=60)
def postgres_case(items):
    # Only runner-local PostgreSQL, unique disposable fixture schema, no external infrastructure.
    assert all(k.replace("-","").isalnum() and v.replace("-","").isalnum() for k,v in items)
    schema="shq_study_"+uuid4().hex
    table=schema+".history";restored=schema+".restored"
    pg(f"CREATE SCHEMA {schema}; CREATE TABLE {table} (id text PRIMARY KEY,payload text NOT NULL);")
    try:
        statements=""
        for k,v in items:statements+=f"BEGIN; INSERT INTO {table} VALUES ('{k}','{v}'); COMMIT;\n"
        before=time.perf_counter();pg(statements);elapsed=time.perf_counter()-before
        pg(f"BEGIN; INSERT INTO {table} VALUES ('interrupted','x'); ROLLBACK;")
        k,v=items[0]
        assert pg(f"INSERT INTO {table} VALUES ('{k}','changed') ON CONFLICT DO NOTHING RETURNING payload;").stdout.strip()==""
        def contents(name):
            return dict(line.split("|",1) for line in pg(f"SELECT id||'|'||payload FROM {name} ORDER BY id;").stdout.splitlines())
        assert contents(table)==dict(items)
        def compete(payload):
            return pg(f"INSERT INTO {table} VALUES ('race','{payload}') ON CONFLICT DO NOTHING RETURNING payload;").stdout.strip()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(compete,("a","b")))
        assert sum(bool(x) for x in results)==1 and contents(table)["race"] in ("a","b")
        pg(f"DELETE FROM {table} WHERE id='race';")
        backup=pg(f"COPY (SELECT id,payload FROM {table} ORDER BY id) TO STDOUT WITH (FORMAT csv);").stdout
        pg(f"CREATE TABLE {restored} (LIKE {table} INCLUDING ALL); COPY {restored} FROM STDIN WITH (FORMAT csv);\n"+backup+"\\.\n")
        assert contents(restored)==dict(items)
        corrupt=pg(f"BEGIN; COPY {restored} FROM STDIN WITH (FORMAT csv);\nmalformed\n\\.\nCOMMIT;\n",check=False)
        assert corrupt.returncode!=0 and contents(restored)==dict(items)
        return {"backend":"postgresql-runner-local","rows":len(items),"seconds_including_process_and_query":elapsed,
                "scope":"disposable runner-local schema; separate-process race, uniqueness, rollback, CSV restore and malformed import checked; timing not equivalent"}
    finally:pg(f"DROP SCHEMA {schema} CASCADE;")
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--postgres",action="store_true")
    parser.add_argument("--output",required=True)
    args=parser.parse_args();results=[]
    with tempfile.TemporaryDirectory() as d:
        for n in (1,5,10,100):
            items=rows(n)
            for fn,suffix in ((json_case,"json"),(sqlite_case,"db")):
                results.append({"installations":n,**fn(Path(d)/f"{n}.{suffix}",items)})
            if args.postgres:results.append({"installations":n,**postgres_case(items)})
    report={"scope":"synthetic local qualification; no production recommendation from timing alone",
            "platform":platform.platform(),"python":platform.python_version(),"sqlite":sqlite3.sqlite_version,
            "postgres":pg("SELECT version();").stdout.strip() if args.postgres else "NOT RUN","results":results}
    Path(args.output).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report))
if __name__=="__main__":main()
