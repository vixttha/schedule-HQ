"""Bounded private local reference store; not a scheduler lease or a distributed database.

Caller supplies a trusted, private, durable directory outside a public worktree.
The lock serializes cooperating local writers only. Never auto-reclaim it.
"""
import hashlib,json,os,tempfile
from contextlib import contextmanager
from pathlib import Path
from schedule_hq.contracts.validation import keys,require,unique,bad_constant
from schedule_hq.history.events import canonical,event_key,event_digest,ingest,validate_event,IDENT
from schedule_hq.policy.reporting import fingerprint
from schedule_hq.contracts.validation import TASKS,timestamp,SHA,safe_text
from schedule_hq.policy.authority import may_publish
from schedule_hq.policy.intent import assess

MAX_SNAPSHOT=8*1024*1024

def digest(data):
    return hashlib.sha256(canonical(data)).hexdigest()

class History:
    def __init__(self,root,repository_id,installation):
        require(type(repository_id) is int and 1<=repository_id<=9007199254740991,"invalid scope")
        require(type(installation) is str and IDENT.fullmatch(installation) is not None,"invalid scope")
        root=Path(root)
        require(root.is_dir() and not root.is_symlink(),"private directory required")
        self.root=root.resolve()
        require(not any((p/".git").exists() for p in (self.root,*self.root.parents)),"private history outside worktree required")
        if os.name!="nt":
            require(self.root.stat().st_mode & 0o077==0,"private directory permissions required")
        self.repo=repository_id;self.installation=installation
        self.path=self.root/"history.json";self.lock=self.root/"history.lock"

    def empty(self):
        return {"schema_version":1,"repository_id":self.repo,"installation":self.installation,"events":[],"binding":None,"delivery":{},"writes":[]}
    def _scope(self,e):
        require(e["repository_id"]==self.repo and e["installation"]==self.installation,"history scope mismatch")
    def _encode(self,data):
        return canonical(data|{"snapshot_digest":digest(data)})
    def _decode(self,payload):
        try:
            require(type(payload) is bytes and len(payload)<=MAX_SNAPSHOT,"snapshot size")
            data=json.loads(payload.decode("utf-8"),object_pairs_hook=unique,parse_constant=bad_constant)
            keys(data,{"schema_version","repository_id","installation","events","binding","delivery","writes","snapshot_digest"})
            checksum=data.pop("snapshot_digest")
            require(checksum==digest(data),"snapshot digest mismatch")
            require(type(data["schema_version"]) is int and data["schema_version"]==1,"unknown snapshot schema")
            require(type(data["repository_id"]) is int and data["repository_id"]==self.repo and data["installation"]==self.installation,"snapshot scope mismatch")
            require(type(data["events"]) is list,"invalid events")
            seen=set();run_slots={}
            for row in data["events"]:
                keys(row,{"key","digest","event"})
                e=row["event"];validate_event(e);self._scope(e)
                k=event_key(e)
                require(k not in seen and row["key"]==k and row["digest"]==event_digest(e),"invalid event record")
                seen.add(k)
                self._check_run_slot(e,run_slots)
            self._validate_delivery(data)
            self._validate_writes(data)
            return data
        except (ValueError,TypeError,OverflowError,RecursionError):
            raise ValueError("invalid private history") from None

    def _read(self):
        require(not self.path.is_symlink(),"unsafe history path")
        if not self.path.exists():return self.empty()
        require(self.path.is_file(),"unsafe history path")
        if os.name!="nt":require(self.path.stat().st_mode & 0o077==0,"private file permissions required")
        with self.path.open("rb") as f:return self._decode(f.read(MAX_SNAPSHOT+1))

    @contextmanager
    def _exclusive(self):
        try:self.lock.mkdir(mode=0o700)
        except FileExistsError:raise RuntimeError("local writer busy or unresolved lock; no auto-reclaim") from None
        try:yield
        finally:self.lock.rmdir()

    def _write(self,data):
        payload=self._encode(data)
        require(len(payload)<=MAX_SNAPSHOT,"private history size limit")
        require(not self.path.is_symlink(),"unsafe history path")
        fd,name=tempfile.mkstemp(prefix=".history-",dir=self.root)
        try:
            with os.fdopen(fd,"wb") as f:
                f.write(payload);f.flush();os.fsync(f.fileno())
            os.replace(name,self.path)
            if os.name!="nt":
                d=os.open(self.root,os.O_RDONLY)
                try:os.fsync(d)
                finally:os.close(d)
        finally:
            if os.path.exists(name):os.unlink(name)

    def append(self,event,*,authenticated=False):
        # Authentication flag is a trusted caller boundary, not a credential.
        e=ingest(canonical(event),authenticated=authenticated);self._scope(e)
        k=event_key(e);d=event_digest(e)
        with self._exclusive():
            data=self._read()
            run_slots={}
            for row in data["events"]:
                self._check_run_slot(row["event"],run_slots)
                if row["key"]==k:
                    require(row["digest"]==d,"conflicting observation")
                    return "DUPLICATE"
            self._check_run_slot(e,run_slots)
            data["events"].append({"key":k,"digest":d,"event":e})
            self._write(data)
            return "ADDED"

    def events(self):
        return [r["event"] for r in self._read()["events"]]

    def export_private(self):
        """Explicit private export. Never upload as a public artifact."""
        return self._encode(self._read())

    def restore_empty(self,payload):
        """Validate before writing; refuse to overwrite any existing snapshot."""
        data=self._decode(payload)
        with self._exclusive():
            require(not self.path.exists() and not self.path.is_symlink(),"restore requires empty destination")
            self._write(data)

    def _record(self,e,binding,ack=None):
        key=event_key(e)
        return {"event_key":key,"intent":digest([self.repo,self.installation,binding,key]),
                "fingerprint":fingerprint(e["receipt"]),"observed_at":e["observed_at"],"ack":ack}

    def _validate_delivery(self,data):
        binding=data["binding"];delivery=data["delivery"]
        require(binding is None or (type(binding) is str and IDENT.fullmatch(binding) is not None),"invalid binding")
        require(type(delivery) is dict and set(delivery)<=set(TASKS),"invalid delivery state")
        require(binding is not None or not delivery,"missing binding")
        events={row["key"]:row["event"] for row in data["events"]}
        for task,state in delivery.items():
            keys(state,{"pending","last","highwater"})
            for field in ("pending","last","highwater"):
                record=state[field]
                if record is None:continue
                keys(record,{"event_key","intent","fingerprint","observed_at","ack"})
                k=record["event_key"];require(type(k) is str and k in events,"missing delivery event")
                e=events[k]
                require(e["receipt"]["task_id"]==task and e["provenance"]=="authenticated","invalid delivery event")
                ack=record["ack"]
                require(ack is None if field!="last" else type(ack) is str and IDENT.fullmatch(ack) is not None,"invalid delivery acknowledgment")
                require(record==self._record(e,binding,ack),"invalid delivery record")
            high=state["highwater"]
            require(high is not None,"missing observation highwater")
            if state["last"]:
                require(timestamp(high["observed_at"])>=timestamp(state["last"]["observed_at"]),"stale highwater")
            if state["pending"]:
                require(state["pending"]==high,"pending differs from highwater")
                if state["last"]:
                    require(timestamp(high["observed_at"])>timestamp(state["last"]["observed_at"]),"stale pending delivery")

    def prepare_delivery(self,key,binding,*,associated=False,delivery_supported=False,readback_supported=False,observation_verified=False):
        # Caller must independently verify the exact event and association with the actual host.
        if not all(v is True for v in (associated,delivery_supported,readback_supported,observation_verified)):
            return {"decision":"BLOCKED"}
        if type(binding) is not str or IDENT.fullmatch(binding) is None or type(key) is not str:
            return {"decision":"BLOCKED"}
        with self._exclusive():
            data=self._read()
            if data["binding"] not in (None,binding):return {"decision":"BLOCKED"}
            e=next((row["event"] for row in data["events"] if row["key"]==key),None)
            if e is None or e["provenance"]!="authenticated":return {"decision":"BLOCKED"}
            task=e["receipt"]["task_id"]
            state=data["delivery"].get(task,{"pending":None,"last":None,"highwater":None})
            if state["pending"] is not None:return {"decision":"BLOCKED"}
            record=self._record(e,binding)
            last=state["last"];high=state["highwater"]
            if high:
                if timestamp(record["observed_at"])<timestamp(high["observed_at"]):return {"decision":"STALE"}
                if timestamp(record["observed_at"])==timestamp(high["observed_at"]) and record!=high:return {"decision":"BLOCKED"}
            if last and record["fingerprint"]==last["fingerprint"]:
                if high!=record:
                    state["highwater"]=record;self._write(data)
                return {"decision":"SUPPRESS"}
            if last and timestamp(record["observed_at"])<=timestamp(last["observed_at"]):return {"decision":"STALE"}
            data["binding"]=binding;state["pending"]=record;state["highwater"]=record;data["delivery"][task]=state
            self._write(data)
            return {"decision":"REPORT","intent":record["intent"]}

    def ack_delivery(self,intent,binding,ack,*,verified=False):
        # An actual adapter must verify that the acknowledgment identifies this exact intent and binding.
        require(verified is True and type(intent) is str and type(binding) is str and type(ack) is str and IDENT.fullmatch(ack) is not None,"unverified acknowledgment")
        with self._exclusive():
            data=self._read()
            require(data["binding"]==binding,"delivery binding mismatch")
            for state in data["delivery"].values():
                last=state["last"];pending=state["pending"]
                if last and last["intent"]==intent:
                    require(last["ack"]==ack,"conflicting acknowledgment")
                    return "DUPLICATE"
                if pending and pending["intent"]==intent:
                    require(not any(s["last"] and s["last"]["ack"]==ack for s in data["delivery"].values()),"acknowledgment already used")
                    state["last"]=pending|{"ack":ack};state["pending"]=None
                    self._write(data);return "ACKNOWLEDGED"
            raise ValueError("unknown delivery intent")

    @staticmethod
    def _check_run_slot(e,seen):
        r=e["receipt"];key=(e["provider"],r["task_id"],e["run_id"])
        slot=r["scheduled_at"]
        require(key not in seen or seen[key]==slot,"contradictory host run slot")
        seen[key]=slot

    def _validate_writes(self,data):
        rows=data["writes"];require(type(rows) is list,"invalid write journal")
        prior=0
        for index,row in enumerate(rows):
            keys(row,{"token","intent","state"})
            i=row["intent"]
            keys(i,{"repository_id","issue","actor","before","expected","fence"})
            require(type(i["repository_id"]) is int and i["repository_id"]==self.repo,"journal scope")
            require(type(i["issue"]) is int and i["issue"]>0 and type(i["fence"]) is int and i["fence"]>prior,"journal fence")
            require(safe_text(i["actor"]),"invalid actor")
            require(all(type(i[k]) is str and SHA.fullmatch(i[k]) is not None for k in ("before","expected")) and i["before"]!=i["expected"],"invalid journal revisions")
            require(row["token"]==digest([self.installation,i]),"journal token mismatch")
            require(row["state"] in ("PENDING","APPLIED") and (row["state"]!="PENDING" or index==len(rows)-1),"invalid journal state")
            prior=i["fence"]

    def prepare_write(self,authority,*,expected):
        """Persist intent only; never issue, extend, or claim a host lease or perform a Git write."""
        require(type(authority) is dict and type(expected) is str and SHA.fullmatch(expected) is not None,"invalid write request")
        try:allowed=may_publish(**authority)
        except (TypeError,ValueError):allowed=False
        require(allowed and authority["repository_id"]==self.repo and safe_text(authority["authenticated_actor"]),"write not authorized")
        require(authority["head"]!=expected,"no-op intent")
        intent={"repository_id":self.repo,"issue":authority["issue"],"actor":authority["authenticated_actor"],
                "before":authority["head"],"expected":expected,"fence":authority["fence"]}
        token=digest([self.installation,intent])
        with self._exclusive():
            data=self._read();rows=data["writes"]
            if rows:
                require(rows[-1]["state"]=="APPLIED","unresolved intent; no automatic retry")
                require(intent["fence"]>rows[-1]["intent"]["fence"],"stale or reused fence")
                require(intent["before"]==rows[-1]["intent"]["expected"],"journal revision drift; owner reconciliation required")
            rows.append({"token":token,"intent":intent,"state":"PENDING"})
            self._write(data);return token

    def reconcile_write(self,token,authority,*,observed,observation_verified=False,intent_verified=False):
        """Readback classification. Only independently verified exact application settles the journal."""
        with self._exclusive():
            data=self._read()
            row=next((r for r in data["writes"] if r["token"]==token),None)
            if row is None:return "BLOCKED"
            outcome=assess(row["intent"],authority,observed=observed,
                           observation_verified=observation_verified,intent_verified=intent_verified)
            if row["state"]=="APPLIED":
                return "ALREADY_APPLIED" if outcome=="ALREADY_APPLIED" else "BLOCKED"
            if outcome=="ALREADY_APPLIED":
                row["state"]="APPLIED";self._write(data)
            return outcome
