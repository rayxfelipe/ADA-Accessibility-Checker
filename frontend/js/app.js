(() => {
  const form = document.getElementById("audit-form");
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const fileNameEl = document.getElementById("file-name");
  const submitBtn = document.getElementById("submit-btn");
  const errorMessageEl = document.getElementById("error-message");
  const statusSection = document.getElementById("status-section");
  const statusMessageEl = statusSection.querySelector("p");
  const resultsSection = document.getElementById("results-section");
  const reportFileNameEl = document.getElementById("report-file-name");
  const reportKpisEl = document.getElementById("report-kpis");
  const reportSummaryEl = document.getElementById("report-summary");
  const checkerOutputEl = document.getElementById("checker-output");
  const failuresOutputEl = document.getElementById("failures-output");
  const manualOutputEl = document.getElementById("manual-output");
  const copyBtn = document.getElementById("copy-btn");
  const printReportBtn = document.getElementById("print-report");
  const remediationJsonBtn = document.getElementById("remediation-json");

  const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024;
  const DEFAULT_SUBMIT_LABEL = "Run Accessibility Audit";
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
    setSelectedFile(event.dataTransfer.files[0]);
  });

  function escapeHtml(value) {
    return value
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatInline(value) {
    return escapeHtml(value)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(
        /\b(Passed|Failed|Needs manual check|Skipped)\b/g,
        (status) => `<span class="rule-status status-${status.toLowerCase().replaceAll(" ", "-")}">${status}</span>`
      );
  }

  function parseTableRow(line) {
    return line
      .replace(/^\s*\|/, "")
      .replace(/\|\s*$/, "")
      .split(/(?<!\\)\|/)
      .map((cell) => cell.replace(/\\\|/g, "|").trim());
  }

  function isTableDivider(line) {
    return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
  }

  function renderMarkdown(text) {
    const lines = text.trim().split("\n");
    const html = [];
    let listType = null;

    const closeList = () => {
      if (listType) html.push(`</${listType}>`);
      listType = null;
    };

    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index].trim();
      if (!line) {
        closeList();
        continue;
      }

      if (line.startsWith("|") && isTableDivider(lines[index + 1] || "")) {
        closeList();
        const headers = parseTableRow(line);
        const rows = [];
        index += 2;
        while (index < lines.length && lines[index].trim().startsWith("|")) {
          rows.push(parseTableRow(lines[index]));
          index += 1;
        }
        index -= 1;
        html.push('<div class="report-table"><table><thead><tr>');
        headers.forEach((header) => html.push(`<th scope="col">${formatInline(header)}</th>`));
        html.push("</tr></thead><tbody>");
        rows.forEach((row) => {
          html.push("<tr>");
          headers.forEach((header, cellIndex) => {
            html.push(`<td data-label="${escapeHtml(header)}">${formatInline(row[cellIndex] || "")}</td>`);
          });
          html.push("</tr>");
        });
        html.push("</tbody></table></div>");
        continue;
      }

      const heading = line.match(/^#{1,6}\s+(.*)/);
      if (heading) {
        closeList();
        html.push(`<h4>${formatInline(heading[1])}</h4>`);
        continue;
      }

      const ordered = line.match(/^\d+[.)]\s+(.*)/);
      const bullet = line.match(/^[-*]\s+(.*)/);
      if (ordered || bullet) {
        const nextListType = ordered ? "ol" : "ul";
        if (listType !== nextListType) {
          closeList();
          listType = nextListType;
          html.push(`<${listType}>`);
        }
        html.push(`<li>${formatInline((ordered || bullet)[1])}</li>`);
        continue;
      }

      closeList();
      html.push(`<p>${formatInline(line)}</p>`);
    }
    closeList();
    return html.join("");
  }

  function getField(report, label) {
    const escapedLabel = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const match = report.match(new RegExp(`^\\*\\*${escapedLabel}:\\*\\*\\s*(.+)$`, "im"));
    return match ? match[1].trim() : "Not reported";
  }

  function getSection(report, heading, nextHeading) {
    const startPattern = new RegExp(`^#{1,6}\\s+${heading}\\s*$`, "im");
    const start = startPattern.exec(report);
    if (!start) return "";
    const contentStart = start.index + start[0].length;
    const remainder = report.slice(contentStart);
    const end = nextHeading
      ? new RegExp(`^#{1,6}\\s+${nextHeading}\\s*$`, "im").exec(remainder)
      : null;
    return remainder.slice(0, end ? end.index : undefined).trim();
  }

  function findSummaryRows(report) {
    const lines = report.split("\n");
    for (let index = 0; index < lines.length - 1; index += 1) {
      if (!lines[index].includes("| Rule |") || !isTableDivider(lines[index + 1])) continue;
      const rows = [];
      index += 2;
      while (index < lines.length && lines[index].trim().startsWith("|")) {
        const [rule, severity, status] = parseTableRow(lines[index]);
        rows.push({ rule, severity, status });
        index += 1;
      }
      return rows;
    }
    return [];
  }

  function renderCheckerTree(treeText) {
    const content = treeText.replace(/^```[^\n]*\n?/, "").replace(/\n?```\s*$/, "");
    const groups = [];
    let group = null;
    let rule = null;

    content.split("\n").forEach((line) => {
      if (/^\S/.test(line)) {
        group = { title: line.trim(), rules: [] };
        groups.push(group);
        rule = null;
        return;
      }
      const ruleMatch = line.match(/^\s{2}(.+?) - (Passed|Failed|Needs manual check|Skipped)\s*$/);
      if (ruleMatch && group) {
        rule = { name: ruleMatch[1], status: ruleMatch[2], details: [] };
        group.rules.push(rule);
        return;
      }
      if (/^\s{4}\S/.test(line) && rule) rule.details.push(line.trim());
    });

    if (!groups.length) return `<div class="report-card report-output">${renderMarkdown(treeText)}</div>`;

    return groups.map((item) => `
      <article class="checker-group">
        <h4>${escapeHtml(item.title)}</h4>
        <ul class="checker-rules">
          ${item.rules.map((itemRule) => `
            <li class="checker-rule">
              <div><span>${escapeHtml(itemRule.name)}</span>${formatInline(itemRule.status)}</div>
              ${itemRule.details.length ? `<ul class="rule-details">${itemRule.details.map((detail) => `<li>${escapeHtml(detail)}</li>`).join("")}</ul>` : ""}
            </li>`).join("")}
        </ul>
      </article>`).join("");
  }

  function renderDashboard(report) {
    const standards = getField(report, "Standards Applied");
    const rows = findSummaryRows(report);
    const count = (value) => rows.filter((row) => row.status.includes("Failed") && row.severity.includes(value)).length;
    const manualCount = rows.filter((row) => row.status.includes("Needs manual check")).length;
    const passedCount = rows.filter((row) => row.status.includes("Passed")).length;
    const metrics = [
      [count("Blocker"), "Blocker", "critical"],
      [count("Critical"), "Critical", "serious"],
      [count("Major"), "Major", "moderate"],
      [manualCount, "Manual checks", "review"],
      [passedCount, "Passed", "minor"],
    ];

    reportKpisEl.innerHTML = metrics.map(([value, label, style]) => `
      <div class="report-card report-kpi ${style}"><strong>${value}</strong><span>${label}</span></div>`).join("");
    reportSummaryEl.innerHTML = `
      <dl class="audit-metadata">
        <div><dt>Standards applied</dt><dd>${formatInline(standards)}</dd></div>
      </dl>`;

    const tree = getSection(report, "ACCESSIBILITY CHECKER TREE(?:\\s+—.*)?", "Failures table");
    const failures = getSection(report, "Failures table", "Manual Verification Queue");
    const manual = getSection(report, "Manual Verification Queue");
    checkerOutputEl.innerHTML = renderCheckerTree(tree || "Checker tree was not returned.");
    failuresOutputEl.innerHTML = failures ? renderMarkdown(failures) : '<p class="empty-state">No failed rules were reported.</p>';
    manualOutputEl.innerHTML = manual ? renderMarkdown(manual) : '<p class="empty-state">No manual verification items were reported.</p>';
  }

  async function readResponse(response, fallbackMessage) {
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || `${fallbackMessage} (HTTP ${response.status}).`);
    }
    return data;
  }

  async function waitForAudit(jobId) {
    while (true) {
      const response = await fetch(`/api/audit/${encodeURIComponent(jobId)}`);
      const job = await readResponse(response, "Could not check the audit status");
      if (job.status === "completed") return job;
      if (job.status === "failed") throw new Error(job.error || "The audit failed.");
      statusMessageEl.textContent = job.status === "running"
        ? "Analyzing the PDF for accessibility issues..."
        : "Your audit is queued...";
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!selectedFile) return;

    const auditedFile = selectedFile;
    const formData = new FormData();
    formData.append("file", auditedFile);

    clearError();
    resultsSection.hidden = true;
    statusSection.hidden = false;
    form.setAttribute("aria-busy", "true");
    submitBtn.disabled = true;
    submitBtn.textContent = "Running audit...";

    try {
      const response = await fetch("/api/audit", {
        method: "POST",
        body: formData,
      });
      let data = await readResponse(response, "The audit request failed");
      if (response.status === 202 && data.jobId) data = await waitForAudit(data.jobId);

      lastReportText = data.report || "No audit result was returned.";
      reportFileNameEl.textContent = data.filename || auditedFile.name;
      renderDashboard(lastReportText);
      resultsSection.hidden = false;
      resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      showError(error.message || "Something went wrong while auditing the document.");
    } finally {
      statusSection.hidden = true;
      statusMessageEl.textContent = "Auditing document... this may take a moment.";
      form.removeAttribute("aria-busy");
      submitBtn.disabled = false;
      submitBtn.textContent = DEFAULT_SUBMIT_LABEL;
    }
  });

  copyBtn.addEventListener("click", async () => {
    if (!lastReportText) return;

    try {
      await navigator.clipboard.writeText(lastReportText);
      copyBtn.textContent = "Copied!";
      setTimeout(() => {
        copyBtn.textContent = "Copy result";
      }, 2000);
    } catch {
      showError("Could not copy the result to the clipboard.");
    }
  });

  printReportBtn.addEventListener("click", () => window.print());

  remediationJsonBtn.addEventListener("click", () => {
    if (!lastReportText) return;

    const auditedFileName = reportFileNameEl.textContent.trim() || "accessibility-audit";
    const downloadName = `${auditedFileName.replace(/\.pdf$/i, "")}-remediation.json`;
    const remediationJson = JSON.stringify({
      fileName: auditedFileName,
      remediationReport: lastReportText,
    }, null, 2);
    const downloadUrl = URL.createObjectURL(new Blob([remediationJson], { type: "application/json" }));
    const downloadLink = document.createElement("a");
    downloadLink.href = downloadUrl;
    downloadLink.download = downloadName;
    downloadLink.click();
    URL.revokeObjectURL(downloadUrl);
  });
})();
