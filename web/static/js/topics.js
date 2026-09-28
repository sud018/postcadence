/* Topics page: every action posts a form and swaps the table HTML back in.
   No page reloads, no framework. */

const table = document.getElementById("table");

async function send(url, data) {
  const response = await fetch(url, { method: "POST", body: data });
  if (!response.ok) {
    table.insertAdjacentHTML("afterbegin",
      `<div class="flash flash-bad">Request failed (${response.status}).</div>`);
    return;
  }
  table.innerHTML = await response.text();
}

/* add ------------------------------------------------------------------- */
const form = document.getElementById("add-form");
const input = document.getElementById("add-input");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!input.value.trim()) return;
  await send("/topics/add", new FormData(form));
  input.value = "";
  input.focus();
});

/* row buttons (delegated, because the table is replaced) ----------------- */
table.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-act]");
  if (button) {
    const data = new FormData();
    data.append("index", button.dataset.index);
    if (button.dataset.act === "move") {
      data.append("delta", button.dataset.delta);
      return send("/topics/move", data);
    }
    if (confirm("Delete this topic?")) return send("/topics/delete", data);
    return;
  }

  /* rename in place ----------------------------------------------------- */
  const cell = event.target.closest(".ttext");
  if (!cell || cell.querySelector("input")) return;

  const original = cell.textContent.trim();
  cell.innerHTML = `<input class="input input-inline" value="${original.replace(/"/g, "&quot;")}">`;
  const field = cell.querySelector("input");
  field.focus();
  field.select();

  const save = async () => {
    const text = field.value.trim();
    if (!text || text === original) { cell.textContent = original; return; }
    const data = new FormData();
    data.append("index", cell.dataset.index);
    data.append("text", text);
    await send("/topics/rename", data);
  };

  field.addEventListener("blur", save, { once: true });
  field.addEventListener("keydown", (e) => {
    if (e.key === "Enter") field.blur();
    if (e.key === "Escape") { field.value = original; field.blur(); }
  });
});

/* file import ----------------------------------------------------------- */
const drop = document.getElementById("drop");
const file = document.getElementById("file");

file.addEventListener("change", () => file.files[0] && upload(file.files[0]));

["dragenter", "dragover"].forEach((name) =>
  document.addEventListener(name, (e) => { e.preventDefault(); drop.classList.add("is-over"); }));
["dragleave", "drop"].forEach((name) =>
  document.addEventListener(name, (e) => { e.preventDefault(); drop.classList.remove("is-over"); }));

document.addEventListener("drop", (event) => {
  const dropped = event.dataTransfer?.files?.[0];
  if (dropped) upload(dropped);
});

async function upload(chosen) {
  const data = new FormData();
  data.append("file", chosen);
  await send("/topics/upload", data);
  file.value = "";
}
