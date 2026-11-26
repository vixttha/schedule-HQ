"""Bounded synthetic storage comparison, not a production storage adapter."""
import argparse,json,os,platform,sqlite3,subprocess,tempfile,time
from pathlib import Path

def rows(n):
    return [(f"i{i:03d}-t{t}",f"synthetic-{i:03d}-{t}") for i in range(n) for t in range(5)]
def encode(data):
    return json.dumps(data,sort_keys=True,separators=(",",":")).encode("ascii")
def json_write(path,data):
    tmp=path.with_suffix(".tmp")
    with tmp.open("wb") as f:
        f.write(encode(data));f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
def json_case(path,items):
    before=time.perf_counter();data={}
    for k,v in items:
        data[k]=v;json_write(path,data)
    elapsed=time.perf_counter()-before
    snapshot=path.read_bytes();read=json.loads(snapshot)
    assert read==dict(items)
    k,v=items[0]
    assert read[k]==v and read[k]!="changed"
    tmp=path.with_suffix(".tmp");tmp.write_bytes(b'{"interrupted":')
    assert path.read_bytes()==snapshot
    tmp.unlink()
    restored=path.with_name(path.name+".backup");restored.write_bytes(snapshot)
    assert json.loads(restored.read_bytes())==read
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
    finally:db.close()
    return {"backend":"sqlite-local","rows":len(items),"write_seconds":elapsed,"bytes":path.stat().st_size,
            "scope":"local serialized writers, unique constraint, rollback and backup checked; not a distributed lease"}
def pg(sql):
    return subprocess.run(["sudo","-u","postgres","psql","-X","-qAt","-v","ON_ERROR_STOP=1","-d","postgres"],
                          input=sql,text=True,capture_output=True,check=True)
def postgres_case(items):
    assert all(k.replace("-","").isalnum() and v.replace("-","").isalnum() for k,v in items)
    statements="CREATE TEMP TABLE shq_history (id text PRIMARY KEY,payload text NOT NULL);\n"
    for k,v in items:statements+=f"BEGIN; INSERT INTO shq_history VALUES ('{k}','{v}'); COMMIT;\n"
    statements+="BEGIN; INSERT INTO shq_history VALUES ('interrupted','x'); ROLLBACK;\n"
    k,v=items[0]
    statements+=f"INSERT INTO shq_history VALUES ('{k}','changed') ON CONFLICT DO NOTHING;\n"
    statements+="SELECT id||'|'||payload FROM shq_history ORDER BY id;\n"
    before=time.perf_counter();result=pg(statements);elapsed=time.perf_counter()-before
    assert dict(line.split("|",1) for line in result.stdout.splitlines())==dict(items)
    return {"backend":"postgresql-runner-local","rows":len(items),"seconds_including_process_and_query":elapsed,
            "scope":"temporary SQL table; uniqueness and rollback checked; concurrent process/restore NOT RUN; timing not equivalent"}
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
