// The device flow, from the page's side: ask for a code, then keep asking
// GitHub whether you have approved it yet.
const connect = document.getElementById("gh-connect");

async function post(url) {
  const response = await fetch(url, { method: "POST" });
  return { ok: response.ok, data: await response.json() };
}

function say(message, bad = false) {
  const status = document.getElementById("gh-status");
  if (!status) return;
  status.textContent = message;
  status.style.color = bad ? "var(--rose)" : "var(--dim)";
}

function waitForApproval(seconds) {
  const timer = setInterval(async () => {
    const { ok, data } = await post("/setup/github/poll");

    if (!ok) {                       // a real refusal: stop asking
      clearInterval(timer);
      say(data.error, true);
      return;
    }
    if (data.status === "connected") {
      clearInterval(timer);
      say(`Connected as ${data.login}. Reloading…`);
      location.reload();
    }
  }, Math.max(seconds, 5) * 1000);   // GitHub asks us not to poll faster
}

if (connect) {
  connect.addEventListener("click", async () => {
    connect.disabled = true;
    connect.textContent = "Asking GitHub…";

    const { ok, data } = await post("/setup/github/start");
    if (!ok) {
      connect.disabled = false;
      connect.textContent = "Connect GitHub";
      say(data.error, true);
      alert(data.error);
      return;
    }

    document.getElementById("gh-code").textContent = data.user_code;
    document.getElementById("gh-open").href = data.url;
    document.getElementById("gh-flow").hidden = false;
    connect.hidden = true;

    window.open(data.url, "_blank", "noopener");
    waitForApproval(data.interval);
  });
}

const copy = document.getElementById("gh-copy");
if (copy) {
  copy.addEventListener("click", async () => {
    await navigator.clipboard.writeText(document.getElementById("gh-code").textContent);
    copy.textContent = "✓";
    setTimeout(() => (copy.textContent = "⧉"), 1200);
  });
}

// Pushing files and sending secrets are slow enough to need a word.
document.querySelectorAll("button[data-busy]").forEach((button) => {
  const form = button.form;
  if (!form) return;
  form.addEventListener("submit", () => {
    button.textContent = button.dataset.busy;
    setTimeout(() => (button.disabled = true), 0);
  });
});
