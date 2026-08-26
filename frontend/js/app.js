(() => {
  const form = document.getElementById("audit-form");
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const fileNameEl = document.getElementById("file-name");
  const submitBtn = document.getElementById("submit-btn");
  const errorMessageEl = document.getElementById("error-message");
  const statusSection = document.getElementById("status-section");
  const resultsSection = document.getElementById("results-section");
  const resultsFilenameEl = document.getElementById("results-filename");
  const reportOutputEl = document.getElementById("report-output");
  const copyBtn = document.getElementById("copy-btn");

  const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024;
  let selectedFile = null;
  let lastReportText = "";

  function showError(message) {
    errorMessageEl.textContent = message;
    errorMessageEl.hidden = false;
  }

  function clearError() {
    errorMessageEl.textContent = "";
    errorMessageEl.hidden = true;
  }

  function setSelectedFile(file) {
    if (!file) return;

    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      showError("Only PDF files are supported.");
      return;
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      showError("File exceeds the 25MB size limit.");
      return;
    }

    clearError();
    selectedFile = file;
    fileNameEl.textContent = `Selected: ${file.name}`;
    submitBtn.disabled = false;
  }

  fileInput.addEventListener("change", (event) => {
    setSelectedFile(event.target.files[0]);
  });

  dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput.click();
    }
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    setSelectedFile(file);
  });

  // Minimal, safe markdown-ish renderer: escapes HTML first, then applies a
  // small set of formatting rules so the agent's response reads well.
  function renderReport(text) {
    const escapeHtml = (value) =>
      value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    const escaped = escapeHtml(text);
    const lines = escaped.split("\n");
    const html = [];
    let inList = false;

    const closeList = () => {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
    };

    for (const rawLine of lines) {
      const line = rawLine.trim();

      if (!line) {
        closeList();
        continue;
      }

      const headingMatch = line.match(/^(#{1,3})\s+(.*)/);
      if (headingMatch) {
        closeList();
        const level = headingMatch[1].length + 2; // start at h3
        html.push(`<h${level}>${formatInline(headingMatch[2])}</h${level}>`);
        continue;
      }

      const listMatch = line.match(/^[-*]\s+(.*)/);
      if (listMatch) {
        if (!inList) {
          html.push("<ul>");
          inList = true;
        }
        html.push(`<li>${formatInline(listMatch[1])}</li>`);
        continue;
      }

      closeList();
      html.push(`<p>${formatInline(line)}</p>`);
    }
    closeList();

    return html.join("\n");
  }

  function formatInline(text) {
    let result = text
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<code>$1</code>");

    result = result.replace(/\b(Critical|Serious|Moderate|Minor)\b/g, (match) => {
      return `<span class="severity-${match.toLowerCase()}">${match}</span>`;
    });

    return result;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!selectedFile) return;

    clearError();
    resultsSection.hidden = true;
    statusSection.hidden = false;
    submitBtn.disabled = true;

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch("/api/audit", {
        method: "POST",
        body: formData,
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || "The audit request failed.");
      }

      lastReportText = data.report || "";
      resultsFilenameEl.textContent = `Document: ${data.filename}`;
      reportOutputEl.innerHTML = renderReport(lastReportText);
      resultsSection.hidden = false;
    } catch (error) {
      showError(error.message || "Something went wrong while auditing the document.");
    } finally {
      statusSection.hidden = true;
      submitBtn.disabled = false;
    }
  });

  copyBtn.addEventListener("click", async () => {
    if (!lastReportText) return;
    try {
      await navigator.clipboard.writeText(lastReportText);
      copyBtn.textContent = "Copied!";
      setTimeout(() => {
        copyBtn.textContent = "Copy report";
      }, 2000);
    } catch {
      showError("Could not copy the report to the clipboard.");
    }
  });
})();
