(() => {
  const dialog = document.getElementById("game-modal");
  if (!dialog) return;

  const content = document.getElementById("game-modal-content");

  document.body.addEventListener("htmx:afterSwap", (event) => {
    if (event.target === content) {
      dialog.showModal();
    }
  });

  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      dialog.close();
    }
  });

  dialog.querySelector("[data-modal-close]").addEventListener("click", () => {
    dialog.close();
  });
})();
