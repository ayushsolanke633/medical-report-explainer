/* ==========================================================
   history.js — Report history timeline, search, view, delete
   Used on history.html
   ========================================================== */

requireAuth();

document.addEventListener("DOMContentLoaded", () => {
  loadHistory();

  const searchInput = document.getElementById("historySearchInput");
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener("input", () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => loadHistory(searchInput.value.trim()), 350);
    });
  }
});

async function loadHistory(search = "") {
  const timelineEl = document.getElementById("historyTimeline");
  const emptyState = document.getElementById("historyEmptyState");
  if (!timelineEl) return;

  timelineEl.innerHTML = `
    <div class="skeleton skeleton-card mb-3"></div>
    <div class="skeleton skeleton-card mb-3"></div>
    <div class="skeleton skeleton-card mb-3"></div>
  `;

  const query = search ? `?search=${encodeURIComponent(search)}` : "";
  const response = await apiRequest(`/history${query}`);
  if (!response || !response.ok) {
    timelineEl.innerHTML = `<p class="text-muted">Could not load history.</p>`;
    return;
  }

  const reports = await response.json();
  timelineEl.innerHTML = "";

  if (reports.length === 0) {
    if (emptyState) emptyState.style.display = "block";
    return;
  }
  if (emptyState) emptyState.style.display = "none";

  reports.forEach((r) => {
    const item = document.createElement("div");
    item.className = "timeline-item glass-card mb-3";
    item.innerHTML = `
      <div class="timeline-dot"></div>
      <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
        <div>
          <h6 class="mb-1">${escapeHtml(r.report_name)}</h6>
          <div class="test-values">
            ${new Date(r.created_at).toLocaleString()}
            ${r.hospital_name ? "• " + escapeHtml(r.hospital_name) : ""}
          </div>
        </div>
        <div class="d-flex align-items-center gap-2">
          ${r.risk_level ? `<span class="risk-badge risk-${r.risk_level.toLowerCase()}">${r.risk_level}</span>` : `<span class="text-muted small">Not analyzed</span>`}
          ${r.health_score !== null && r.health_score !== undefined ? `<span class="fw-semibold">${Math.round(r.health_score)}/100</span>` : ""}
        </div>
      </div>
      <div class="mt-3 d-flex gap-2">
        <a class="btn btn-sm btn-outline-brand" href="dashboard.html#report-${r.id}" onclick="sessionStorage.setItem('mre_open_report', ${r.id})">View</a>
        <button class="btn btn-sm btn-outline-danger" onclick="confirmDeleteReport(${r.id})">
          <i class="bi bi-trash"></i> Delete
        </button>
      </div>
    `;
    timelineEl.appendChild(item);
  });
}

async function confirmDeleteReport(reportId) {
  if (!confirm("Delete this report permanently? This cannot be undone.")) return;

  const response = await apiRequest(`/delete/${reportId}`, { method: "DELETE" });
  if (response && response.ok) {
    showToast("Report deleted.", "success");
    loadHistory(document.getElementById("historySearchInput")?.value.trim() || "");
  } else {
    showToast("Could not delete this report.", "error");
  }
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
