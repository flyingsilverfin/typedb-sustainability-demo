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

// ---- CSV tables (the demo data has no quoted fields) ----
// Optional excerpt attributes:
//   data-columns="mill,refinery"                    show only these columns
//   data-rows="mill=A|mill=B&refinery=C"            show the first row matching each `|`-separated condition
// In excerpts, a name repeated across columns of the same row is highlighted.

const PLACEHOLDER = "NOT REFINED";

function excerpt(header, rows, columnSpec, rowSpec) {
  let picked = rows;
  if (rowSpec) {
    picked = rowSpec.split("|").map((condition) => {
      const tests = condition.split("&").map((term) => term.split("="));
      return rows.find((r) => tests.every(([col, value]) => r[header.indexOf(col.trim())] === value.trim()));
    }).filter(Boolean);
  }
  const columns = columnSpec ? columnSpec.split(",").map((c) => header.indexOf(c.trim())) : header.map((_, i) => i);
  return { header: columns.map((i) => header[i]), rows: picked.map((r) => columns.map((i) => r[i])) };
}

async function renderCsv(el) {
  const path = el.dataset.csv;
  const isExcerpt = Boolean(el.dataset.columns || el.dataset.rows);
  try {
    const [allHeader, ...allRows] = (await fetchText(path)).trim().split(/\r?\n/).map((line) => line.split(","));
    const { header, rows } = excerpt(allHeader, allRows, el.dataset.columns, el.dataset.rows);
    const isNumeric = header.map((_, i) => rows.every((r) => r[i] !== "" && !isNaN(Number(r[i]))));
    const cell = (row) => (v, i) => {
      const classes = [];
      if (isNumeric[i]) classes.push("num");
      if (v === PLACEHOLDER) classes.push("placeholder");
      else if (isExcerpt && row.filter((other) => other === v).length > 1) classes.push("repeated");
      const shown = isNumeric[i] ? Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 }) : v;
      return `<td${classes.length ? ` class="${classes.join(" ")}"` : ""}>${escapeHtml(shown)}</td>`;
    };
    el.innerHTML = `<div class="table-wrap${isExcerpt ? " excerpt" : ""}"><table class="data">
      <thead><tr>${header.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr></thead>
      <tbody>${rows.map((r) => `<tr>${r.map(cell(r)).join("")}</tr>`).join("")}</tbody>
    </table></div>`;
  } catch (e) {
    el.innerHTML = `<p class="error">Could not load ${path} (${escapeHtml(e.message)}).</p>`;
  }
}

document.querySelectorAll("[data-code]").forEach(renderCode);
document.querySelectorAll("[data-svg]").forEach(renderSvg);
document.querySelectorAll("[data-csv]").forEach(renderCsv);
document.querySelectorAll("[data-source-link]").forEach((a) => (a.href = sourceLink(a.dataset.sourceLink)));

// ---- "Questions or help?" box: posts to a Discord channel via webhook ----

const DISCORD_WEBHOOK =
  "https://discord.com/api/webhooks/1557084826350395525/2tMgN43cSGrp80Qr0EhlOU6kfMG4L5STR3OtVv5jqA1ros51yWj7metJX1bTkY5Gn2FD";
const DISCORD_USER_ID = "672741530997358602"; // Joshua's numeric Discord user ID; mentions only ping with this set

function currentSection() {
  // the last section heading scrolled past, so Joshua knows where the question came from
  let label = "Top of page";
  document.querySelectorAll("h2, h3").forEach((h) => {
    if (h.getBoundingClientRect().top < window.innerHeight * 0.4) label = h.textContent.trim();
  });
  return label;
}

function setupHelp() {
  const box = document.getElementById("help");
  if (!box) return;
  const form = box.querySelector("form");
  const status = form.querySelector(".help-status");
  const send = form.querySelector(".help-send");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = form.elements.name.value.trim() || "Someone";
    const message = form.elements.message.value.trim();
    if (!message) return;
    const mention = DISCORD_USER_ID ? `<@${DISCORD_USER_ID}> ` : "@joshua.send ";
    const content = `${mention}**${name}** asked from *${currentSection()}*:\n>>> ${message}`;
    send.disabled = true;
    status.textContent = "Sending…";
    try {
      const response = await fetch(DISCORD_WEBHOOK, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: "ER 2026 tutorial",
          content: content.slice(0, 2000),
          // only ever ping Joshua, whatever the message text contains
          allowed_mentions: { parse: [], users: DISCORD_USER_ID ? [DISCORD_USER_ID] : [] },
        }),
      });
      if (!response.ok) throw new Error(`${response.status}`);
      form.elements.message.value = "";
      status.textContent = "Sent! Joshua will come over or reply in person.";
    } catch (e) {
      status.textContent = "Couldn't send. Please raise your hand instead!";
    } finally {
      setTimeout(() => (send.disabled = false), 5000); // stay well within Discord's rate limit
    }
  });
}

setupHelp();
