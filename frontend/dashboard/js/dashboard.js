/**
 * dashboard.js — Rapor listeleme dashboard'u
 * Raporları localStorage'dan okur, listeler, filtreler.
 * PDF/Excel'i tarayıcıda üretir, mail'i backend'e gönderir.
 */

/* ─── Dil (chat ile aynı: nexus_lang) ─────────────────────── */
const LANG = localStorage.getItem("nexus_lang") === "en" ? "en" : "tr";

const I18N = {
  tr: {
    dashboard_title: "📊 Rapor Dashboard",
    back: "← Analize Dön",
    search_ph: "Başlık veya özette ara...",
    all_sources: "Tüm kaynaklar",
    empty: "Henüz rapor yok. Önce sohbette bir analiz yapın.",
    summary: "Özet", chart: "Grafik", action_plan: "Aksiyon Planı", sql: "SQL Sorgusu",
    view: "Görüntüle", mail_send: "Gönder",
    no_summary: "Özet bulunamadı.", untitled: "İsimsiz Rapor",
    mail_ph: "ornek@mail.com",
    mail_invalid: "Geçerli bir mail adresi girin",
    mail_preparing: "PDF hazırlanıyor…",
    mail_sent: "Mail gönderildi ✔",
    mail_failed: "Mail gönderilemedi",
    pdf_downloading: "PDF indiriliyor",
    excel_downloading: "Excel indiriliyor",
  },
  en: {
    dashboard_title: "📊 Report Dashboard",
    back: "← Back to Analysis",
    search_ph: "Search in title or summary...",
    all_sources: "All sources",
    empty: "No reports yet. Run an analysis in the chat first.",
    summary: "Summary", chart: "Chart", action_plan: "Action Plan", sql: "SQL Query",
    view: "View", mail_send: "Send",
    no_summary: "No summary available.", untitled: "Untitled Report",
    mail_ph: "example@mail.com",
    mail_invalid: "Enter a valid email address",
    mail_preparing: "Preparing PDF…",
    mail_sent: "Mail sent ✔",
    mail_failed: "Mail could not be sent",
    pdf_downloading: "Downloading PDF",
    excel_downloading: "Downloading Excel",
  },
};

function tr(key) { return (I18N[LANG] && I18N[LANG][key]) || I18N.tr[key] || key; }
// Production'da aynı origin'den serve edilir (relative URL).
// Lokal geliştirmede: window.API_BASE_OVERRIDE = "http://localhost:8000/api/v1"
const API_BASE = window.API_BASE_OVERRIDE || "/api/v1";
const REPORTS_KEY = "nexus_reports"; // raporların saklandığı yer

let allReports = []; // tüm raporlar (filtresiz)

/* ─── Raporları yükle ─────────────────────────────────────── */
function loadReports() {
  try {
    const raw = localStorage.getItem(REPORTS_KEY);
    allReports = raw ? JSON.parse(raw) : [];
  } catch {
    allReports = [];
  }
  // En yeni rapor en üstte
  allReports.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
}

/* ─── Filtrele ve çiz ─────────────────────────────────────── */
function renderReports() {
  const search = document.getElementById("searchInput").value.toLowerCase();
  const source = document.getElementById("sourceFilter").value;

  const filtered = allReports.filter((r) => {
    const matchText =
      (r.title || "").toLowerCase().includes(search) ||
      (r.summary || "").toLowerCase().includes(search);
    const matchSource = !source || r.source_type === source;
    return matchText && matchSource;
  });

  const grid = document.getElementById("reportGrid");
  const empty = document.getElementById("emptyState");

  if (!filtered.length) {
    grid.innerHTML = "";
    empty.style.display = "block";
    return;
  }
  empty.style.display = "none";

  grid.innerHTML = filtered
    .map(
      (r, i) => `
    <div class="card">
      <div class="card-title">${esc(r.title || tr("untitled"))}</div>
      <div class="card-meta">
        ${r.source_type ? `<span class="badge">${esc(r.source_type)}</span>` : ""}
        <span>${formatDate(r.created_at)}</span>
      </div>
      <div class="card-summary">${esc(r.summary || tr("no_summary"))}</div>
      <div class="card-actions">
        <button class="btn btn-view"  onclick="openDetail(${i})">${tr("view")}</button>
        <button class="btn btn-pdf"   onclick="downloadPDF(${i})">PDF</button>
        <button class="btn btn-excel" onclick="downloadExcel(${i})">Excel</button>
        <button class="btn btn-mail"  onclick="toggleMail(${i})">Mail</button>
      </div>
      <div class="mail-box" id="mailbox-${i}">
        <input type="email" id="mailinput-${i}" placeholder="${tr("mail_ph")}" />
        <button class="btn btn-mail" onclick="sendMail(${i})">${tr("mail_send")}</button>
      </div>
    </div>`
    )
    .join("");

  // Filtrelenmiş listeyi index eşleşmesi için sakla
  window._filtered = filtered;
}

