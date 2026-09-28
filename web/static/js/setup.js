/* Setup step 1: choose a provider, verify the key, pick a model. */

const form = document.getElementById("provider-form");
const result = document.getElementById("result");
const where = document.getElementById("where");

const HELP = {
  openai: "platform.openai.com → API keys",
  anthropic: "console.anthropic.com → API keys",
  gemini: "aistudio.google.com → Get API key",
  ollama: "No key needed. Cloud posting will not work with this.",
};

/* highlight the chosen card and update the hint */
form.addEventListener("change", (event) => {
  if (event.target.name !== "provider") return;
  document.querySelectorAll(".pcard").forEach((card) =>
    card.classList.toggle("is-on", card.contains(event.target) && event.target.checked));
  where.textContent = HELP[event.target.value] || "";
  result.innerHTML = "";
});

document.querySelectorAll(".pcard").forEach((card) =>
  card.addEventListener("click", () => {
    document.querySelectorAll(".pcard").forEach((c) => c.classList.remove("is-on"));
    card.classList.add("is-on");
  }));

/* verify the key */
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector("button");
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Checking…";
  result.innerHTML = '<div class="flash">Asking the model to say hello…</div>';

  const response = await fetch("/setup/provider", { method: "POST", body: new FormData(form) });
  result.innerHTML = await response.text();
  document.getElementById("api-key").value = "";

  button.disabled = false;
  button.textContent = original;
  wireModelForm();
});

/* the model dropdown arrives with the result, so wire it up afterwards */
function wireModelForm() {
  const modelForm = document.getElementById("model-form");
  if (!modelForm) return;
  modelForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const response = await fetch("/setup/model", { method: "POST", body: new FormData(modelForm) });
    result.innerHTML = await response.text();
  });
}
