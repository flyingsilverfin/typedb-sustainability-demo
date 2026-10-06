# Building Executable ER Models with TypeDB (ER 2026 tutorial)

Materials for the ER 2026 tutorial *Building Executable Entity-Relationship Models*:
an executable ER model of a palm oil supply chain, built step by step in TypeDB.

**Tutorial page:** served from this repository with GitHub Pages (`index.html`).

## Layout

| Path | What |
|---|---|
| `index.html`, `assets/` | The tutorial web page (static, no build step) |
| `schema/01-…05-*.tql` | The schema snippets, in tutorial order |
| `schema/02a-…`, `schema/04c-…` | Discussion-only alternatives (not part of the final model) |
| `schema/full-schema.tql` | **Generated**: snippets 1–5 merged into one `define` |
| `data/palm_kaltim_eu_2022_demo.csv` | The 81-row data excerpt |
| `data/insert-data.tql` | **Generated**: the excerpt as one `insert` query |
| `diagrams/*.svg` | ER diagrams shown on the page |
| `scripts/build.py` | Regenerates the two generated files |

The page loads the `.tql`, `.svg` and `.csv` files directly, so editing a snippet updates the page.
After editing a snippet or the CSV, run:

```sh
python3 scripts/build.py
```

## Preview locally

The page fetches files, so it needs a web server rather than `file://`:

```sh
python3 -m http.server 8080   # then open http://localhost:8080
```

## Publish

Settings → Pages → *Deploy from a branch* → `main` / root. The `.nojekyll` file makes GitHub serve the files as-is.

## Data

Benedict, J. J., Biddle, H., Gollnow, F., Heilmayr, R., Mueller, C., Ribeiro, V., & Suavet, C. (2024).
*Indonesia palm oil supply chain (2018–2022)* (Version 1.2) [Data set]. Trase. https://doi.org/10.48650/X83N-7M36

Licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The excerpt keeps 16 of the original columns and
81 rows (2022, East Kalimantan → EU); values are unchanged in the CSV and rounded in `insert-data.tql`.
Trase flows are modelled, not observed shipments.
