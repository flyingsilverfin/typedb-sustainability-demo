import sys
from typedb.driver import TypeDB, Credentials, DriverOptions, TransactionType
from typedb.api.connection.driver_tls_config import DriverTlsConfig
DB="er2026_palm_scratch"
d=TypeDB.driver("localhost:1729", Credentials("admin","password"), DriverOptions(DriverTlsConfig.disabled()))
def run(q, kind="read", limit=12, commit=False):
    tt={"read":TransactionType.READ,"write":TransactionType.WRITE,"schema":TransactionType.SCHEMA}[kind]
    print("="*70); print(q.strip()); print("-"*30)
    try:
        with d.transaction(DB, tt) as tx:
            a=tx.query(q).resolve()
            if a.is_concept_documents():
                docs=list(a.as_concept_documents()); print(len(docs),"docs"); [print(x) for x in docs[:limit]]
            elif a.is_concept_rows():
                rows=list(a.as_concept_rows()); print(len(rows),"rows")
                for r in rows[:limit]:
                    out={}
                    for c in r.column_names():
                        v=r.get(c)
                        try:
                            if v.is_attribute() or v.is_value(): out[c]=v.get_value() if v.is_value() else v.get_value()
                            elif v.is_type(): out[c]=v.get_label()
                            else: out[c]=str(v.get_type().get_label())
                        except Exception as e: out[c]=str(v)
                    print(out)
            else: print("ok")
            if commit: tx.commit(); print("COMMITTED")
    except Exception as e: print("ERROR:", str(e)[:600])
for q in open(sys.argv[1]).read().split("\n#---\n"):
    if q.strip():
        kind="read"; commit=False
        if q.startswith("#write"): kind="write"; commit=True
        if q.startswith("#schema"): kind="schema"; commit=True
        if q.startswith("#nocommit"): kind="write"
        run(q, kind, commit=commit)
