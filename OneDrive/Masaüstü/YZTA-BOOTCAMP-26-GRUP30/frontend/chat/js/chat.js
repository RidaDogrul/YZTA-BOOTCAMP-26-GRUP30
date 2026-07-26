/**
 * chat.js — Mesaj render + localStorage geçmişi + toast
 */

const STORAGE_KEY = "nexus_history";
let messageHistory = [];
let _msgCounter = 0;
const TYPING_ID = "typing-row";

/* ── DOM helpers ─────────────────────────────────────────── */
const $msg  = () => document.getElementById("messages");
const $empty = () => document.getElementById("emptyState");

function _setEmptyVisible(show) {
  const e = $empty(), m = $msg();
  if (!e || !m) return;
  e.style.display  = show ? "flex"  : "none";
  m.style.display  = show ? "none"  : "flex";
}

function _newId() { return `m${Date.now()}_${++_msgCounter}`; }

function _time(iso) {
  try { return new Date(iso).toLocaleTimeString("tr-TR", { hour:"2-digit", minute:"2-digit" }); }
  catch { return ""; }
}

function _esc(s) {
  return String(s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}

function _scrollBottom() {
  const el = $msg();
  if (el) requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; });
}

/* ── History ─────────────────────────────────────────────── */
function _loadHistory() {
  try { const r = localStorage.getItem(STORAGE_KEY); if (r) messageHistory = JSON.parse(r); }
  catch { messageHistory = []; }
}

function _saveHistory() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(messageHistory.slice(-60))); }
  catch { /* storage full */ }
}

function clearHistory() {
  messageHistory = [];
  localStorage.removeItem(STORAGE_KEY);
  const m = $msg();
  if (m) m.innerHTML = "";
  _setEmptyVisible(true);
}

function restoreHistory() {
  _loadHistory();
  if (!messageHistory.length) return;
  _setEmptyVisible(false);
  messageHistory.forEach(entry => {
    if (entry.role === "user") _renderUser(entry);
    else _renderAgent(entry);
  });
  _scrollBottom();
}

/* ── User message ────────────────────────────────────────── */
function addUserMessage(text) {
  _setEmptyVisible(false);
  const entry = { id: _newId(), role: "user", text, ts: new Date().toISOString() };
  messageHistory.push(entry);
  _saveHistory();
  _renderUser(entry);
  _scrollBottom();
}

function _renderUser({ id, text, ts }) {
  const row = document.createElement("div");
  row.className = "msg-row user"; row.dataset.id = id;
  row.innerHTML = `
    <div class="msg-bubble">
      <div class="msg-text">${_esc(text)}</div>
      <span class="msg-time">${_time(ts)}</span>
    </div>`;
  $msg().appendChild(row);
}

/* ── Typing indicator ────────────────────────────────────── */
function showTyping() {
  if (document.getElementById(TYPING_ID)) return;
  const row = document.createElement("div");
  row.className = "msg-row agent"; row.id = TYPING_ID;
  const typingLabel = typeof t === "function" ? t("chat.typing") : "Analiz ediliyor";
  row.innerHTML = `
    <div class="msg-bubble">
      <div class="typing-bubble" aria-label="${typingLabel}">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>`;
  $msg().appendChild(row);
  _scrollBottom();
}

/* Pipeline progress steps */
function getSteps() {
  return [
    { key:"schema",  label: typeof t === "function" ? t("proc.schema") : "Şema okunuyor" },
    { key:"sql",     label: typeof t === "function" ? t("proc.sql") : "Sorgu oluşturuluyor" },
    { key:"execute", label: typeof t === "function" ? t("proc.execute") : "Veri çekiliyor" },
    { key:"clean",   label: typeof t === "function" ? t("proc.clean") : "Veri temizleniyor" },
    { key:"insight", label: typeof t === "function" ? t("proc.insight") : "Analiz hazırlanıyor" },
  ];
}

