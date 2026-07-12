// Shared signup/login form handling for signup.html and login.html.
(function () {
  "use strict";

  function showMessage(el, message, isError) {
    el.textContent = message;
    el.classList.remove("d-none", "text-danger", "text-success");
    el.classList.add(isError ? "text-danger" : "text-success");
  }

  async function postAuth(route, payload) {
    const response = await fetch(`${window.APP_CONFIG.API_BASE_URL}/auth/${route}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || `Request failed with status ${response.status}`);
    }
    return data;
  }

  function initSignupForm() {
    const form = document.getElementById("signup-form");
    if (!form) return;
    const messageEl = document.getElementById("auth-message");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const email = document.getElementById("signup-email").value.trim();
      const password = document.getElementById("signup-password").value;
      try {
        const data = await postAuth("signup", { email, password });
        showMessage(messageEl, data.message, false);
      } catch (error) {
        showMessage(messageEl, error.message, true);
      }
    });

    const confirmForm = document.getElementById("confirm-form");
    if (confirmForm) {
      confirmForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const email = document.getElementById("confirm-email").value.trim();
        const code = document.getElementById("confirm-code").value.trim();
        try {
          const data = await postAuth("confirm", { email, code });
          showMessage(messageEl, data.message, false);
        } catch (error) {
          showMessage(messageEl, error.message, true);
        }
      });
    }
  }

  function initLoginForm() {
    const form = document.getElementById("login-form");
    if (!form) return;
    const messageEl = document.getElementById("auth-message");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const email = document.getElementById("login-email").value.trim();
      const password = document.getElementById("login-password").value;
      try {
        const data = await postAuth("login", { email, password });
        localStorage.setItem("patent-assistant-token", data.id_token);
        showMessage(messageEl, "Login successful. Redirecting...", false);
        window.location.href = "index.html";
      } catch (error) {
        showMessage(messageEl, error.message, true);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initSignupForm();
    initLoginForm();
  });
})();
