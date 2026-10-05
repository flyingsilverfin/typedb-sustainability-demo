import time,sys
from typedb.driver import TypeDB, Credentials, DriverOptions, TransactionType
from typedb.api.connection.driver_tls_config import DriverTlsConfig
DB="er2026_palm_scratch"
d=TypeDB.driver("localhost:1729", Credentials("admin","password"), DriverOptions(DriverTlsConfig.disabled()))
if d.databases.contains(DB): d.databases.get(DB).delete()
d.databases.create(DB)
with d.transaction(DB, TransactionType.SCHEMA) as tx:
    tx.query(open('schema.tql').read()).resolve(); tx.commit()
t=time.time()
with d.transaction(DB, TransactionType.WRITE) as tx:
    for i,l in enumerate(open('data.tql')):
        try: tx.query(l).resolve()
        except Exception as e: print('FAIL line',i+1,l[:200],e); sys.exit(1)
    tx.commit()
print('loaded in %.1fs'%(time.time()-t))