/* ─── Detay modalı ────────────────────────────────────────── */
function openDetail(i) {
  const r = window._filtered[i];
  const modal = document.getElementById("modalContent");

  const actions = (r.action_plan || [])
    .map((a) => `<li>${esc(typeof a === "string" ? a : a.action || "")}</li>`)
    .join("");

  modal.innerHTML = `
    <button class="modal-close" onclick="closeModal()">×</button>
    <h2>${esc(r.title || tr("report"))}</h2>
    <div class="card-meta">
      ${r.source_type ? `<span class="badge">${esc(r.source_type)}</span>` : ""}
      <span>${formatDate(r.created_at)}</span>
    </div>

    <div class="section">
      <h3>${tr("summary")}</h3>
      <p>${esc(r.summary || "—")}</p>
    </div>

    ${
      r.chart_data && r.chart_data.length
        ? `<div class="section"><h3>${tr("chart")}</h3><canvas id="detailChart" height="120"></canvas></div>`
        : ""
    }

    ${
      actions
        ? `<div class="section"><h3>${tr("action_plan")}</h3><ul>${actions}</ul></div>`
        : ""
    }

    ${
      r.sql_query
        ? `<div class="section"><h3>${tr("sql")}</h3><pre>${esc(r.sql_query)}</pre></div>`
        : ""
    }
  `;

  document.getElementById("modalBg").classList.add("open");

  // Grafiği çiz
  if (r.chart_data && r.chart_data.length) {
    drawChart("detailChart", r.chart_data);
  }
}

function closeModal() {
  document.getElementById("modalBg").classList.remove("open");
}

/* ─── Grafik çiz (Chart.js) ───────────────────────────────── */
function drawChart(canvasId, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const keys = Object.keys(data[0]);
  const labelKey = keys.find((k) => typeof data[0][k] !== "number") || keys[0];
  const valueKeys = keys.filter((k) => typeof data[0][k] === "number");

  new Chart(canvas, {
    type: "bar",
    data: {
      labels: data.map((d) => d[labelKey]),
      datasets: valueKeys.map((k, idx) => ({
        label: k,
        data: data.map((d) => d[k]),
        backgroundColor: ["#6366f1", "#22c55e", "#f59e0b"][idx % 3],
      })),
    },
    options: {
      plugins: { legend: { labels: { color: "#94a3b8" } } },
      scales: {
        x: { ticks: { color: "#94a3b8" } },
        y: { ticks: { color: "#94a3b8" } },
      },
    },
  });
}


/* ─── Rapor içeriğini PDF için hazırla (ortak) ─────────────── */
function buildReportElement(r) {
  const el = document.createElement("div");
  el.style.padding = "30px";
  el.style.fontFamily = "sans-serif";
  el.style.color = "#111";
  el.innerHTML = `
    <h1 style="color:#4f46e5">${esc(r.title || tr("report"))}</h1>
    <p style="color:#666">${formatDate(r.created_at)} · ${esc(r.source_type || "")}</p>
    <h3>${tr("summary")}</h3>
    <p>${esc(r.summary || "—")}</p>
  `;

  // ── Grafiği resim olarak ekle (varsa) ──
  if (r.chart_data && r.chart_data.length) {
    const tempCanvas = document.createElement("canvas");
    tempCanvas.width = 700;
    tempCanvas.height = 350;
    const ctx = tempCanvas.getContext("2d");
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);

    const keys = Object.keys(r.chart_data[0]);
    const labelKey = keys.find((k) => typeof r.chart_data[0][k] !== "number") || keys[0];
    const valueKeys = keys.filter((k) => typeof r.chart_data[0][k] === "number");

    const chart = new Chart(tempCanvas, {
      type: "bar",
      data: {
        labels: r.chart_data.map((d) => d[labelKey]),
        datasets: valueKeys.map((k, idx) => ({
          label: k,
          data: r.chart_data.map((d) => d[k]),
          backgroundColor: ["#6366f1", "#22c55e", "#f59e0b"][idx % 3],
        })),
      },
      options: {
        responsive: false,
        animation: false,
        plugins: { legend: { labels: { color: "#111" } } },
        scales: { x: { ticks: { color: "#111" } }, y: { ticks: { color: "#111" } } },
      },
    });

    const img = document.createElement("img");
    img.src = tempCanvas.toDataURL("image/png");
    img.style.width = "100%";
    img.style.maxWidth = "600px";
    const chartTitle = document.createElement("h3");
    chartTitle.textContent = tr("chart");
    el.appendChild(chartTitle);
    el.appendChild(img);
    chart.destroy();
  }

  // ── Aksiyon planı ──
  if ((r.action_plan || []).length) {
    const h = document.createElement("h3");
    h.textContent = tr("action_plan");
    const ul = document.createElement("ul");
    ul.innerHTML = r.action_plan
      .map((a) => `<li>${esc(typeof a === "string" ? a : a.action || "")}</li>`)
      .join("");
    el.appendChild(h);
    el.appendChild(ul);
  }

  // ── SQL ──
  if (r.sql_query) {
    const h = document.createElement("h3");
    h.textContent = tr("sql");
    const pre = document.createElement("pre");
    pre.style.cssText = "background:#f4f4f4;padding:10px;white-space:pre-wrap";
    pre.textContent = r.sql_query;
    el.appendChild(h);
    el.appendChild(pre);
  }

  return el;
}

