"use strict";

// Preview guard only. When the backend is connected, render preview=False
// in Flask and these ordinary HTML forms will submit to their action URLs.
if (document.body.dataset.preview === "true") {
  for (const form of document.querySelectorAll("[data-preview-form]")) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const nameInput = form.elements.namedItem("name") || form.elements.namedItem("displayName");
      if (nameInput && !nameInput.value.trim()) {
        nameInput.setCustomValidity("Enter a name.");
        nameInput.reportValidity();
        nameInput.addEventListener("input", () => nameInput.setCustomValidity(""), { once: true });
        return;
      }
      const message = form.querySelector("[data-form-status]");
      message.textContent = "This is a demo, so your changes haven’t been saved.";
      message.hidden = false;
    });
  }
}
