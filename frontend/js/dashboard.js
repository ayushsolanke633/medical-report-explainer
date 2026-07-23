/* ==========================================================
   dashboard.js — Dashboard logic: render analysis, charts,
   recent reports, translation toggle, download, extra AI tools.
   ========================================================== */

requireAuth();

let currentReportId = null;
let currentAnalysisEn = null; // cache of English analysis for instant toggle back
let healthScoreChart = null;

document.addEventListener("DOMContentLoaded", () => {
  loadRecentReports();
  loadWelcomeName();
  setupLanguageToggle();
  setupDownloadButton();
  setupBmiCalculator();
  setupRiskCalculators();
});

// ---------- Welcome card ----------
async function loadWelcomeName() {
  const nameEl = document.getElementById("welcomeUserName");
  if (!nameEl) return;
  const response = await apiRequest("/profile");
  if (response && response.ok) {
    const profile = await response.json();
    nameEl.innerText = profile.name.split(" ")[0];
  }
}

// ---------- Recent reports ----------
async function loadRecentReports() {
  const listEl = document.getElementById("recentReportsList");
  if (!listEl) return;

  const response = await apiRequest("/history");
  if (!response || !response.ok) return;

  const reports = await response.json();
  listEl.innerHTML = "";

  if (reports.length === 0) {
    listEl.innerHTML = `<p class="text-muted">No reports uploaded yet. Upload your first report above!</p>`;
    updateAnalyticsCharts([]);
    return;
  }

  reports.slice(0, 5).forEach((r) => {
    const item = document.createElement("div");
    item.className = "recent-report-item";
    item.innerHTML = `
      <div>
        <div class="fw-semibold">${escapeHtml(r.report_name)}</div>
        <div class="test-values">${new Date(r.created_at).toLocaleDateString()} ${r.hospital_name ? "• " + escapeHtml(r.hospital_name) : ""}</div>
      </div>
      <div class="d-flex align-items-center gap-2">
        ${r.risk_level ? `<span class="risk-badge risk-${r.risk_level.toLowerCase()}">${r.risk_level}</span>` : ""}
        <button class="btn btn-sm btn-outline-brand" onclick="viewReport(${r.id})">View</button>
      </div>
    `;
    listEl.appendChild(item);
  });

  updateAnalyticsCharts(reports);
}

async function viewReport(reportId) {
  const response = await apiRequest(`/report/${reportId}`);
  if (!response || !response.ok) {
    showToast("Could not load this report.", "error");
    return;
  }
  const detail = await response.json();
  currentReportId = reportId;
  if (detail.analysis) {
    renderAnalysis(detail.analysis, reportId);
    document.getElementById("analysisResults")?.scrollIntoView({ behavior: "smooth" });
  } else {
    showToast("This report has not been analyzed yet.", "info");
  }
}

// ---------- Render full analysis ----------
function renderAnalysis(analysis, reportId) {
  currentReportId = reportId;
  currentAnalysisEn = analysis;

  document.getElementById("analysisResults").style.display = "block";

  // Health score ring
  renderHealthScoreRing(analysis.health_score);

  // Risk badge
  const riskBadge = document.getElementById("riskLevelBadge");
  if (riskBadge) {
    riskBadge.innerText = analysis.risk_level;
    riskBadge.className = `risk-badge risk-${analysis.risk_level.toLowerCase()}`;
  }

  // Patient summary
  setTextAndVoice("patientSummaryText", analysis.patient_summary);
  setTextAndVoice("overallHealthSummaryText", analysis.overall_health_summary);

  // Key findings
  const findingsList = document.getElementById("keyFindingsList");
  if (findingsList) {
    findingsList.innerHTML = analysis.key_findings.map((f) => `<li>${escapeHtml(f)}</li>`).join("");
  }

  // Detected tests / condition cards
  const testsContainer = document.getElementById("detectedTestsContainer");
  if (testsContainer) {
    testsContainer.innerHTML = analysis.detected_tests.map(renderTestCard).join("");
  }

  // Diet & exercise advice
  renderSimpleList("dietAdviceList", analysis.diet_advice);
  renderSimpleList("exerciseAdviceList", analysis.exercise_advice);
  renderSimpleList("redFlagsList", analysis.red_flags);
  renderSimpleList("emergencySignsList", analysis.emergency_signs);

  setTextAndVoice("doctorRecommendationText", analysis.doctor_recommendation);

  // Emergency banner
  const emergencyBanner = document.getElementById("emergencyBanner");
  if (emergencyBanner) {
    emergencyBanner.style.display = analysis.emergency_signs.length > 0 ? "block" : "none";
  }
}

