/**
 * app.js — State yönetimi ve event binding (yeni HTML yapısına uygun)
 *
 * HTML element id'leri:
 *   sidebar, sidebarToggle, menuBtn
 *   sourceTabs (source-tab butonlar), sourceType (hidden input)
 *   panel-sql, panel-mongodb, panel-s3, panel-snowflake
 *   connDot, connLabel  (conn-pill içinde)
 *   btnTestConn, btnConnect, btnDisconnect
 *   btnRefreshSchema, schemaPanel, schemaText
 *   sessionInfo, sessionIdDisplay
 *   topbarBadge
 *   btnClearHistory
 *   questionInput, sendBtn
 */

/* ═══════════════════════════════════════════════════════════
   State
═══════════════════════════════════════════════════════════ */
const State = {
  sessionId:   null,
  sourceType:  null,
  isConnected: false,
  isSending:   false,
};

/* ═══════════════════════════════════════════════════════════
   DOM refs  (evaluated lazily after DOMContentLoaded)
═══════════════════════════════════════════════════════════ */
let els = {};

function _initEls() {
  const g = (id) => document.getElementById(id);
  els = {
    sidebar:          g("sidebar"),
    sidebarToggle:    g("sidebarToggle"),
    menuBtn:          g("menuBtn"),
    sourceTypeInput:  g("sourceType"),          // hidden input
    sourceTabs:       document.querySelectorAll(".source-tab"),
    connDot:          g("connDot"),
    connLabel:        g("connLabel"),
    btnTestConn:      g("btnTestConn"),
    btnConnect:       g("btnConnect"),
    btnDisconnect:    g("btnDisconnect"),
    btnRefreshSchema: g("btnRefreshSchema"),
    schemaPanel:      g("schemaPanel"),
    schemaText:       g("schemaText"),
    sessionInfo:      g("sessionInfo"),
    sessionIdDisplay: g("sessionIdDisplay"),
    topbarBadge:      g("topbarBadge"),
    btnClearHistory:  g("btnClearHistory"),
    questionInput:    g("questionInput"),
    sendBtn:          g("sendBtn"),
  };
}

/* ═══════════════════════════════════════════════════════════
   Source-tab switching
═══════════════════════════════════════════════════════════ */
const PANEL_MAP = {
  postgresql: "panel-sql",
  mysql:      "panel-sql",
  mongodb:    "panel-mongodb",
  s3:         "panel-s3",
  snowflake:  "panel-snowflake",
};

function _switchSource(srcType) {
  // Update hidden input
  els.sourceTypeInput.value = srcType;

  // Toggle active tab style
  els.sourceTabs.forEach(tab => {
    tab.classList.toggle("active", tab.dataset.src === srcType);
  });

  // Show correct field panel
  Object.values(PANEL_MAP).forEach(panelId => {
    const el = document.getElementById(panelId);
    if (el) el.classList.remove("active");
  });
  const targetPanel = document.getElementById(PANEL_MAP[srcType]);
  if (targetPanel) targetPanel.classList.add("active");
}

/* ═══════════════════════════════════════════════════════════
   Connection badge helpers
═══════════════════════════════════════════════════════════ */
function _setDot(state, label) {
  // state: "" | "testing" | "connected" | "error"
  els.connDot.className  = "conn-dot" + (state ? ` ${state}` : "");
  els.connLabel.textContent = label;
}

function _setConnected(sessionId, sourceType) {
  State.sessionId   = sessionId;
  State.sourceType  = sourceType;
  State.isConnected = true;

  _setDot("connected", `${_srcLabel(sourceType)} bağlı`);

  // topbar badge
  els.topbarBadge.textContent = _srcLabel(sourceType);
  els.topbarBadge.className   = "topbar-badge show connected";

  // Button swap
  els.btnConnect.classList.add("hidden");
  els.btnDisconnect.classList.remove("hidden");
  els.btnTestConn.disabled = true;

  // Disable source tabs while connected
  els.sourceTabs.forEach(t => t.disabled = true);

  // Enable input
  els.questionInput.disabled = false;
  els.questionInput.placeholder = "Verileriniz hakkında herhangi bir şey sorun…";
  els.sendBtn.disabled = false;

  // Session chip
  els.sessionIdDisplay.textContent = sessionId;
  els.sessionInfo.classList.remove("hidden");

  // Persist for page reload
  sessionStorage.setItem("nx_sid",  sessionId);
  sessionStorage.setItem("nx_src",  sourceType);
}

