(() => {
  const dialog = document.getElementById("game-modal");
  if (!dialog) return;

  const content = document.getElementById("game-modal-content");
  const closeBtn = dialog.querySelector("[data-modal-close]");
  const skeleton = document.getElementById("game-modal-skeleton");

  document.body.addEventListener("htmx:beforeRequest", (event) => {
    if (event.detail.target !== content) return;
    content.replaceChildren(skeleton.content.cloneNode(true));
    if (!dialog.open) {
      dialog.showModal();
    }
  });

  document.body.addEventListener("htmx:afterSwap", (event) => {
    if (event.detail.target === content) {
      wireGalleryCarousels(content);
    }
  });

  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      dialog.close();
    }
  });

  closeBtn.addEventListener("click", () => dialog.close());

  dialog.addEventListener("close", () => {
    content.innerHTML = "";
  });

  wireGalleryCarousels(document);

  function wireGalleryCarousels(root) {
    root.querySelectorAll(".gallery-carousel").forEach((carousel) => {
      if (carousel.dataset.wired) return;
      carousel.dataset.wired = "true";

      const slides = Array.from(carousel.querySelectorAll(".gallery-slide"));
      const dots = Array.from(carousel.querySelectorAll("[data-gallery-dot]"));
      const prevBtn = carousel.querySelector("[data-gallery-prev]");
      const nextBtn = carousel.querySelector("[data-gallery-next]");
      if (slides.length < 2) return;

      let index = 0;
      const show = (i) => {
        index = (i + slides.length) % slides.length;
        slides.forEach((slide, n) => slide.classList.toggle("is-active", n === index));
        dots.forEach((dot, n) => dot.classList.toggle("is-active", n === index));
      };

      prevBtn?.addEventListener("click", () => show(index - 1));
      nextBtn?.addEventListener("click", () => show(index + 1));
      dots.forEach((dot, n) => dot.addEventListener("click", () => show(n)));
    });
  }
})();
