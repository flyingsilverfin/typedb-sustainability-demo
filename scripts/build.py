"""Generate the derived tutorial files from their sources.

  schema/full-schema.tql  <- the tutorial snippets, merged into a single `define` query
  data/insert-data.tql    <- data/palm_kaltim_eu_2022_demo.csv, as a single `insert` query

Run from anywhere:  python3 scripts/build.py
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The snippets that make up the final model, in tutorial order.
# Discussion-only alternatives (option 1, the commodity challenge) are deliberately excluded.
SCHEMA_SNIPPETS = [
    "schema/01-places.tql",
    "schema/02-places-containment.tql",
    "schema/03b-option-2-companies-facilities.tql",
    "schema/04-company-ownership.tql",
    "schema/05a-commodities.tql",
    "schema/06-trade-flow.tql",
]
FULL_SCHEMA = "schema/full-schema.tql"
DATA_CSV = "data/palm_kaltim_eu_2022_demo.csv"
DATA_INSERT = "data/insert-data.tql"

NOT_REFINED = "NOT REFINED"


def build_full_schema() -> str:
    # A query can only contain one `define`, so strip each snippet's own `define` line.
    parts = ["define"]
    for path in SCHEMA_SNIPPETS:
        body = [line for line in (ROOT / path).read_text().splitlines() if line.strip() != "define"]
        parts.append("")
        parts.append("\n".join(body).strip("\n"))
    return "\n".join(parts) + "\n"


def var(prefix: str, name: str) -> str:
    return "$" + prefix + "_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def build_insert() -> str:
    rows = list(csv.DictReader((ROOT / DATA_CSV).open()))
    q = json.dumps
    lines, seen = [], set()

    def once(key, statement):
        if key not in seen:
            seen.add(key)
            lines.append(statement)

    lines.append("insert\n\n## Places ##")
    for r in rows:
        for c in (r["country_of_production"], r["country_of_first_import"]):
            once(("country", c), f'{var("country", c)} isa country, has country_name {q(c)};')
    for r in rows:
        p = r["province_of_production"]
        once(("prov", p), f'{var("prov", p)} isa province, has province_name {q(p)};')
    for r in rows:
        k = r["kabupaten_of_production"]
        once(("kab", k), f'{var("kab", k)} isa kabupaten, has kabupaten_name {q(k)};')

    lines.append("\n## Containment ##")
    for r in rows:
        once(("in", "prov", r["province_of_production"]),
             f'containment (parent: {var("country", r["country_of_production"])}, '
             f'child: {var("prov", r["province_of_production"])});')
    for r in rows:
        once(("in", "kab", r["kabupaten_of_production"]),
             f'containment (parent: {var("prov", r["province_of_production"])}, '
             f'child: {var("kab", r["kabupaten_of_production"])});')

    lines.append("\n## Commodities ##")
    for r in rows:
        c = r["product_type"]
        once(("com", c), f'{var("com", c)} isa commodity, has commodity_name {q(c)};')

    lines.append("\n## Companies ##")
    for r in rows:
        for col in ("mill_group", "refinery_group", "exporter", "exporter_group", "importer", "importer_group"):
            v = r[col]
            if v != NOT_REFINED:
                once(("co", v), f'{var("co", v)} isa company, has company_name {q(v)};')

    lines.append("\n## Facilities ##")
    for r in rows:
        once(("mill", r["mill"]), f'{var("mill", r["mill"])} isa mill, has facility_name {q(r["mill"])};')
    for r in rows:
        if r["refinery"] != NOT_REFINED:
            once(("ref", r["refinery"]), f'{var("ref", r["refinery"])} isa refinery, has facility_name {q(r["refinery"])};')

    exporters = {r["exporter"] for r in rows}
    lines.append("\n## Ownership ##")
    for r in rows:
        once(("own", "mill", r["mill"]),
             f'ownership (owner: {var("co", r["mill_group"])}, owned: {var("mill", r["mill"])});')
    for r in rows:
        refinery = r["refinery"]
        if refinery == NOT_REFINED:
            continue
        # A refinery sharing its name with an exporter is read as owned by that company,
        # which in turn is owned by the group (see the tutorial, "companies & facilities").
        owner = refinery if refinery in exporters else r["refinery_group"]
        once(("own", "ref", refinery), f'ownership (owner: {var("co", owner)}, owned: {var("ref", refinery)});')
    for r in rows:
        for company, group in (("exporter", "exporter_group"), ("importer", "importer_group")):
            if r[company] != r[group]:   # group == company means no parent recorded
                once(("own", "co", r[company]),
                     f'ownership (owner: {var("co", r[group])}, owned: {var("co", r[company])});')

    lines.append("\n## Trade flows ##")
    for r in rows:
        roles = [f'origin: {var("kab", r["kabupaten_of_production"])}', f'mill: {var("mill", r["mill"])}']
        if r["refinery"] != NOT_REFINED:
            roles.append(f'refiner: {var("ref", r["refinery"])}')
        roles += [
            f'exporter: {var("co", r["exporter"])}',
            f'importer: {var("co", r["importer"])}',
            f'destination: {var("country", r["country_of_first_import"])}',
            f'commodity: {var("com", r["product_type"])}',
        ]
        volume = round(float(r["volume"]), 3)
        deforestation = round(float(r["palm_oil_deforestation_10_year_total_exposure"]), 4)
        usd = f'{float(r["fob"]):.2f}dec'
        lines.append(f'trade_flow ({", ".join(roles)}),\n'
                     f'  has volume_tonnes {volume}, has deforestation_ha {deforestation}, has usd {usd};')
    return "\n".join(lines) + "\n"


def main():
    (ROOT / FULL_SCHEMA).write_text(build_full_schema())
    (ROOT / DATA_INSERT).write_text(build_insert())
    print(f"wrote {FULL_SCHEMA} and {DATA_INSERT}")


if __name__ == "__main__":
    main()