function renderTestCard(test) {
  const statusClass = test.status.toLowerCase();
  return `
    <div class="test-card status-${statusClass}">
      <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
        <div>
          <span class="status-dot ${statusClass}"></span>
          <strong>${escapeHtml(test.test_name)}</strong>
        </div>
        <div class="test-values">
          Value: <strong>${escapeHtml(test.actual_value)}</strong> &nbsp;|&nbsp; Normal: ${escapeHtml(test.normal_range)}
        </div>
      </div>
      <p class="mt-2 mb-1">${escapeHtml(test.meaning)}</p>
      ${test.possible_causes.length ? `<p class="mb-1"><strong>Possible causes:</strong> ${test.possible_causes.map(escapeHtml).join(", ")}</p>` : ""}
      ${test.lifestyle_suggestions.length ? `<p class="mb-1"><strong>Lifestyle tips:</strong> ${test.lifestyle_suggestions.map(escapeHtml).join(", ")}</p>` : ""}
      ${test.diet_suggestions.length ? `<p class="mb-1"><strong>Diet tips:</strong> ${test.diet_suggestions.map(escapeHtml).join(", ")}</p>` : ""}
      <p class="mb-0 test-values"><strong>When to consult a doctor:</strong> ${escapeHtml(test.when_to_consult_doctor)}</p>
    </div>
  `;
}

function renderSimpleList(elementId, items) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.innerHTML = (items || []).map((i) => `<li>${escapeHtml(i)}</li>`).join("") || `<li class="text-muted">None noted</li>`;
}

function setTextAndVoice(elementId, text) {
  const el = document.getElementById(elementId);
  if (el) el.innerText = text;
}

// ---------- Health score ring (Chart.js doughnut) ----------
function renderHealthScoreRing(score) {
  const canvas = document.getElementById("healthScoreChart");
  if (!canvas) return;

  const color = score >= 75 ? "#16a34a" : score >= 50 ? "#d97706" : "#dc2626";

  if (healthScoreChart) healthScoreChart.destroy();
  healthScoreChart = new Chart(canvas, {
    type: "doughnut",
    data: {
      datasets: [{
        data: [score, 100 - score],
        backgroundColor: [color, "#e2e8f0"],
        borderWidth: 0,
        cutout: "78%",
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
    },
  });

  document.getElementById("healthScoreValue").innerText = `${Math.round(score)}`;
}

// ---------- Analytics charts (report count, abnormal values trend) ----------
let reportCountChart = null;
let healthTrendChart = null;

function updateAnalyticsCharts(reports) {
  const countCanvas = document.getElementById("reportCountChart");
  const trendCanvas = document.getElementById("healthTrendChart");
  if (!countCanvas || !trendCanvas) return;

  const sorted = [...reports].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  const labels = sorted.map((r) => new Date(r.created_at).toLocaleDateString());
  const scores = sorted.map((r) => r.health_score || 0);

  if (reportCountChart) reportCountChart.destroy();
  reportCountChart = new Chart(countCanvas, {
    type: "bar",
    data: {
      labels: ["Total Reports"],
      datasets: [{ label: "Reports", data: [reports.length], backgroundColor: "#1a56db", borderRadius: 8 }],
    },
    options: { responsive: true, plugins: { legend: { display: false } } },
  });

  if (healthTrendChart) healthTrendChart.destroy();
  healthTrendChart = new Chart(trendCanvas, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Health Score Trend",
        data: scores,
        borderColor: "#0ea5b7",
        backgroundColor: "rgba(14,165,183,0.15)",
        tension: 0.35,
        fill: true,
      }],
    },
    options: { responsive: true, scales: { y: { min: 0, max: 100 } } },
  });
}

