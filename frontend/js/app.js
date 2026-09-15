(() => {
  const form = document.getElementById("audit-form");
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const fileNameEl = document.getElementById("file-name");
  const submitBtn = document.getElementById("submit-btn");
  const errorMessageEl = document.getElementById("error-message");
  const statusSection = document.getElementById("status-section");
  const resultsSection = document.getElementById("results-section");
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

  // Render only the Markdown constructs allowed by the audit report contract.
  function renderReport(text) {
    const escapeHtml = (value) =>
      value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

    const parseTableRow = (line) => {
      const content = line.replace(/^\s*\|/, "").replace(/\|\s*$/, "");
      const cells = [];
      let cell = "";

      for (let index = 0; index < content.length; index += 1) {
        if (content[index] === "\\" && content[index + 1] === "|") {
          cell += "|";
          index += 1;
        } else if (content[index] === "|") {
          cells.push(cell.trim());
          cell = "";
        } else {
          cell += content[index];
        }
      }
      cells.push(cell.trim());
      return cells;
    };

    const isTableDivider = (line) =>
      /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);

    const lines = text.split("\n");
    const html = [];
    let listType = null;

    const closeList = () => {
      if (listType) {
        html.push(`</${listType}>`);
        listType = null;
      }
    };

    const openList = (type, className = "") => {
      if (listType !== type) {
        closeList();
        html.push(`<${type}${className ? ` class="${className}"` : ""}>`);
        listType = type;
      }
    };

    for (let index = 0; index < lines.length; index += 1) {
      const rawLine = lines[index];
      const line = rawLine.trim();

      if (!line) {
        closeList();
        continue;
      }

      if (line.startsWith("|") && isTableDivider(lines[index + 1] || "")) {
        closeList();
        const headers = parseTableRow(line);
        index += 2;
        const rows = [];
        while (index < lines.length && lines[index].trim().startsWith("|")) {
          rows.push(parseTableRow(lines[index]));
          index += 1;
        }
        index -= 1;

        html.push('<div class="report-table"><table><thead><tr>');
        headers.forEach((header) => {
          html.push(`<th scope="col">${formatInline(escapeHtml(header))}</th>`);
        });
        html.push("</tr></thead><tbody>");
        rows.forEach((row) => {
          html.push("<tr>");
          headers.forEach((header, cellIndex) => {
            html.push(
              `<td data-label="${escapeHtml(header)}">${formatInline(
                escapeHtml(row[cellIndex] || "")
              )}</td>`
            );
          });
          html.push("</tr>");
        });
        html.push("</tbody></table></div>");
        continue;
      }

      const headingMatch = line.match(/^(#{1,3})\s+(.*)/);
      if (headingMatch) {
        closeList();
        const level = Math.min(headingMatch[1].length + 1, 4);
        html.push(
          `<h${level}>${formatInline(escapeHtml(headingMatch[2]))}</h${level}>`
        );
        continue;
      }

      if (/^(?:-{3,}|\*{3,}|_{3,})$/.test(line)) {
        closeList();
        html.push("<hr>");
        continue;
      }

      const blockquoteMatch = line.match(/^>\s?(.*)/);
      if (blockquoteMatch) {
        closeList();
        html.push(`<blockquote>${formatInline(escapeHtml(blockquoteMatch[1]))}</blockquote>`);
        continue;
      }

      const checkboxMatch = line.match(/^[-*]\s+\[([ xX])\]\s+(.*)/);
      if (checkboxMatch) {
        openList("ul", "report-checklist");
        const checked = checkboxMatch[1].toLowerCase() === "x";
        html.push(
          `<li><input type="checkbox" disabled${checked ? " checked" : ""}>` +
            `<span>${formatInline(escapeHtml(checkboxMatch[2]))}</span></li>`
        );
        continue;
      }

      const listMatch = line.match(/^[-*]\s+(.*)/);
      if (listMatch) {
        openList("ul");
        html.push(`<li>${formatInline(escapeHtml(listMatch[1]))}</li>`);
        continue;
      }

      const orderedMatch = line.match(/^\d+[.)]\s+(.*)/);
      if (orderedMatch) {
        openList("ol");
        html.push(`<li>${formatInline(escapeHtml(orderedMatch[1]))}</li>`);
        continue;
      }

      closeList();
      html.push(`<p>${formatInline(escapeHtml(line))}</p>`);
    }
    closeList();

    return html.join("\n");
  }

  function formatInline(text) {
    let result = text
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<code>$1</code>");

    result = result.replace(
      /\b(Needs Human Review|Critical|Serious|High|Moderate|Medium|Minor|Low)\b/g,
      (match) => {
        const severityClass = match.toLowerCase().replaceAll(" ", "-");
        return `<span class="severity-${severityClass}">${match}</span>`;
      }
    );

    result = result.replace(/\b(PASS|PARTIAL|FAIL)\b/g, (match) => {
      return `<span class="compliance-${match.toLowerCase()}">${match}</span>`;
    });

    result = result.replace(
      /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
      '<a href="$2">$1</a>'
    );

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
      reportOutputEl.innerHTML = renderReport(lastReportText);
      statusSection.hidden = true;
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
