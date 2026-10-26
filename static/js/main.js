document.querySelectorAll("form[data-confirm]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm(form.dataset.confirm || "Are you sure?")) {
      event.preventDefault();
    }
  });
});
document.querySelectorAll(".flash").forEach((item) => {
  window.setTimeout(() => {
    item.classList.add("flash-fade");
  }, 4500);
});
