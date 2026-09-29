// Copy buttons. Same behaviour as the LinkedIn setup page, which loads its own
// script - this page only needs this one piece of it.
document.querySelectorAll("[data-copy]").forEach((button) =>
  button.addEventListener("click", async () => {
    await navigator.clipboard.writeText(
      document.getElementById(button.dataset.copy).textContent.trim());
    button.textContent = "✓";
    setTimeout(() => (button.textContent = "⧉"), 1200);
  }));
