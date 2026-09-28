/* Setup step 1: choose a provider, see its models, verify the key, save a choice. */

const form = document.getElementById("provider-form");
const result = document.getElementById("result");
const models = document.getElementById("models");
const where = document.getElementById("where");
const keyField = document.getElementById("api-key");

const HELP = {
  openai: "platform.openai.com → API keys",
  anthropic: "console.anthropic.com → API keys",
  gemini: "aistudio.google.com → Get API key",
  ollama: "No key needed — Ollama must be running on this machine.",
};

/* selecting a provider: highlight it, swap the hint, load its usual models ---- */
async function selectProvider(id) {
  document.querySelectorAll(".pcard").forEach((card) =>
    card.classList.toggle("is-on", card.dataset.provider === id));
  where.textContent = HELP[id] || "";
  keyField.disabled = id === "ollama";
  keyField.placeholder = id === "ollama" ? "No key needed" : "Paste your API key";
  result.innerHTML = "";

  const response = await fetch(`/setup/models?provider=${encodeURIComponent(id)}`);
  models.innerHTML = await response.text();
  wireModelForm();
}

document.querySelectorAll(".pcard").forEach((card) =>
  card.addEventListener("click", () => {
    card.querySelector("input").checked = true;
    selectProvider(card.dataset.provider);
  }));

/* verify the key, then replace the list with the models this key can really use */
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector('button[type="submit"]');
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Checking…";
  result.innerHTML = '<div class="flash">Asking the model to say hello…</div>';

  const response = await fetch("/setup/provider", { method: "POST", body: new FormData(form) });
  result.innerHTML = await response.text();
  models.innerHTML = "";                 // the live list is inside the result now
  keyField.value = "";

  button.disabled = false;
  button.textContent = original;
  wireModelForm();
});

/* the model form arrives with the HTML, so bind it each time it appears ------- */
function wireModelForm() {
  const modelForm = document.getElementById("model-form");
  if (!modelForm || modelForm.dataset.wired) return;
  modelForm.dataset.wired = "1";

  modelForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const response = await fetch("/setup/model", { method: "POST", body: new FormData(modelForm) });
    const saved = await response.text();
    (modelForm.closest("#result") ? result : models).insertAdjacentHTML("beforeend", saved);
  });
}

/* show the current provider's models on first load */
selectProvider(document.querySelector('input[name="provider"]:checked').value);
