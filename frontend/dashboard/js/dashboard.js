/**
 * dashboard.js — Report Dashboard
 *
 * URL formatları:
 *   ?report_id=rpt_abc123               → authenticated (JWT gerekebilir)
 *   ?public_id=rpt_abc123              → herkese açık
 *
 * Backend endpoints:
 *   GET /api/v1/reports/public/{id}    → public (auth gereksiz)
 */

const API_BASE = "http://localhost:8000/api/v1";

/* ─── Yardımcı fonksiyonlar ───────────────────────────────── */

function _esc(s) {
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function _formatDate(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      year: "numeric", month: "long", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch { return iso; }
}

function _formatNumber(n) {
  if (typeof n !== "number") return String(n);
  if (Number.isInteger(n)) return n.toLocaleString();
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function showToast(msg, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const icons = {
    success: `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 10l5 5 8-8" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    error:   `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="10" cy="10" r="8"/><path d="M10 6v4M10 14h.01" stroke-linecap="round"/></svg>`,
    info:    `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="10" cy="10" r="8"/><path d="M10 10v4M10 6h.01" stroke-linecap="round"/></svg>`,
  };
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || icons.info}</span>
    <span class="toast-content">${_esc(msg)}</span>`;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("show"));
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 400);
  }, 4000);
}

/* ─── Durum yönetimi ──────────────────────────────────────── */

function showLoading() {
  document.getElementById("loadingState").style.display = "flex";
  document.getElementById("errorState").classList.add("hidden");
  document.getElementById("reportContainer").classList.add("hidden");
}

function showError(message) {
  document.getElementById("loadingState").style.display = "none";
  document.getElementById("errorState").classList.remove("hidden");
  document.getElementById("reportContainer").classList.add("hidden");
  document.getElementById("errorMessage").textContent = message;
}

function showReport() {
  document.getElementById("loadingState").style.display = "none";
  document.getElementById("errorState").classList.add("hidden");
  document.getElementById("reportContainer").classList.remove("hidden");
}

/* ─── API çağrısı ─────────────────────────────────────────── */

async function fetchReport(reportId, isPublic) {
  const endpoint = isPublic
    ? `/reports/public/${encodeURIComponent(reportId)}`
    : `/reports/${encodeURIComponent(reportId)}`;

  const headers = { "Content-Type": "application/json" };

  // Eğer JWT token varsa Authorization başlığı ekle
  const token = localStorage.getItem("nexus_auth_token");
  if (token && !isPublic) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, { headers });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/* ─── Dashboard render fonksiyonları ─────────────────────── */

function renderReportHeader(report) {
  // Başlık
  const titleEl = document.getElementById("reportTitle");
  if (titleEl) {
    titleEl.textContent = report.title || "Data Analysis Report";
  }

  // Tarih
  const dateEl = document.getElementById("reportDate");
  if (dateEl) {
    dateEl.textContent = _formatDate(report.created_at || new Date().toISOString());
  }

  // Kaynak bilgisi
  const sourceEl = document.getElementById("reportSource");
  if (sourceEl && report.sources_queried?.length) {
    const src = report.sources_queried[0];
    sourceEl.textContent = `${src.alias || src.source_type} · ${src.row_count?.toLocaleString() ?? "—"} rows`;
  }
}

function renderSummary(summary) {
  const el = document.getElementById("summaryContent");
  if (!el) return;
  try {
    el.innerHTML = typeof marked !== "undefined"
      ? marked.parse(summary)
      : `<p>${_esc(summary)}</p>`;
  } catch {
    el.innerHTML = `<p>${_esc(summary)}</p>`;
  }
}