function _setDisconnected() {
  State.sessionId   = null;
  State.sourceType  = null;
  State.isConnected = false;

  _setDot("", "Bağlantı bekleniyor");

  els.topbarBadge.className = "topbar-badge";

  els.btnConnect.classList.remove("hidden");
  els.btnDisconnect.classList.add("hidden");
  els.btnTestConn.disabled = false;

  els.sourceTabs.forEach(t => t.disabled = false);

  els.questionInput.disabled = true;
  els.questionInput.placeholder = "Veri kaynağınız hakkında bir şey sorun…";
  els.sendBtn.disabled = true;

  els.schemaPanel.classList.add("hidden");
  els.schemaText.textContent = "";
  els.sessionInfo.classList.add("hidden");
  els.sessionIdDisplay.textContent = "";

  sessionStorage.removeItem("nx_sid");
  sessionStorage.removeItem("nx_src");
}

function _srcLabel(type) {
  return ({ postgresql:"PostgreSQL", mysql:"MySQL", mongodb:"MongoDB",
             s3:"AWS S3", snowflake:"Snowflake" })[type] || type;
}

/* ═══════════════════════════════════════════════════════════
   Button: Test
═══════════════════════════════════════════════════════════ */
async function handleTestConnection() {
  _setDot("testing", "Test ediliyor…");
  _setLoading(els.btnTestConn, true, "Test ediliyor…");

  try {
    const result = await apiTestConnection(buildConnectPayload());
    _setDot("connected", "Test başarılı");
    showToast("success", "Bağlantı başarılı",
      result.version || result.database || result.bucket || "");
  } catch (err) {
    _setDot("error", "Test başarısız");
    showToast("error", "Bağlantı testi başarısız", err.message, 5000);
  } finally {
    _setLoading(els.btnTestConn, false, "Test Et");
    if (!State.isConnected) {
      setTimeout(() => { if (!State.isConnected) _setDot("", "Bağlantı bekleniyor"); }, 3000);
    }
  }
}

/* ═══════════════════════════════════════════════════════════
   Button: Connect
═══════════════════════════════════════════════════════════ */
async function handleConnect() {
  _setDot("testing", "Bağlanıyor…");
  _setLoading(els.btnConnect, true, "Bağlanıyor…");

  try {
    const res = await apiConnect(buildConnectPayload());
    _setConnected(res.session_id, res.source_type);
    showToast("success", "Bağlantı kuruldu", res.message);
    _loadSchema(res.session_id);
  } catch (err) {
    _setDot("error", "Bağlantı hatası");
    showToast("error", "Bağlanılamadı", err.message, 5000);
    setTimeout(() => { if (!State.isConnected) _setDot("", "Bağlantı bekleniyor"); }, 3000);
  } finally {
    _setLoading(els.btnConnect, false, "Bağlan");
  }
}

/* ═══════════════════════════════════════════════════════════
   Button: Disconnect
═══════════════════════════════════════════════════════════ */
async function handleDisconnect() {
  if (!State.sessionId) return;
  _setLoading(els.btnDisconnect, true, "");

  try {
    await apiDisconnect(State.sessionId);
    showToast("info", "Bağlantı kesildi");
  } catch { /* ignore — clear state anyway */ } finally {
    _setDisconnected();
    _setLoading(els.btnDisconnect, false, "Bağlantıyı Kes");
  }
}

/* ═══════════════════════════════════════════════════════════
   Schema
═══════════════════════════════════════════════════════════ */
async function _loadSchema(sessionId) {
  const btn = els.btnRefreshSchema;
  btn.classList.add("spinning");
  try {
    const schema = await apiGetSchema(sessionId);
    els.schemaText.textContent = schema.schema_text || "(Şema boş)";
    els.schemaPanel.classList.remove("hidden");
  } catch (err) {
    els.schemaText.textContent = `Şema yüklenemedi: ${err.message}`;
    els.schemaPanel.classList.remove("hidden");
  } finally {
    btn.classList.remove("spinning");
  }
}

