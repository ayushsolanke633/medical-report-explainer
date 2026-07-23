/* ==========================================================
   main.js — Shared config, dark mode, toasts, auth helpers
   Loaded on every page.
   ========================================================== */

// ---------- Global config ----------
const API_BASE_URL = "http://127.0.0.1:8000";

// ---------- Auth token helpers ----------
function getToken() {
  return localStorage.getItem("mre_token");
}

function setToken(token) {
  localStorage.setItem("mre_token", token);
}

function clearToken() {
  localStorage.removeItem("mre_token");
}

function isLoggedIn() {
  return !!getToken();
}

function logout() {
  clearToken();
  window.location.href = "login.html";
}

/**
 * Redirects to login.html if the user is not authenticated.
 * Call at the top of protected pages (dashboard.html, history.html).
 */
function requireAuth() {
  if (!isLoggedIn()) {
    window.location.href = "login.html";
  }
}

/**
 * Wrapper around fetch() that automatically attaches the JWT bearer
 * token and the API base URL, and redirects to login on 401.
 */
async function apiRequest(path, options = {}) {
  const headers = options.headers || {};
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (!(options.body instanceof FormData) && options.body) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (response.status === 401) {
    clearToken();
    window.location.href = "login.html";
    return null;
  }

  return response;
}

// ---------- Dark mode ----------
function initTheme() {
  const saved = localStorage.getItem("mre_theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
  updateThemeIcon(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  const next = current === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("mre_theme", next);
  updateThemeIcon(next);
}

function updateThemeIcon(theme) {
  const icon = document.getElementById("themeIcon");
  if (icon) {
    icon.className = theme === "dark" ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
  }
}

// ---------- Toast notifications ----------
function showToast(message, type = "success") {
  let container = document.querySelector(".toast-container-custom");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container-custom";
    document.body.appendChild(container);
  }

  const colors = {
    success: "#16a34a",
    error: "#dc2626",
    info: "#1a56db",
    warning: "#d97706",
  };

  const toastEl = document.createElement("div");
  toastEl.style.background = "#ffffff";
  toastEl.style.borderLeft = `5px solid ${colors[type] || colors.info}`;
  toastEl.style.borderRadius = "12px";
  toastEl.style.boxShadow = "0 8px 24px rgba(0,0,0,0.12)";
  toastEl.style.padding = "14px 18px";
  toastEl.style.marginBottom = "10px";
  toastEl.style.minWidth = "260px";
  toastEl.style.fontSize = "0.92rem";
  toastEl.style.fontWeight = "500";
  toastEl.style.color = "#1e293b";
  toastEl.style.opacity = "0";
  toastEl.style.transform = "translateX(20px)";
  toastEl.style.transition = "all 0.3s ease";
  toastEl.innerText = message;

  container.appendChild(toastEl);
  requestAnimationFrame(() => {
    toastEl.style.opacity = "1";
    toastEl.style.transform = "translateX(0)";
  });

  setTimeout(() => {
    toastEl.style.opacity = "0";
    toastEl.style.transform = "translateX(20px)";
    setTimeout(() => toastEl.remove(), 300);
  }, 3800);
}

// ---------- Navbar auth state ----------
function updateNavbarAuthLinks() {
  const authLinks = document.getElementById("navAuthLinks");
  if (!authLinks) return;

  if (isLoggedIn()) {
    authLinks.innerHTML = `
      <li class="nav-item"><a class="nav-link nav-link-custom" href="dashboard.html">Dashboard</a></li>
      <li class="nav-item"><a class="nav-link nav-link-custom" href="history.html">History</a></li>
      <li class="nav-item"><a class="nav-link nav-link-custom" href="#" onclick="logout()">Logout</a></li>
    `;
  } else {
    authLinks.innerHTML = `
      <li class="nav-item"><a class="nav-link nav-link-custom" href="login.html">Login</a></li>
      <li class="nav-item"><a class="btn btn-brand ms-2" href="register.html">Get Started</a></li>
    `;
  }
}

// ---------- Voice: Read explanation aloud ----------
let currentUtterance = null;

function speakText(text, buttonEl) {
  if (!("speechSynthesis" in window)) {
    showToast("Voice playback is not supported in this browser.", "warning");
    return;
  }

  if (speechSynthesis.speaking) {
    speechSynthesis.cancel();
    if (buttonEl) buttonEl.classList.remove("speaking");
    if (currentUtterance) return; // was already speaking this one -> just stop
  }

  currentUtterance = new SpeechSynthesisUtterance(text);
  currentUtterance.rate = 0.95;
  currentUtterance.onend = () => {
    if (buttonEl) buttonEl.classList.remove("speaking");
    currentUtterance = null;
  };

  if (buttonEl) buttonEl.classList.add("speaking");
  speechSynthesis.speak(currentUtterance);
}

// ---------- Init on every page ----------
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  updateNavbarAuthLinks();

  const themeBtn = document.getElementById("themeToggleBtn");
  if (themeBtn) themeBtn.addEventListener("click", toggleTheme);

  // Smooth scroll for in-page anchors (landing page nav)
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      const targetId = this.getAttribute("href");
      const target = document.querySelector(targetId);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth" });
      }
    });
  });
});
