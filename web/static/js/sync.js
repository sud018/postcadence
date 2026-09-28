// Fills in the sync badge (every page) and the sync card (Settings) once the
// page has loaded, because asking GitHub takes a moment.
const LABELS = { same: "on GitHub ✓", changed: "changed here", missing: "not on GitHub yet" };

async function loadSync() {
  const badge = document.getElementById("sync-badge");
  let data;
  try {
    const response = await fetch("/sync/status");
    data = await response.json();
  } catch {
    data = { level: "error", text: "Could not check", files: [], behind: 0 };
  }

  if (badge) {
    badge.textContent = data.text;
    badge.className = `sync-pill sync-${data.level}`;
    badge.hidden = false;
  }

  const summary = document.getElementById("sync-summary");
  if (summary) {
    summary.textContent = data.text;
    summary.className = `sync-pill sync-${data.level}`;
  }

  const list = document.getElementById("sync-files");
  if (list) {
    list.innerHTML = "";
    for (const file of data.files) {
      const row = document.createElement("li");
      row.innerHTML = `<code></code><span class="fs-${file.status}"></span>`;
      row.querySelector("code").textContent = file.path;
      row.querySelector("span").textContent = LABELS[file.status] || file.status;
      list.appendChild(row);
    }
    if (data.behind || data.ahead) {
      const row = document.createElement("li");
      row.innerHTML = `<code>data/state.json</code><span class="fs-changed"></span>`;
      const parts = [];
      if (data.behind) parts.push(`${data.behind} newer on GitHub`);
      if (data.ahead) parts.push(`${data.ahead} only here`);
      row.querySelector("span").textContent = parts.join(" · ");
      list.appendChild(row);
    }
    if (!list.children.length) {
      list.innerHTML = `<li><span></span></li>`;
      list.querySelector("span").textContent = data.text;
    }
  }

  const push = document.getElementById("sync-push");
  if (push) push.disabled = data.level !== "push";
  const pull = document.getElementById("sync-pull");
  if (pull) pull.disabled = !data.behind;
  const pushState = document.getElementById("sync-push-state");
  if (pushState) pushState.disabled = !data.ahead;
}

document.addEventListener("DOMContentLoaded", loadSync);

document.querySelectorAll("button[data-busy]").forEach((button) => {
  if (button.dataset.busyBound) return;
  button.dataset.busyBound = "1";
  const form = button.form;
  if (!form) return;
  form.addEventListener("submit", () => {
    button.textContent = button.dataset.busy;
    setTimeout(() => (button.disabled = true), 0);
  });
});