function showProcessing() {
  const old = document.getElementById(TYPING_ID);
  if (old) old.remove();
  const row = document.createElement("div");
  row.className = "msg-row agent"; row.id = TYPING_ID;
  const steps = getSteps().map((s, i) => `
    <div class="proc-step ${i===0?"active":""}" id="step-${s.key}">
      <span class="proc-icon">
        ${i===0 ? '<div class="proc-spin"></div>' : '<div class="proc-dot"></div>'}
      </span>
      <span>${s.label}</span>
    </div>`).join("");
  row.innerHTML = `
    <div class="msg-bubble">
      <div class="processing-steps">${steps}</div>
    </div>`;
  $msg().appendChild(row);
  _scrollBottom();
}

function advanceStep(stepKey) {
  const steps = getSteps();
  const idx = steps.findIndex(s => s.key === stepKey);
  if (idx < 0) return;
  // Mark previous done
  steps.slice(0, idx).forEach(s => {
    const el = document.getElementById(`step-${s.key}`);
    if (el) { el.className = "proc-step done"; el.querySelector(".proc-icon").innerHTML = '<span class="proc-check">✓</span>'; }
  });
  // Mark current active
  const cur = document.getElementById(`step-${stepKey}`);
  if (cur) { cur.className = "proc-step active"; cur.querySelector(".proc-icon").innerHTML = '<div class="proc-spin"></div>'; }
  // Mark remaining idle
  steps.slice(idx + 1).forEach(s => {
    const el = document.getElementById(`step-${s.key}`);
    if (el) { el.className = "proc-step"; el.querySelector(".proc-icon").innerHTML = '<div class="proc-dot"></div>'; }
  });
  _scrollBottom();
}

function hideTyping() {
  const el = document.getElementById(TYPING_ID);
  if (el) el.remove();
}

/* ── Agent message ───────────────────────────────────────── */
function addAgentMessage(response) {
  const id = _newId();
  const ts = new Date().toISOString();
  const entry = {
    id, role:"agent",
    text:       response.summary,
    sql:        response.sql_query || null,
    chartData:  response.chart_data || [],
    actionPlan: response.action_plan || [],
    ts,
  };
  messageHistory.push(entry);
  _saveHistory();
  _renderAgent(entry);
  _scrollBottom();
}

