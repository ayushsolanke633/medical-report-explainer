/* ==========================================================
   upload.js — Drag & drop upload, progress bar, trigger analysis
   Used on dashboard.html
   ========================================================== */

document.addEventListener("DOMContentLoaded", () => {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const progressWrap = document.getElementById("uploadProgressWrap");
  const progressBar = document.getElementById("uploadProgressBar");
  const progressLabel = document.getElementById("uploadProgressLabel");
  const hospitalInput = document.getElementById("hospitalNameInput");

  if (!dropzone || !fileInput) return; // not on dashboard page

  dropzone.addEventListener("click", () => fileInput.click());

  ["dragenter", "dragover"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length) handleFileUpload(files[0]);
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length) handleFileUpload(e.target.files[0]);
  });

  function handleFileUpload(file) {
    if (file.type !== "application/pdf") {
      showToast("Only PDF files are supported.", "error");
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      showToast("File exceeds the 20MB size limit.", "error");
      return;
    }

    uploadFile(file);
  }

  function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    const hospitalName = hospitalInput ? hospitalInput.value.trim() : "";
    const url = new URL(`${API_BASE_URL}/upload`);
    if (hospitalName) url.searchParams.set("hospital_name", hospitalName);

    progressWrap.style.display = "block";
    progressBar.style.width = "0%";
    progressLabel.innerText = "Uploading...";

    const xhr = new XMLHttpRequest();
    xhr.open("POST", url.toString());
    xhr.setRequestHeader("Authorization", `Bearer ${getToken()}`);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        progressBar.style.width = `${percent}%`;
        progressBar.setAttribute("aria-valuenow", percent);
        progressLabel.innerText = `Uploading... ${percent}%`;
      }
    };

    xhr.onload = async () => {
      if (xhr.status === 201) {
        const data = JSON.parse(xhr.responseText);
        progressLabel.innerText = "Extracting report text complete. Running AI analysis...";
        showToast("File uploaded successfully!", "success");
        await runAnalysis(data.report_id);
      } else {
        let detail = "Upload failed. Please try again.";
        try {
          detail = JSON.parse(xhr.responseText).detail || detail;
        } catch (_) {}
        showToast(detail, "error");
        progressWrap.style.display = "none";
      }
    };

    xhr.onerror = () => {
      showToast("Network error during upload. Is the backend running?", "error");
      progressWrap.style.display = "none";
    };

    xhr.send(formData);
  }

  async function runAnalysis(reportId) {
    showSkeletonLoading(true);
    try {
      const response = await apiRequest(`/analyze/${reportId}`, { method: "POST" });
      if (!response) return;

      if (!response.ok) {
        const err = await response.json();
        showToast(err.detail || "AI analysis failed.", "error");
        return;
      }

      const analysis = await response.json();
      showToast("AI analysis complete!", "success");
      progressWrap.style.display = "none";

      if (typeof renderAnalysis === "function") {
        renderAnalysis(analysis, reportId);
      }
      if (typeof loadRecentReports === "function") {
        loadRecentReports();
      }
    } catch (err) {
      console.error(err);
      showToast("Something went wrong while analyzing the report.", "error");
    } finally {
      showSkeletonLoading(false);
    }
  }

  function showSkeletonLoading(show) {
    const skeleton = document.getElementById("analysisSkeleton");
    const resultsArea = document.getElementById("analysisResults");
    if (skeleton) skeleton.style.display = show ? "block" : "none";
    if (resultsArea) resultsArea.style.display = show ? "none" : "block";
  }
});
