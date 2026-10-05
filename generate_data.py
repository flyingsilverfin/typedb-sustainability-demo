"""Generate data.tql from the Trase subset (two-level ownership model)."""
import csv, json
R = list(csv.DictReader(open('palm_kaltim_eu_2022.csv')))
q = json.dumps
SENTINELS = {'NOT REFINED', 'UNKNOWN', 'UNKNOWN AFFILIATION', ''}
L, seen = [], set()
def once(k, s):
    if k not in seen: seen.add(k); L.append(s)

L.append('insert $c isa country, has name "INDONESIA", has trase-id "ID";')
L.append('match $c isa country, has trase-id "ID"; insert $p isa province, has name "KALIMANTAN TIMUR", has trase-id "ID-64"; containment (container: $c, contained: $p);')
L.append('insert $x isa crude-palm-oil, has name "PALM OIL";')
L.append('insert $x isa refined-palm-oil, has name "REFINED PALM OIL";')

exporters = {r['exporter'] for r in R}
operated = {r['refinery'] for r in R if r['refinery'] in exporters}   # name-match inference

# 1. companies: exporters, importers, and every parent (group) value
for r in R:
    for c in ['mill_group', 'refinery_group', 'exporter', 'exporter_group', 'importer', 'importer_group']:
        if r[c] not in SENTINELS: once(('co', r[c]), f'insert $c isa company, has name {q(r[c])};')
# 2. places and facilities
for r in R:
    once(('c', r['country_of_first_import_trase_id']), f'insert $c isa country, has name {q(r["country_of_first_import"])}, has trase-id {q(r["country_of_first_import_trase_id"])};')
    once(('k', r['kabupaten_of_production_trase_id']), f'match $p isa province, has trase-id "ID-64"; insert $k isa kabupaten, has name {q(r["kabupaten_of_production"])}, has trase-id {q(r["kabupaten_of_production_trase_id"])}; containment (container: $p, contained: $k);')
    once(('m', r['mill_trase_id']), f'insert $m isa mill, has name {q(r["mill"])}, has trase-id {q(r["mill_trase_id"])};')
    if r['refinery'] not in SENTINELS:
        once(('r', r['refinery_trase_id']), f'insert $m isa refinery, has name {q(r["refinery"])}, has trase-id {q(r["refinery_trase_id"])};')
    once(('p', r['port_of_export']), f'insert $p isa port, has name {q(r["port_of_export"])};')
# 3. ownership (Trase groups) and operation (inferred)
for r in R:
    links = [('mill', r['mill_trase_id'], r['mill_group'])]
    if r['refinery'] not in SENTINELS:
        if r['refinery'] in operated:
            # level 2: refinery -> operating company; its group is then derived via the company
            once(('op', r['refinery_trase_id']), f'match $f isa refinery, has trase-id {q(r["refinery_trase_id"])}; $c isa company, has name {q(r["refinery"])}; insert operation (operator: $c, facility: $f), has basis "name-match";')
        else:
            links.append(('refinery', r['refinery_trase_id'], r['refinery_group']))
    links += [('company', r['exporter'], r['exporter_group']), ('company', r['importer'], r['importer_group'])]
    for kind, ident, grp in links:
        if grp in SENTINELS or (kind == 'company' and ident == grp): continue   # no parent / self-group
        sub = f'$s isa company, has name {q(ident)}' if kind == 'company' else f'$s isa {kind}, has trase-id {q(ident)}'
        once(('own', kind, ident), f'match {sub}; $g isa company, has name {q(grp)}; insert ownership (parent: $g, subsidiary: $s), has basis "trase-group";')
# 4. flows
for r in R:
    ref = r['refinery'] not in SENTINELS
    m = (f'match $o isa kabupaten, has trase-id {q(r["kabupaten_of_production_trase_id"])}; $m isa mill, has trase-id {q(r["mill_trase_id"])}; '
         + (f'$r isa refinery, has trase-id {q(r["refinery_trase_id"])}; ' if ref else '')
         + f'$e isa company, has name {q(r["exporter"])}; $p isa port, has name {q(r["port_of_export"])}; $i isa company, has name {q(r["importer"])}; '
         + f'$d isa country, has trase-id {q(r["country_of_first_import_trase_id"])}; $c isa commodity, has name {q(r["product_type"])}; ')
    roles = 'origin: $o, mill: $m, ' + ('refinery: $r, ' if ref else '') + 'exporter: $e, port: $p, importer: $i, destination: $d, commodity: $c'
    L.append(m + f'insert $f isa trade-flow, links ({roles}), has year {r["year"]}, has volume-t {float(r["volume"] or 0)}, '
             f'has fob-usd {float(r["fob"] or 0)}, has deforestation-ha {float(r["palm_oil_deforestation_10_year_total_exposure"] or 0)};')
open('data.tql', 'w').write('\n'.join(L) + '\n')
print(len(L), 'statements;', sum('insert ownership' in l for l in L), 'ownership;', sum('insert operation' in l for l in L), 'operation;', sum(l.startswith('insert $c isa company') for l in L), 'companies')