/* ═══════════════════════════════════════════════════════════
   Send question
═══════════════════════════════════════════════════════════ */
async function handleSend() {
  if (State.isSending || !State.isConnected) return;

  const question = els.questionInput.value.trim();
  if (!question) return;

  State.isSending = true;
  els.questionInput.value = "";
  _autoResize(els.questionInput);
  els.sendBtn.disabled = true;

  addUserMessage(question);
  showProcessing();          // pipeline progress indicator

  // Simulate step advances while waiting for response
  const stepKeys = ["schema", "sql", "execute", "clean", "insight"];
  let stepIdx = 0;
  const stepTimer = setInterval(() => {
    if (stepIdx < stepKeys.length) advanceStep(stepKeys[stepIdx++]);
    else clearInterval(stepTimer);
  }, 900);

  // On mobile, collapse sidebar to show messages
  if (window.innerWidth <= 768) els.sidebar.classList.add("collapsed");

  try {
    const response = await apiAsk(State.sessionId, question);
    clearInterval(stepTimer);
    hideTyping();
    addAgentMessage(response);
  } catch (err) {
    clearInterval(stepTimer);
    hideTyping();
    addErrorMessage(err.message);
    showToast("error", "Yanıt alınamadı", err.message, 5000);
  } finally {
    State.isSending = false;
    els.sendBtn.disabled = false;
    els.questionInput.focus();
  }
}

/* ═══════════════════════════════════════════════════════════
   Micro-helpers
═══════════════════════════════════════════════════════════ */
function _setLoading(btn, on, label) {
  btn.disabled = on;
  if (on) {
    btn.innerHTML = `<span class="btn-spinner"></span>${label ? `<span>${label}</span>` : ""}`;
  } else {
    // Restore original inner text (label parameter)
    btn.textContent = label;
  }
}

function _autoResize(ta) {
  ta.style.height = "auto";
  ta.style.height = Math.min(ta.scrollHeight, 140) + "px";
}
/* ═══════════════════════════════════════════════════════════
   Event binding
═══════════════════════════════════════════════════════════ */
function _bindEvents() {
  // Sidebar toggles
  els.sidebarToggle.addEventListener("click", () => els.sidebar.classList.toggle("collapsed"));
  els.menuBtn.addEventListener("click",        () => els.sidebar.classList.toggle("collapsed"));

  // Close sidebar on outside click (mobile)
  document.addEventListener("click", e => {
    if (window.innerWidth > 768) return;
    if (!els.sidebar.classList.contains("collapsed") &&
        !els.sidebar.contains(e.target) &&
        e.target !== els.menuBtn) {
      els.sidebar.classList.add("collapsed");
    }
  });

  // Source tabs
  els.sourceTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      if (!State.isConnected) _switchSource(tab.dataset.src);
    });
  });

  // Connection buttons
  els.btnTestConn.addEventListener("click",    handleTestConnection);
  els.btnConnect.addEventListener("click",     handleConnect);
  els.btnDisconnect.addEventListener("click",  handleDisconnect);

  // Schema refresh
  els.btnRefreshSchema.addEventListener("click", () => {
    if (State.sessionId) _loadSchema(State.sessionId);
  });

  // Clear history
  els.btnClearHistory.addEventListener("click", () => {
    if (confirm("Tüm konuşma geçmişi silinecek. Devam edilsin mi?")) {
      clearHistory();
      showToast("info", "Geçmiş temizlendi");
    }
  });

  // Send
  els.sendBtn.addEventListener("click", handleSend);
  els.questionInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  });
  els.questionInput.addEventListener("input", () => _autoResize(els.questionInput));

  // Suggestion cards (welcome screen)
  document.querySelectorAll(".suggestion-card").forEach(card => {
    card.addEventListener("click", () => {
      if (!State.isConnected) {
        showToast("warning", "Önce bağlanın", "Bir veri kaynağına bağlanmadan soru sorulamaz.");
        return;
      }
      els.questionInput.value = card.dataset.q;
      _autoResize(els.questionInput);
      els.questionInput.focus();
    });
  });
}

/* ═══════════════════════════════════════════════════════════
   Boot
═══════════════════════════════════════════════════════════ */
function _boot() {
  _initEls();
  _switchSource("postgresql");  // default tab
  _setDisconnected();
  restoreHistory();
  _bindEvents();

  // Try to restore last session from sessionStorage
  const sid = sessionStorage.getItem("nx_sid");
  const src = sessionStorage.getItem("nx_src");
  if (sid && src) {
    apiGetSchema(sid)
      .then(schema => {
        _setConnected(sid, src);
        els.schemaText.textContent = schema.schema_text || "";
        els.schemaPanel.classList.remove("hidden");
        showToast("info", "Önceki oturum geri yüklendi", _srcLabel(src));
      })
      .catch(() => {
        sessionStorage.removeItem("nx_sid");
        sessionStorage.removeItem("nx_src");
      });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", _boot);
} else {
  _boot();
}
