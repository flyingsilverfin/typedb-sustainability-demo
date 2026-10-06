// Fills the page from the repository's own files, so the page and the repo never drift apart:
//   <div data-code="schema/01-places.tql">  -> highlighted TypeQL with copy + raw-file link
//   <figure data-svg="diagrams/places.svg">  -> inline SVG (inherits the page's colours)
//   <div data-csv="data/....csv">            -> scrollable table

const BRANCH = "main";

// On GitHub Pages (https://<owner>.github.io/<repo>/) link to the file on GitHub; locally, link relatively.
function sourceLink(path) {
  const host = location.hostname;
  if (host.endsWith(".github.io")) {
    const owner = host.slice(0, -".github.io".length);
    const repo = location.pathname.split("/").filter(Boolean)[0];
    if (repo) return `https://github.com/${owner}/${repo}/blob/${BRANCH}/${path}`;
  }
  return path;
}

async function fetchText(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.text();
}

// ---- TypeQL highlighting: Prism with the TypeDB website's TypeQL grammar (assets/prism-typeql.js) ----

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function highlight(source) {
  const grammar = window.Prism && Prism.languages.typeql;
  return grammar ? Prism.highlight(source, grammar, "typeql") : escapeHtml(source);
}

// ---- code blocks ----

async function renderCode(el) {
  const path = el.dataset.code;
  el.classList.add("code");
  el.innerHTML = `
    <div class="bar">
      <span class="path">${path}</span>
      <span class="actions"><button type="button">Copy</button><a href="${sourceLink(path)}" target="_blank" rel="noopener">View file</a></span>
    </div>
    <pre><code class="language-typeql">Loading…</code></pre>`;
  const code = el.querySelector("code");
  try {
    const text = await fetchText(path);
    code.innerHTML = highlight(text.replace(/\s+$/, ""));
    const button = el.querySelector("button");
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(text);
        button.textContent = "Copied!";
      } catch {
        button.textContent = "Copy failed";
      }
      setTimeout(() => (button.textContent = "Copy"), 1500);
    });
  } catch (e) {
    code.innerHTML = `<span class="error">Could not load ${path} (${escapeHtml(e.message)}). Open the file directly via “View file”.</span>`;
  }
}

// ---- diagrams ----

async function renderSvg(el) {
  const path = el.dataset.svg;
  try {
    el.insertAdjacentHTML("afterbegin", await fetchText(path));
  } catch (e) {
    el.insertAdjacentHTML("afterbegin", `<img src="${path}" alt="">`);
  }
}

// ---- CSV table (the demo data has no quoted fields) ----

async function renderCsv(el) {
  const path = el.dataset.csv;
  try {
    const [header, ...rows] = (await fetchText(path)).trim().split(/\r?\n/).map((line) => line.split(","));
    const isNumeric = header.map((_, i) => rows.every((r) => r[i] !== "" && !isNaN(Number(r[i]))));
    const cell = (v, i) => {
      const shown = isNumeric[i] ? Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 }) : v;
      return `<td${isNumeric[i] ? ' class="num"' : ""}>${escapeHtml(shown)}</td>`;
    };
    el.innerHTML = `<div class="table-wrap"><table class="data">
      <thead><tr>${header.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr></thead>
      <tbody>${rows.map((r) => `<tr>${r.map(cell).join("")}</tr>`).join("")}</tbody>
    </table></div>`;
  } catch (e) {
    el.innerHTML = `<p class="error">Could not load ${path} (${escapeHtml(e.message)}).</p>`;
  }
}

document.querySelectorAll("[data-code]").forEach(renderCode);
document.querySelectorAll("[data-svg]").forEach(renderSvg);
document.querySelectorAll("[data-csv]").forEach(renderCsv);
document.querySelectorAll("[data-source-link]").forEach((a) => (a.href = sourceLink(a.dataset.sourceLink)));