function renderMetrics(report) {
  const section = document.getElementById("metricsSection");
  const grid = document.getElementById("metricsGrid");
  if (!section || !grid) return;

  const cards = [];

  // sources_queried'den metrik kartları üret
  if (report.sources_queried?.length) {
    report.sources_queried.forEach(src => {
      if (src.row_count != null) {
        cards.push({
          label: `${src.alias || src.source_type} Rows`,
          value: _formatNumber(src.row_count),
          change: null,
          success: src.success,
        });
      }
    });
  }

  // chart_data'dan sayısal metrikler çıkar
  if (report.chart_data?.length) {
    const data = report.chart_data;
    const keys = Object.keys(data[0] || {});
    const numericKeys = keys.filter(k => {
      const v = data[0][k];
      return typeof v === "number" && !["id", "index"].includes(k.toLowerCase());
    });

    numericKeys.slice(0, 3).forEach(key => {
      const values = data.map(d => Number(d[key])).filter(v => !isNaN(v));
      if (!values.length) return;
      const sum = values.reduce((a, b) => a + b, 0);
      const avg = sum / values.length;
      const max = Math.max(...values);

      cards.push({
        label: `Total ${_humanLabel(key)}`,
        value: _formatNumber(Math.round(sum)),
        change: null,
      });
      cards.push({
        label: `Avg ${_humanLabel(key)}`,
        value: _formatNumber(Math.round(avg * 100) / 100),
        change: null,
      });
      cards.push({
        label: `Peak ${_humanLabel(key)}`,
        value: _formatNumber(max),
        change: null,
      });
    });
  }

  if (!cards.length) return;

  section.style.display = "";
  grid.innerHTML = cards.slice(0, 6).map(card => `
    <div class="metric-card">
      <div class="metric-label">${_esc(card.label)}</div>
      <div class="metric-value">${_esc(String(card.value))}</div>
      ${card.change != null
        ? `<div class="metric-change ${card.change >= 0 ? "positive" : "negative"}">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
              ${card.change >= 0
                ? '<path d="M8 12V4M4 8l4-4 4 4" stroke-linecap="round" stroke-linejoin="round"/>'
                : '<path d="M8 4v8M4 8l4 4 4-4" stroke-linecap="round" stroke-linejoin="round"/>'
              }
            </svg>
            ${Math.abs(card.change)}%
          </div>`
        : ""
      }
    </div>`).join("");
}

function renderChart(reportData) {
  const section = document.getElementById("chartSection");
  if (!section) return;
  if (!reportData.chart_data?.length) return;

  section.style.display = "";
  const wrapper = document.getElementById("chartWrapper");
  if (!wrapper) return;

  // chart.js'in renderChart fonksiyonunu kullan (chat modülünden paylaşılan)
  if (typeof window.renderChart === "function") {
    const canvas = document.getElementById("reportChart");
    if (canvas) {
      const container = canvas.parentElement;
      container.innerHTML = "";
      window.renderChart(container, reportData.chart_data, "dashboard-main");
    }
  } else {
    // Fallback: Chart.js doğrudan kullan
    _renderFallbackChart(reportData.chart_data);
  }
}

