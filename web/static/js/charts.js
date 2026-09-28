// One tooltip per chart: each column is its own hit target, on hover and on
// keyboard focus. The text comes from data-tip and goes in with textContent.
document.querySelectorAll(".chart-wrap").forEach((wrap) => {
  const tip = wrap.querySelector(".chart-tip");
  if (!tip) return;

  function show(col) {
    tip.textContent = col.dataset.tip;
    tip.hidden = false;
    const box = col.querySelector(".hit").getBoundingClientRect();
    const frame = wrap.getBoundingClientRect();
    const left = box.left - frame.left + box.width / 2;
    tip.style.left = `${Math.min(Math.max(left, 70), frame.width - 70)}px`;
    col.classList.add("is-hot");
  }

  function hide(col) {
    tip.hidden = true;
    col.classList.remove("is-hot");
  }

  wrap.querySelectorAll(".col").forEach((col) => {
    col.addEventListener("pointerenter", () => show(col));
    col.addEventListener("pointerleave", () => hide(col));
    col.addEventListener("focus", () => show(col));
    col.addEventListener("blur", () => hide(col));
  });
});
