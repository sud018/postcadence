// Copy buttons, the tick list that remembers, and the Recheck button.
const TICKS = "postcadence.linkedin.steps";

function readTicks() {
  try {
    return new Set(JSON.parse(localStorage.getItem(TICKS) || "[]"));
  } catch {
    return new Set();          // private window, or storage switched off
  }
}

function writeTicks(done) {
  try {
    localStorage.setItem(TICKS, JSON.stringify([...done]));
  } catch {
    /* nothing to do: the ticks are a convenience, not state we rely on */
  }
}

const done = readTicks();
document.querySelectorAll(".walk-step").forEach((step) => {
  const box = step.querySelector("input");
  const id = step.dataset.step;

  box.checked = done.has(id);
  step.classList.toggle("is-done", box.checked);

  box.addEventListener("change", () => {
    box.checked ? done.add(id) : done.delete(id);
    step.classList.toggle("is-done", box.checked);
    writeTicks(done);
  });
});

const reset = document.getElementById("li-reset");
if (reset) {
  reset.addEventListener("click", () => {
    done.clear();
    writeTicks(done);
    document.querySelectorAll(".walk-step").forEach((step) => {
      step.querySelector("input").checked = false;
      step.classList.remove("is-done");
    });
  });
}

document.querySelectorAll("[data-copy]").forEach((button) =>
  button.addEventListener("click", async () => {
    await navigator.clipboard.writeText(document.getElementById(button.dataset.copy).textContent);
    button.textContent = "✓";
    setTimeout(() => (button.textContent = "⧉"), 1200);
  }));

const recheck = document.getElementById("li-recheck");
if (recheck) {
  recheck.addEventListener("click", async () => {
    const label = recheck.textContent;
    recheck.textContent = recheck.dataset.busy;
    recheck.disabled = true;

    const panel = document.getElementById("li-checks");
    try {
      const response = await fetch("/setup/linkedin/check", { method: "POST" });
      panel.innerHTML = await response.text();          // our own template, not user input
    } catch {
      panel.textContent = "Could not reach LinkedIn just now. Try again in a moment.";
    }

    recheck.textContent = label;
    recheck.disabled = false;
  });
}