function _renderFallbackChart(data) {
  if (!data?.length) return;
  const canvas = document.getElementById("reportChart");
  if (!canvas) return;

  const keys = Object.keys(data[0]);
  const numKeys = keys.filter(k => typeof data[0][k] === "number");
  const labelKey = keys.find(k => !numKeys.includes(k)) || keys[0];
  if (!numKeys.length) return;

  const PALETTE = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#a855f7"];
  const labels = data.map(r => String(r[labelKey]));
  const isTime = ["date","month","year","week","day","period"].some(w =>
    labelKey.toLowerCase().includes(w)
  );

  new Chart(canvas, {
    type: isTime ? "line" : "bar",
    data: {
      labels,
      datasets: numKeys.map((k, i) => ({
        label: _humanLabel(k),
        data: data.map(r => Number(r[k])),
        borderColor: PALETTE[i % PALETTE.length],
        backgroundColor: PALETTE[i % PALETTE.length] + (isTime ? "22" : "cc"),
        borderWidth: 2,
        borderRadius: isTime ? 0 : 5,
        tension: 0.38,
        fill: isTime && numKeys.length === 1,
        pointRadius: data.length < 25 ? 4 : 2,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 420 },
      plugins: {
        legend: {
          labels: { color: "#94a3b8", font: { size: 11 } },
        },
        tooltip: {
          backgroundColor: "#0d0f1a",
          titleColor: "#f1f5f9",
          bodyColor: "#94a3b8",
        },
      },
      scales: {
        x: { ticks: { color: "#475569" }, grid: { color: "rgba(255,255,255,.04)" } },
        y: { ticks: { color: "#475569" }, grid: { color: "rgba(255,255,255,.04)" } },
      },
    },
  });
}

function renderActionPlan(actionPlan) {
  const section = document.getElementById("actionSection");
  const list = document.getElementById("actionList");
  if (!section || !list || !actionPlan?.length) return;

  section.style.display = "";

  const priorityOrder = ["high", "medium", "low", ""];
  list.innerHTML = actionPlan.map((item, i) => {
    // Öncelik tespiti
    const text = typeof item === "string" ? item : (item.action || String(item));
    const priority = typeof item === "object" ? (item.priority || "").toLowerCase() : "";
    const priorityBadge = ["high", "medium", "low"].includes(priority)
      ? `<span class="action-priority ${priority}">${priority}</span>`
      : "";

    return `
      <div class="action-item">
        <div class="action-number">${i + 1}</div>
        <div class="action-content">
          <div class="action-text">${_esc(text)}</div>
          ${priorityBadge}
        </div>
      </div>`;
  }).join("");
}

function renderSqlSection(sqlQuery) {
  const section = document.getElementById("sqlSection");
  const codeEl = document.getElementById("sqlQuery");
  if (!section || !codeEl || !sqlQuery) return;

  section.style.display = "";
  codeEl.textContent = sqlQuery;
}

/* ─── Collapsible SQL section ─────────────────────────────── */

function _initCollapsible() {
  const header = document.getElementById("sqlHeader");
  const content = document.getElementById("sqlContent");
  if (!header || !content) return;

  header.addEventListener("click", () => {
    const isCollapsed = content.classList.contains("collapsed");
    content.classList.toggle("collapsed", !isCollapsed);
    header.classList.toggle("collapsed", !isCollapsed);
  });
}

/* ─── Share button ────────────────────────────────────────── */

function _initShareButton(reportId) {
  const btn = document.getElementById("btnShare");
  if (!btn) return;

  btn.addEventListener("click", () => {
    const shareUrl = window.location.href;
    navigator.clipboard.writeText(shareUrl).then(() => {
      showToast("Report link copied to clipboard!", "success");
      const origText = btn.querySelector("span").textContent;
      btn.querySelector("span").textContent = "Copied!";
      setTimeout(() => { btn.querySelector("span").textContent = origText; }, 2000);
    }).catch(() => {
      showToast("Could not copy. Use the address bar to share.", "info");
    });
  });
}

/* ─── Export button ───────────────────────────────────────── */

function _initExportButton(report) {
  const btn = document.getElementById("btnExport");
  if (!btn) return;

  btn.addEventListener("click", () => {
    try {
      const content = {
        title: report.title || "Report",
        date: _formatDate(report.created_at),
        summary: report.summary,
        action_plan: report.action_plan || [],
        sql_query: report.sql_query,
        sources: report.sources_queried,
      };
      const blob = new Blob(
        [JSON.stringify(content, null, 2)],
        { type: "application/json" }
      );
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `nexus-report-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
      showToast("Report exported as JSON", "success");
    } catch {
      showToast("Export failed. Please try again.", "error");
    }
  });
}

/* ─── Copy SQL ────────────────────────────────────────────── */

function _initCopySql(sql) {
  const btn = document.getElementById("btnCopySql");
  if (!btn || !sql) return;

  btn.addEventListener("click", () => {
    navigator.clipboard.writeText(sql).then(() => {
      const orig = btn.querySelector("span") ? btn.querySelector("span").textContent : btn.textContent;
      btn.textContent = "Copied!";
      setTimeout(() => { btn.textContent = "Copy"; }, 2000);
      showToast("SQL query copied", "success");
    });
  });
}

/* ─── Yardımcı: human-readable label ─────────────────────── */

function _humanLabel(key) {
  return key
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, c => c.toUpperCase());
}

/* ─── Ana giriş noktası ───────────────────────────────────── */

async function init() {
  showLoading();

  // URL parametrelerini oku
  const params = new URLSearchParams(window.location.search);
  const publicId = params.get("public_id");
  const reportId = params.get("report_id");

  const id = publicId || reportId;
  const isPublic = Boolean(publicId);

  if (!id) {
    showError("No report ID provided. Please generate a report first.");
    return;
  }

  try {
    const report = await fetchReport(id, isPublic);

    // Raporun başlık meta bilgilerini doldur (sadece public endpoint
    // ChatResponse döndürdüğünden title ve created_at olmayabilir)
    report.title = report.title
      || (document.URL.includes("public_id") ? "Shared Report" : "Analysis Report");
    report.created_at = report.created_at || new Date().toISOString();

    renderReportHeader(report);
    renderSummary(report.summary || "No summary available.");
    renderMetrics(report);
    renderChart(report);
    renderActionPlan(report.action_plan);
    renderSqlSection(report.sql_query);

    _initCollapsible();
    _initShareButton(id);
    _initExportButton(report);
    _initCopySql(report.sql_query);

    showReport();

    // Sayfa başlığını güncelle
    document.title = `${report.title} — Nexus Analytics`;
  } catch (err) {
    if (err.message?.includes("not public") || err.message?.includes("403")) {
      showError("This report is private and cannot be accessed without authorization.");
    } else if (err.message?.includes("404") || err.message?.includes("not found")) {
      showError("Report not found. It may have been deleted or the link is invalid.");
    } else {
      showError(`Failed to load report: ${err.message}`);
    }
  }
}

document.addEventListener("DOMContentLoaded", init);
