/* Schedule step: one time field per post, and a timezone shortcut. */

const times = document.getElementById("times");
const count = document.getElementById("count");
const DEFAULTS = ["09:00", "13:00", "17:30", "11:00", "19:00"];

count.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-n]");
  if (!button) return;
  const want = Number(button.dataset.n);

  count.querySelectorAll("button").forEach((b) => b.classList.toggle("is-on", b === button));

  const fields = [...times.querySelectorAll("input")];
  for (let i = fields.length; i < want; i++) {
    const field = document.createElement("input");
    Object.assign(field, { className: "input", type: "time", name: "post_times", required: true,
                           value: DEFAULTS[i] || "12:00" });
    times.appendChild(field);
  }
  fields.slice(want).forEach((f) => f.remove());
});

document.getElementById("detect").addEventListener("click", () => {
  const mine = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const select = document.getElementById("tz");
  if ([...select.options].some((o) => o.value === mine)) select.value = mine;
});

/* only show preview options when preview mode is chosen */
const previewOpts = document.getElementById("preview-opts");
const syncMode = () => {
  const mode = document.querySelector('input[name="mode"]:checked')?.value;
  previewOpts.style.display = mode === "preview" ? "" : "none";
};
document.querySelectorAll('input[name="mode"]').forEach((r) => r.addEventListener("change", syncMode));
syncMode();
