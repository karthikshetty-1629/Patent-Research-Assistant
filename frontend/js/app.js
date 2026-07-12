// Core interactivity for index.html: theme toggle, voice search, and
// calling the /search RAG endpoint.
(function () {
  "use strict";

  const THEME_KEY = "patent-assistant-theme";

  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    const preferred = saved || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", preferred);
    updateThemeIcon(preferred);
  }

  function updateThemeIcon(theme) {
    const icon = document.getElementById("theme-icon");
    if (icon) icon.textContent = theme === "dark" ? "☀️" : "🌙";
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "light";
    const next = current === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem(THEME_KEY, next);
    updateThemeIcon(next);
  }

  function initVoiceSearch() {
    const micButton = document.getElementById("mic-button");
    const searchInput = document.getElementById("search-input");
    if (!micButton || !searchInput) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      micButton.disabled = true;
      micButton.title = "Voice search is not supported in this browser";
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onstart = () => micButton.classList.add("listening");
    recognition.onend = () => micButton.classList.remove("listening");
    recognition.onerror = () => micButton.classList.remove("listening");
    recognition.onresult = (event) => {
      searchInput.value = event.results[0][0].transcript;
      runSearch();
    };

    micButton.addEventListener("click", () => recognition.start());
  }

  function renderResults(data) {
    const answerEl = document.getElementById("answer");
    const resultsEl = document.getElementById("results");
    resultsEl.innerHTML = "";

    answerEl.textContent = data.answer || "No answer generated.";
    answerEl.parentElement.classList.remove("d-none");

    (data.sources || []).forEach((source) => {
      const card = document.createElement("div");
      card.className = "result-card";
      const score = typeof source.relevance_score === "number" ? source.relevance_score.toFixed(3) : "n/a";
      card.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
          <h5 class="mb-1">${source.title || "Untitled patent"}</h5>
          <span class="badge badge-score">score ${score}</span>
        </div>
        <div class="result-meta">Patent ${source.patent_id || "unknown"} &middot; Published ${source.publication_date || "unknown"}</div>
      `;
      resultsEl.appendChild(card);
    });
  }

  async function runSearch() {
    const searchInput = document.getElementById("search-input");
    const query = searchInput.value.trim();
    if (!query) return;

    const submitButton = document.getElementById("search-submit");
    const spinner = document.getElementById("search-spinner");
    submitButton.disabled = true;
    spinner.classList.remove("d-none");

    try {
      const response = await fetch(`${window.APP_CONFIG.API_BASE_URL}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        throw new Error(errorBody.error || `Request failed with status ${response.status}`);
      }
      const data = await response.json();
      renderResults(data);
    } catch (error) {
      const answerEl = document.getElementById("answer");
      answerEl.textContent = `Error: ${error.message}`;
      answerEl.parentElement.classList.remove("d-none");
    } finally {
      submitButton.disabled = false;
      spinner.classList.add("d-none");
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initVoiceSearch();

    const themeButton = document.getElementById("theme-toggle");
    if (themeButton) themeButton.addEventListener("click", toggleTheme);

    const searchForm = document.getElementById("search-form");
    if (searchForm) {
      searchForm.addEventListener("submit", (event) => {
        event.preventDefault();
        runSearch();
      });
    }
  });
})();