function _renderAgent({ id, text, sql, chartData, actionPlan, ts }) {
  const row = document.createElement("div");
  row.className = "msg-row agent"; row.dataset.id = id;

  // Markdown render (guarded)
  let summaryHtml;
  try { summaryHtml = typeof marked !== "undefined" ? marked.parse(text) : _esc(text); }
  catch { summaryHtml = _esc(text); }

  let inner = `<div class="msg-bubble">
    <div class="msg-text">${summaryHtml}</div>`;

  // SQL block
  if (sql) {
    const sqlQueryText = typeof t === "function" ? t("response.sql_query") : "SQL Sorgusu";
    const copyText = typeof t === "function" ? t("response.copy") : "📋 Kopyala";
    inner += `
      <div class="msg-sql">
        <div class="msg-sql-header">
          <span>${sqlQueryText}</span>
          <button class="copy-btn" data-sql="${_esc(sql)}">${copyText}</button>
        </div>
        <pre>${_esc(sql)}</pre>
      </div>`;
  }

  // Chart placeholder
  if (Array.isArray(chartData) && chartData.length > 0) {
    const chartTitle = typeof t === "function" ? t("response.chart") : "📊 Veri Görselleştirme";
    inner += `
      <div class="msg-chart">
        <div class="msg-chart-title">${chartTitle}</div>
        <div data-chart="${id}"></div>
      </div>`;
  }

  // Action plan — her madde tıklanabilir buton
  if (Array.isArray(actionPlan) && actionPlan.length > 0) {
    const actionTitle = typeof t === "function" ? t("response.action_plan") : "💡 Önerilen Adımlar — Tıklayarak Uygula";
    const items = actionPlan.map((item, idx) => `
      <li>
        <button class="action-btn" data-q="${_esc(item)}" type="button"
                title="Bu adımı analiz et: ${_esc(item)}">
          <span class="action-btn-num">${idx + 1}</span>
          <span>${_esc(item)}</span>
          <span class="action-btn-arrow">→</span>
        </button>
      </li>`).join("");
    inner += `
      <div class="msg-actions">
        <div class="msg-actions-title">${actionTitle}</div>
        <ol>${items}</ol>
      </div>`;
  }

  inner += `<span class="msg-time">${_time(ts)}</span></div>`;
  row.innerHTML = inner;
  $msg().appendChild(row);

  // Render chart after DOM insertion
  if (Array.isArray(chartData) && chartData.length > 0) {
    const wrapper = row.querySelector(`[data-chart="${id}"]`);
    if (wrapper) renderChart(wrapper, chartData, id);
  }

  // Copy handler
  row.querySelectorAll(".copy-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      navigator.clipboard.writeText(btn.dataset.sql).then(() => {
        const copiedText = typeof t === "function" ? t("response.copied") : "✅ Kopyalandı";
        const copyText = typeof t === "function" ? t("response.copy") : "📋 Kopyala";
        btn.textContent = copiedText;
        setTimeout(() => (btn.textContent = copyText), 2000);
      });
    });
  });

  // Action plan — tıklayınca soruyu input'a yaz ve gönder
  row.querySelectorAll(".action-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const question = btn.dataset.q;
      if (!question) return;

      // app.js'deki State ve handleSend'e erişim
      if (typeof State === "undefined" || !State.isConnected) {
        const connectFirstText = typeof t === "function" ? t("toast.connect_first") : "Önce bağlanın";
        const connectRequiredText = typeof t === "function" ? t("toast.connect_required") : "Bir veri kaynağına bağlanmadan analiz yapılamaz.";
        showToast("warning", connectFirstText, connectRequiredText);
        return;
      }

      const input = document.getElementById("questionInput");
      if (!input) return;

      // Butona tıklandığını görsel olarak göster
      btn.style.borderColor = "var(--orange)";
      btn.style.background  = "rgba(249,115,22,.15)";
      setTimeout(() => {
        btn.style.borderColor = "";
        btn.style.background  = "";
      }, 600);

      // Input'u doldur ve gönder
      input.value = question;
      if (typeof _autoResize === "function") _autoResize(input);
      // handleSend app.js'de tanımlı — global scope'da mevcut
      if (typeof handleSend === "function") {
        handleSend();
      } else {
        // Fallback: input focus + enter event
        input.focus();
        input.dispatchEvent(new KeyboardEvent("keydown", { key:"Enter", bubbles:true }));
      }
    });
  });
}

/* ── Error message ───────────────────────────────────────── */
function addErrorMessage(text) {
  const id = _newId();
  const ts = new Date().toISOString();
  messageHistory.push({ id, role:"agent", text:`⚠️ ${text}`, ts });
  _saveHistory();
  const row = document.createElement("div");
  row.className = "msg-row agent"; row.dataset.id = id;
  row.innerHTML = `
    <div class="msg-bubble">
      <div class="msg-text" style="border-color:rgba(239,68,68,.4);color:#fca5a5">${_esc(`⚠️ ${text}`)}</div>
      <span class="msg-time">${_time(ts)}</span>
    </div>`;
  $msg().appendChild(row);
  _scrollBottom();
}

/* ── Toasts ──────────────────────────────────────────────── */
const TOAST_ICONS = { success:"✅", error:"❌", warning:"⚠️", info:"ℹ️" };
function showToast(type, title, message="", duration=3500) {
  const cont = document.getElementById("toastContainer");
  if (!cont) return;
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.setAttribute("role","alert");
  el.innerHTML = `
    <span class="toast-icon">${TOAST_ICONS[type]||"ℹ️"}</span>
    <div class="toast-body">
      <div class="toast-title">${_esc(title)}</div>
      ${message ? `<div class="toast-msg">${_esc(message)}</div>` : ""}
    </div>`;
  cont.appendChild(el);
  setTimeout(() => {
    el.classList.add("removing");
    el.addEventListener("animationend", () => el.remove(), { once:true });
  }, duration);
}