// ---------- Language toggle (English / Marathi) ----------
function setupLanguageToggle() {
  const btnEn = document.getElementById("langBtnEn");
  const btnMr = document.getElementById("langBtnMr");
  if (!btnEn || !btnMr) return;

  btnEn.addEventListener("click", () => {
    if (!currentAnalysisEn) return;
    setActiveLangButton(btnEn, btnMr);
    renderAnalysis(currentAnalysisEn, currentReportId);
  });

  btnMr.addEventListener("click", async () => {
    if (!currentReportId) {
      showToast("Analyze a report first.", "info");
      return;
    }
    setActiveLangButton(btnMr, btnEn);
    showToast("Translating to Marathi...", "info");

    const response = await apiRequest("/translate", {
      method: "POST",
      body: JSON.stringify({ report_id: currentReportId, target_language: "mr" }),
    });

    if (!response || !response.ok) {
      showToast("Translation failed.", "error");
      return;
    }

    const translated = await response.json();
    renderAnalysis(translated, currentReportId);
    currentAnalysisEn = currentAnalysisEn || translated; // keep English cached for toggle-back
  });
}

function setActiveLangButton(active, inactive) {
  active.classList.add("btn-brand");
  active.classList.remove("btn-outline-brand");
  inactive.classList.add("btn-outline-brand");
  inactive.classList.remove("btn-brand");
}

// ---------- Download PDF summary ----------
function setupDownloadButton() {
  const downloadBtn = document.getElementById("downloadSummaryBtn");
  if (!downloadBtn) return;

  downloadBtn.addEventListener("click", async () => {
    if (!currentReportId) {
      showToast("Analyze a report first.", "info");
      return;
    }
    const token = getToken();
    const url = `${API_BASE_URL}/download/${currentReportId}`;

    try {
      const response = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error("Download failed");
      const blob = await response.blob();
      const link = document.createElement("a");
      link.href = window.URL.createObjectURL(blob);
      link.download = `report_${currentReportId}_summary.pdf`;
      link.click();
      showToast("Summary downloaded!", "success");
    } catch (err) {
      showToast("Could not download summary PDF.", "error");
    }
  });
}

// ---------- Extra AI tool: BMI Calculator ----------
function setupBmiCalculator() {
  const form = document.getElementById("bmiForm");
  if (!form) return;

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const heightCm = parseFloat(document.getElementById("bmiHeight").value);
    const weightKg = parseFloat(document.getElementById("bmiWeight").value);
    if (!heightCm || !weightKg) return;

    const heightM = heightCm / 100;
    const bmi = weightKg / (heightM * heightM);
    let category = "Normal weight";
    if (bmi < 18.5) category = "Underweight";
    else if (bmi >= 25 && bmi < 30) category = "Overweight";
    else if (bmi >= 30) category = "Obese";

    document.getElementById("bmiResult").innerHTML = `
      Your BMI is <strong>${bmi.toFixed(1)}</strong> — <strong>${category}</strong>
    `;
  });
}

// ---------- Extra AI tools: Diabetes & Heart risk (simple heuristic estimators) ----------
function setupRiskCalculators() {
  const diabetesForm = document.getElementById("diabetesRiskForm");
  if (diabetesForm) {
    diabetesForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const age = parseInt(document.getElementById("diabAge").value, 10);
      const bmi = parseFloat(document.getElementById("diabBmi").value);
      const familyHistory = document.getElementById("diabFamilyHistory").checked;

      let score = 0;
      if (age > 45) score += 2;
      if (bmi >= 25) score += 2;
      if (familyHistory) score += 3;

      const level = score >= 5 ? "High" : score >= 2 ? "Moderate" : "Low";
      document.getElementById("diabetesRiskResult").innerHTML =
        `Estimated Diabetes Risk: <span class="risk-badge risk-${level.toLowerCase()}">${level}</span>`;
    });
  }

  const heartForm = document.getElementById("heartRiskForm");
  if (heartForm) {
    heartForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const age = parseInt(document.getElementById("heartAge").value, 10);
      const smoker = document.getElementById("heartSmoker").checked;
      const highBp = document.getElementById("heartHighBp").checked;

      let score = 0;
      if (age > 50) score += 2;
      if (smoker) score += 3;
      if (highBp) score += 3;

      const level = score >= 6 ? "High" : score >= 3 ? "Moderate" : "Low";
      document.getElementById("heartRiskResult").innerHTML =
        `Estimated Heart Risk: <span class="risk-badge risk-${level.toLowerCase()}">${level}</span>`;
    });
  }
}

// ---------- Helpers ----------
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