/* ─── PDF indir ───────────────────────────────────────────── */
function downloadPDF(i) {
  const r = window._filtered[i];
  html2pdf()
    .set({ filename: `${(r.title || tr("report")).replace(/\s+/g, "_")}.pdf`, margin: 10 })
    .from(buildReportElement(r))
    .save();
  toast(tr("pdf_downloading"), "success");
}

/* ─── Excel indir (SheetJS) ───────────────────────────────── */
function downloadExcel(i) {
  const r = window._filtered[i];
  const wb = XLSX.utils.book_new();

  // 1. sayfa: özet bilgiler
  const summarySheet = XLSX.utils.json_to_sheet([
    { Alan: tr("title"), Değer: r.title || "" },
    { Alan: tr("date"), Değer: formatDate(r.created_at) },
    { Alan: tr("source"), Değer: r.source_type || "" },
    { Alan: tr("summary"), Değer: r.summary || "" },
  ]);
  XLSX.utils.book_append_sheet(wb, summarySheet, tr("summary"));

  // 2. sayfa: grafik verisi (varsa)
  if (r.chart_data && r.chart_data.length) {
    const dataSheet = XLSX.utils.json_to_sheet(r.chart_data);
    XLSX.utils.book_append_sheet(wb, dataSheet, tr("data"));
  }

  XLSX.writeFile(wb, `${(r.title || tr("report")).replace(/\s+/g, "_")}.xlsx`);
  toast(tr("excel_downloading"), "success");
}

/* ─── Mail kutusunu aç/kapat ──────────────────────────────── */
function toggleMail(i) {
  document.getElementById(`mailbox-${i}`).classList.toggle("open");
}


/* ─── Mail gönder (PDF ekli, backend → Resend) ────────────── */
async function sendMail(i) {
  const r = window._filtered[i];
  const email = document.getElementById(`mailinput-${i}`).value.trim();
  if (!email || !email.includes("@")) {
    toast(tr("mail_invalid"), "error");
    return;
  }

  toast(tr("pdf_preparing"), "success");
  try {
    // PDF'i base64 üret
    const dataUri = await html2pdf()
      .set({ margin: 10 })
      .from(buildReportElement(r))
      .outputPdf("datauristring");
    const pdfBase64 = dataUri.split(",")[1]; // önekten sonrası

    const html = `
      <h2>${esc(r.title || tr("report"))}</h2>
      <p>${esc(r.summary || "")}</p>
      <p>${tr("detailed_report")}</p>`;

    const res = await fetch(`${API_BASE}/reports/email`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        to: email,
        subject: r.title || tr("report"),
        html: html,
        pdf_base64: pdfBase64,
        filename: `${(r.title || tr("report")).replace(/\s+/g, "_")}.pdf`,
      }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    toast(tr("mail_sent"), "success");
    document.getElementById(`mailbox-${i}`).classList.remove("open");
  } catch (err) {
    toast(`${tr("mail_failed")}: ${err.message}`, "error");
  }
}

/* ─── Yardımcılar ─────────────────────────────────────────── */
function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function formatDate(iso) {
  if (!iso) return "—";
  try {
    const locale = LANG === "en" ? "en-US" : "tr-TR";
    return new Date(iso).toLocaleString(locale, {
      day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function toast(msg, type = "success") {
  const cont = document.getElementById("toasts");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  cont.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

/* ─── Başlat ──────────────────────────────────────────────── */
function init() {
  // Statik HTML metinlerini dile göre ayarla
  document.querySelector(".topbar h1").textContent = tr("dashboard_title");
  document.querySelector(".topbar a").textContent = tr("back");
  document.getElementById("searchInput").placeholder = tr("search_ph");
  document.getElementById("emptyState").textContent = tr("empty");
  const allOpt = document.querySelector('#sourceFilter option[value=""]');
  if (allOpt) allOpt.textContent = tr("all_sources");
  loadReports();
  renderReports();
  document.getElementById("searchInput").addEventListener("input", renderReports);
  document.getElementById("sourceFilter").addEventListener("change", renderReports);
  // Modalın dışına tıklayınca kapat
  document.getElementById("modalBg").addEventListener("click", (e) => {
    if (e.target.id === "modalBg") closeModal();
  });
}

document.addEventListener("DOMContentLoaded", init);