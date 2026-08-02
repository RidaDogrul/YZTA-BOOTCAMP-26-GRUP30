/**
 * app.js — State yönetimi, event binding, merge panel (inline accordion), tablo seçimi
 *
 * Kaynak birleştirme akışı:
 *   1. Kullanıcı ilk kaynağa bağlanır → birincil kaynak MergeState'e eklenir,
 *      şeması arka planda çekilir ve accordion otomatik açılır.
 *   2. "Kaynak Ekle" → tab + form görünür → kullanıcı yeni kaynak bilgilerini girer.
 *   3. "Ekle" → apiAddSource → yeni kaynağın şeması otomatik çekilir → accordion açılır.
 *   4. Her kaynağın accordion'ında tablolar checkboxlarla listelenir.
 *   5. "Tüm Kaynaklarla Sorgula" → seçili tablolar source_selection olarak gönderilir.
 */

/* ═══════════════════════════════════════════════════════════
   State
═══════════════════════════════════════════════════════════ */
const State = {
  sessionId:   null,
  sourceType:  null,
  isConnected: false,
  isSending:   false,
  schemaData:  null,
};

/**
 * MergeState.sources her eleman:
 * {
 *   sourceId:    string   — backend source_id
 *   sourceType:  string   — "postgresql" | "mysql" | ...
 *   alias:       string   — kullanıcı dostu ad
 *   isPrimary:   bool
 *   tables:      string[] — seçili tablo adları (boş = tümü)
 *   schemaData:  { tables:[], collections:[], files:[], error:null } | null
 *   expanded:    bool     — accordion açık mı?
 *   loading:     bool     — şema yükleniyor mu?
 * }
 */
const MergeState = {
  sources:       [],
  addingSource:  false,
};

/* ═══════════════════════════════════════════════════════════
   DOM refs
═══════════════════════════════════════════════════════════ */
let els = {};

function _initEls() {
  const g = (id) => document.getElementById(id);
  els = {
    sidebar:             g("sidebar"),
    sidebarToggle:       g("sidebarToggle"),
    menuBtn:             g("menuBtn"),
    sourceTypeInput:     g("sourceType"),
    sourceTabs:          document.querySelectorAll(".source-tab"),
    connDot:             g("connDot"),
    connLabel:           g("connLabel"),
    btnTestConn:         g("btnTestConn"),
    btnConnect:          g("btnConnect"),
    btnDisconnect:       g("btnDisconnect"),
    btnRefreshSchema:    g("btnRefreshSchema"),
    schemaPanel:         g("schemaPanel"),
    schemaText:          g("schemaText"),
    sessionInfo:         g("sessionInfo"),
    sessionIdDisplay:    g("sessionIdDisplay"),
    topbarBadge:         g("topbarBadge"),
    btnClearHistory:     g("btnClearHistory"),
    btnClearChat:        g("btnClearChat"),
    btnGenerateReport:   g("btnGenerateReport"),
    questionInput:       g("questionInput"),
    sendBtn:             g("sendBtn"),
    // Merge
    mergeSectionLabel:   g("mergeSectionLabel"),
    mergeBar:            g("mergeBar"),
    mergeSourceList:     g("mergeSourceList"),
    btnAddSource:        g("btnAddSource"),
    btnRunMerge:         g("btnRunMerge"),
    addSourceForm:       g("addSourceForm"),
    addSourceAlias:      g("addSourceAlias"),
    btnAddSourceConfirm: g("btnAddSourceConfirm"),
    btnAddSourceCancel:  g("btnAddSourceCancel"),
    asfTypePicker:       g("asfTypePicker"),
    asfFields:           g("asfFields"),
    // Data search
    dataSearchWrap:      g("dataSearchWrap"),
    dataSearchInput:     g("dataSearchInput"),
    dataSearchResults:   g("dataSearchResults"),
  };
}

/* ═══════════════════════════════════════════════════════════
   Util
═══════════════════════════════════════════════════════════ */
function _esc(s) {
  return String(s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

function _srcLabel(type) {
  return ({ postgresql:"PostgreSQL", mysql:"MySQL", mongodb:"MongoDB",
            s3:"AWS S3", snowflake:"Snowflake" }[type] || type);
}

const SRC_COLOR_CLASS = {
  postgresql:"pg", mysql:"mysql", mongodb:"mongo", s3:"s3", snowflake:"snow"
};

/* ═══════════════════════════════════════════════════════════
   Source-tab switching
═══════════════════════════════════════════════════════════ */
const PANEL_MAP = {
  postgresql:"panel-sql", mysql:"panel-sql",
  mongodb:"panel-mongodb", s3:"panel-s3", snowflake:"panel-snowflake",
};

function _switchSource(srcType) {
  els.sourceTypeInput.value = srcType;
  els.sourceTabs.forEach(t => t.classList.toggle("active", t.dataset.src === srcType));
  Object.values(PANEL_MAP).forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.remove("active");
  });
  const panel = document.getElementById(PANEL_MAP[srcType]);
  if (panel) panel.classList.add("active");

  // Update placeholder based on selected source type
  const connUrlInput = document.getElementById("connectionUrl");
  if (connUrlInput) {
    if (srcType === "mysql") {
      connUrlInput.placeholder = "mysql+pymysql://user:pass@host:3306/db";
    } else {
      connUrlInput.placeholder = "postgresql+psycopg2://user:pass@host:5432/db";
    }
  }
}

/* ═══════════════════════════════════════════════════════════
   Connection state
═══════════════════════════════════════════════════════════ */
function _setDot(state, label) {
  els.connDot.className     = "conn-dot" + (state ? ` ${state}` : "");
  els.connLabel.textContent = label;
}

/**
 * Birincil bağlantı kuruldu.
 * @param {string} sessionId
 * @param {string} sourceType
 * @param {string} sourceId   — backend'den gelen gerçek source_id
 * @param {string} alias
 */
function _setConnected(sessionId, sourceType, sourceId, alias) {
  State.sessionId   = sessionId;
  State.sourceType  = sourceType;
  State.isConnected = true;

  const displayAlias = alias || _srcLabel(sourceType);
  const connectedText = typeof t === "function" ? t("connection.source_connected", { source: displayAlias }) : `${displayAlias} bağlı`;
  _setDot("connected", connectedText);

  const cls = SRC_COLOR_CLASS[sourceType] || "";
  els.topbarBadge.textContent = displayAlias;
  els.topbarBadge.className   = `topbar-badge show connected src-${cls}`;

  els.btnConnect.classList.add("hidden");
  els.btnDisconnect.classList.remove("hidden");
  els.btnTestConn.disabled = true;
  els.sourceTabs.forEach(t => (t.disabled = true));

  els.questionInput.disabled    = false;
  els.questionInput.placeholder = typeof t === "function" ? t("chat.placeholder") : "Verileriniz hakkında herhangi bir şey sorun…";
  els.sendBtn.disabled          = false;

  els.sessionIdDisplay.textContent = sessionId;
  els.sessionInfo.classList.remove("hidden");

  // Birincil kaynağı MergeState'e kaydet (gerçek source_id ile)
  MergeState.sources = [{
    sourceId:   sourceId,
    sourceType: sourceType,
    alias:      displayAlias,
    isPrimary:  true,
    tables:     [],
    schemaData: null,
    expanded:   false,
    loading:    false,
  }];
  _renderMergeSourceList();
  _showMergePanel(true);
  _showDataSearch(true);

  sessionStorage.setItem("nx_sid", sessionId);
  sessionStorage.setItem("nx_src", sourceType);
  sessionStorage.setItem("nx_sid2", sourceId);
}

function _setDisconnected() {
  State.sessionId   = null;
  State.sourceType  = null;
  State.isConnected = false;
  State.schemaData  = null;

  const waitingText = typeof t === "function" ? t("connection.waiting") : "Bağlantı bekleniyor";
  _setDot("", waitingText);
  els.topbarBadge.className = "topbar-badge";

  els.btnConnect.classList.remove("hidden");
  els.btnDisconnect.classList.add("hidden");
  els.btnTestConn.disabled = false;
  els.sourceTabs.forEach(t => (t.disabled = false));

  els.questionInput.disabled    = true;
  els.questionInput.placeholder = typeof t === "function" ? t("chat.placeholder_disconnected") : "Veri kaynağınız hakkında bir şey sorun…";
  els.sendBtn.disabled          = true;

  els.schemaPanel.classList.add("hidden");
  els.schemaText.textContent = "";
  els.sessionInfo.classList.add("hidden");
  els.sessionIdDisplay.textContent = "";

  MergeState.sources      = [];
  MergeState.addingSource = false;
  _renderMergeSourceList();
  _showMergePanel(false);
  _showDataSearch(false);
  _hideAddSourceForm();

  sessionStorage.removeItem("nx_sid");
  sessionStorage.removeItem("nx_src");
  sessionStorage.removeItem("nx_sid2");
}

/* ═══════════════════════════════════════════════════════════
   Merge panel — görünürlük
═══════════════════════════════════════════════════════════ */
function _showMergePanel(show) {
  if (els.mergeSectionLabel) els.mergeSectionLabel.style.display = show ? "" : "none";
  if (els.mergeBar) els.mergeBar.classList.toggle("visible", show);
}

function _showDataSearch(show) {
  if (els.dataSearchWrap) els.dataSearchWrap.classList.toggle("visible", show);
}

/* ═══════════════════════════════════════════════════════════
   Merge panel — inline accordion render
   Her kaynak için:
     [badge] [alias]  [tümünü seç / temizle] [kaldır?]
     ▼ accordion
       ┌──────────────────────────────────────┐
       │ □ tablo_adı                          │
       │ ☑ diger_tablo                        │
       └──────────────────────────────────────┘
═══════════════════════════════════════════════════════════ */
function _renderMergeSourceList() {
  const list = els.mergeSourceList;
  if (!list) return;
  list.innerHTML = "";

  MergeState.sources.forEach(src => {
    const cls = SRC_COLOR_CLASS[src.sourceType] || "";
    const selCount = src.tables.length;
    const allTablesText = typeof t === "function" ? t("merge.all_tables") : "Tüm tablolar";
    const selectedText = typeof t === "function" ? t("merge.selected_count") : "seçili";
    const selLabel = selCount === 0 ? allTablesText : `${selCount} ${selectedText}`;

    // ── Ana kart ───────────────────────────────────────
    const card = document.createElement("div");
    card.className = "msrc-card" + (src.expanded ? " expanded" : "");
    card.dataset.sid = src.sourceId;   // ← artık src-xxx gerçek ID

    const showTablesLabel = typeof t === "function" ? t("merge.show_tables") : "Tabloları göster";
    const removeLabel = typeof t === "function" ? t("merge.remove") : "Kaldır";
    const removeTitle = typeof t === "function" ? t("merge.remove_source") : "Kaynağı kaldır";
    const schemaLoadingText = typeof t === "function" ? t("merge.schema_loading") : "Şema yükleniyor…";

    card.innerHTML = `
      <div class="msrc-header">
        <button class="msrc-toggle" aria-expanded="${src.expanded}" aria-label="${showTablesLabel}">
          <svg class="msrc-chevron" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M2 4l4 4 4-4" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <span class="merge-src-badge src-${cls}">${_srcLabel(src.sourceType)}</span>
        <span class="msrc-alias">${_esc(src.alias)}</span>
        <span class="msrc-sel-count ${selCount > 0 ? "has-sel" : ""}">${selLabel}</span>
        ${src.isPrimary ? "" : `
          <button class="msrc-remove" title="${removeTitle}" aria-label="${removeLabel}">
            <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 1l8 8M9 1l-8 8" stroke-linecap="round"/>
            </svg>
          </button>
        `}
      </div>

      <div class="msrc-body" ${src.expanded ? "" : 'style="display:none"'}>
        ${src.loading
          ? `<div class="msrc-loading"><div class="proc-spin"></div> <span>${schemaLoadingText}</span></div>`
          : _buildTableList(src)
        }
      </div>
    `;

    // Accordion aç/kapa
    card.querySelector(".msrc-toggle").addEventListener("click", () => _toggleAccordion(src.sourceId));

    // Kaldır
    const removeBtn = card.querySelector(".msrc-remove");
    if (removeBtn) removeBtn.addEventListener("click", () => _removeSource(src.sourceId));

    // Checkbox değişimleri (body içinde)
    card.querySelectorAll(".msrc-cb").forEach(cb => {
      cb.addEventListener("change", () => _onTableCheck(src.sourceId, cb));
    });

    // Tümünü Seç / Temizle butonları
    const btnAll  = card.querySelector(".msrc-sel-all");
    const btnNone = card.querySelector(".msrc-sel-none");
    if (btnAll)  btnAll.addEventListener("click",  () => _selectAllTables(src.sourceId, true));
    if (btnNone) btnNone.addEventListener("click", () => _selectAllTables(src.sourceId, false));

    list.appendChild(card);
  });

  // "Tüm Kaynaklarla Sorgula" — 2+ kaynak varsa aktif
  if (els.btnRunMerge) els.btnRunMerge.disabled = MergeState.sources.length < 2;
}

/* ─── Tablo listesi HTML'i ─────────────────────────────── */
function _buildTableList(src) {
  const sd = src.schemaData;

  if (!sd) {
    const schemaNotLoadedText = typeof t === "function" ? t("merge.schema_not_loaded") : "Şema henüz yüklenmedi.";
    return `<div class="msrc-empty">${schemaNotLoadedText}</div>`;
  }
  if (sd.error) return `<div class="msrc-error">⚠ ${_esc(sd.error)}</div>`;

  let items = [];
  if (sd.tables?.length)
    items = sd.tables.map(t => t.table_name || t.name || String(t));
  else if (sd.collections?.length)
    items = sd.collections.map(c => c.collection_name || c.name || String(c));
  else if (sd.files?.length)
    items = sd.files.map(f => f.key || String(f));

  if (!items.length) {
    const noTablesText = typeof t === "function" ? t("merge.no_tables") : "Bu kaynakta tablo bulunamadı.";
    return `<div class="msrc-empty">${noTablesText}</div>`;
  }

  const selected = new Set(src.tables);
  const rows = items.map(name => {
    const chk = selected.has(name) ? "checked" : "";
    return `
      <label class="msrc-table-row ${chk ? "checked" : ""}">
        <input class="msrc-cb" type="checkbox" value="${_esc(name)}" ${chk}/>
        <span class="msrc-cb-box"></span>
        <span class="msrc-table-name">${_esc(name)}</span>
      </label>`;
  }).join("");

  const selectAllText = typeof t === "function" ? t("merge.select_all") : "Tümünü Seç";
  const clearText = typeof t === "function" ? t("merge.clear") : "Temizle";

  return `
    <div class="msrc-toolbar">
      <button class="msrc-sel-all">${selectAllText}</button>
      <button class="msrc-sel-none">${clearText}</button>
    </div>
    <div class="msrc-table-list">${rows}</div>`;
}

/* ─── Accordion toggle ─────────────────────────────────── */
function _toggleAccordion(sourceId) {
  const src = MergeState.sources.find(s => s.sourceId === sourceId);
  if (!src) return;

  src.expanded = !src.expanded;

  const card = els.mergeSourceList?.querySelector(`[data-sid="${CSS.escape(sourceId)}"]`);
  if (!card) return;

  card.classList.toggle("expanded", src.expanded);
  const btn  = card.querySelector(".msrc-toggle");
  const body = card.querySelector(".msrc-body");
  if (btn)  btn.setAttribute("aria-expanded", src.expanded);
  if (body) body.style.display = src.expanded ? "" : "none";

  // Açılırken şema yoksa çek
  if (src.expanded && !src.schemaData && !src.loading) {
    _fetchSchemaForSource(src, card);
  }
}

/* ─── Şema çekme (tek kaynak için) ────────────────────── */
async function _fetchSchemaForSource(src, card) {
  src.loading = true;
  const body = card?.querySelector(".msrc-body");
  const schemaLoadingText = typeof t === "function" ? t("merge.schema_loading") : "Şema yükleniyor…";
  if (body) body.innerHTML = `<div class="msrc-loading"><div class="proc-spin"></div> <span>${schemaLoadingText}</span></div>`;

  try {
    const multi = await apiGetMultiSchema(State.sessionId);
    if (multi?.sources) {
      multi.sources.forEach(ms => {
        const s = MergeState.sources.find(x => x.sourceId === ms.source_id);
        if (s) {
          s.schemaData = {
            tables:      ms.tables      || [],
            collections: ms.collections || [],
            files:       ms.files       || [],
            error:       ms.error       || null,
          };
          s.loading = false;
          // Güncel kart varsa body'yi yenile
          const c = els.mergeSourceList?.querySelector(`[data-sid="${CSS.escape(s.sourceId)}"]`);
          const b = c?.querySelector(".msrc-body");
          if (b && s.expanded) b.innerHTML = _buildTableList(s);
          // Checkbox event'lerini yeniden bağla
          if (b) {
            b.querySelectorAll(".msrc-cb").forEach(cb => {
              cb.addEventListener("change", () => _onTableCheck(s.sourceId, cb));
            });
            const btnAll  = b.querySelector(".msrc-sel-all");
            const btnNone = b.querySelector(".msrc-sel-none");
            if (btnAll)  btnAll.addEventListener("click",  () => _selectAllTables(s.sourceId, true));
            if (btnNone) btnNone.addEventListener("click", () => _selectAllTables(s.sourceId, false));
          }
        }
      });
    }
  } catch (err) {
    src.loading = false;
    const b = card?.querySelector(".msrc-body");
    const schemaLoadErrorText = typeof t === "function" ? t("merge.schema_load_error", { error: err.message }) : `Şema yüklenemedi: ${err.message}`;
    if (b) b.innerHTML = `<div class="msrc-error">⚠ ${_esc(schemaLoadErrorText)}</div>`;
  }
}

/* ─── Checkbox değişimi ────────────────────────────────── */
function _onTableCheck(sourceId, cb) {
  const src = MergeState.sources.find(s => s.sourceId === sourceId);
  if (!src) return;

  const label = cb.closest("label");
  if (label) label.classList.toggle("checked", cb.checked);

  if (cb.checked) {
    if (!src.tables.includes(cb.value)) src.tables.push(cb.value);
  } else {
    src.tables = src.tables.filter(t => t !== cb.value);
  }
  _updateSelCount(sourceId);
}

/* ─── Tümünü Seç / Temizle ────────────────────────────── */
function _selectAllTables(sourceId, selectAll) {
  const src = MergeState.sources.find(s => s.sourceId === sourceId);
  if (!src) return;

  const card = els.mergeSourceList?.querySelector(`[data-sid="${CSS.escape(sourceId)}"]`);
  if (!card) return;

  card.querySelectorAll(".msrc-cb").forEach(cb => {
    cb.checked = selectAll;
    cb.closest("label")?.classList.toggle("checked", selectAll);
  });

  if (selectAll) {
    const allNames = [...card.querySelectorAll(".msrc-cb")].map(cb => cb.value);
    src.tables = allNames;
  } else {
    src.tables = [];
  }
  _updateSelCount(sourceId);
}

/* ─── Seçim sayacını güncelle ─────────────────────────── */
function _updateSelCount(sourceId) {
  const src  = MergeState.sources.find(s => s.sourceId === sourceId);
  const card = els.mergeSourceList?.querySelector(`[data-sid="${CSS.escape(sourceId)}"]`);
  if (!src || !card) return;

  const badge = card.querySelector(".msrc-sel-count");
  if (badge) {
    const n = src.tables.length;
    const allTablesText = typeof t === "function" ? t("merge.all_tables") : "Tüm tablolar";
    const selectedText = typeof t === "function" ? t("merge.selected_count") : "seçili";
    badge.textContent = n === 0 ? allTablesText : `${n} ${selectedText}`;
    badge.classList.toggle("has-sel", n > 0);
  }
}

/* ═══════════════════════════════════════════════════════════
   Kaynak kaldırma
═══════════════════════════════════════════════════════════ */
async function _removeSource(sourceId) {
  if (!State.sessionId) return;
  try {
    await apiRemoveSource(State.sessionId, sourceId);
    MergeState.sources = MergeState.sources.filter(s => s.sourceId !== sourceId);
    _renderMergeSourceList();
    const sourceRemovedText = typeof t === "function" ? t("toast.source_removed") : "Kaynak kaldırıldı";
    showToast("info", sourceRemovedText);
  } catch (err) {
    const removeFailedText = typeof t === "function" ? t("toast.remove_failed") : "Kaldırılamadı";
    showToast("error", removeFailedText, err.message);
  }
}

/* ═══════════════════════════════════════════════════════════
   Kaynak ekleme formu — kendi type-picker + field panelleri
═══════════════════════════════════════════════════════════ */

// Tüm desteklenen kaynak tipleri ve etiketleri
const ALL_SOURCE_TYPES = [
  { type:"postgresql", label:"PostgreSQL", cls:"pg" },
  { type:"mysql",      label:"MySQL",      cls:"mysql" },
  { type:"mongodb",    label:"MongoDB",    cls:"mongo" },
  { type:"s3",         label:"☁ S3",       cls:"s3" },
  { type:"snowflake",  label:"❄ Snowflake",cls:"snow" },
];

// Seçili kaynak tipi (add-source formuna özel)
let _asfSelectedType = null;

/**
 * Type picker'ı render et — birincil kaynak tipi ve zaten eklenenler hariç.
 */
function _renderAsfTypePicker() {
  const picker = els.asfTypePicker;
  if (!picker) return;
  picker.innerHTML = "";

  // Zaten kullanılan tipler (birincil dahil)
  const usedTypes = new Set(MergeState.sources.map(s => s.sourceType));

  const available = ALL_SOURCE_TYPES.filter(st => !usedTypes.has(st.type));

  if (!available.length) {
    const noTypesText = typeof t === "function" ? t("add_source.no_types") : "Eklenebilecek başka kaynak tipi yok.";
    picker.innerHTML = `<p class="asf-no-types">${noTypesText}</p>`;
    _asfSelectedType = null;
    return;
  }

  // İlk kullanılabilir tipi seç
  _asfSelectedType = available[0].type;

  available.forEach(({ type, label, cls }) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `asf-type-btn ${cls}${type === _asfSelectedType ? " active" : ""}`;
    btn.dataset.type = type;
    btn.textContent = label;
    btn.addEventListener("click", () => {
      _asfSelectedType = type;
      picker.querySelectorAll(".asf-type-btn").forEach(b =>
        b.classList.toggle("active", b.dataset.type === type)
      );
      _renderAsfFields(type);
    });
    picker.appendChild(btn);
  });

  _renderAsfFields(_asfSelectedType);
}

/**
 * Seçili kaynak tipine göre bağlantı alanlarını render et.
 */
function _renderAsfFields(type) {
  const container = els.asfFields;
  if (!container) return;

  const FIELDS = {
    postgresql: `
      <div class="field-group" style="padding:0">
        <label class="field-label" for="asf_connUrl">Bağlantı URL</label>
        <input class="field-input" type="text" id="asf_connUrl"
          placeholder="postgresql+psycopg2://user:pass@host:5432/db" autocomplete="off"/>
      </div>`,

    mysql: `
      <div class="field-group" style="padding:0">
        <label class="field-label" for="asf_connUrl">Bağlantı URL</label>
        <input class="field-input" type="text" id="asf_connUrl"
          placeholder="mysql+pymysql://user:pass@host:3306/db" autocomplete="off"/>
      </div>`,

    mongodb: `
      <div class="field-group" style="padding:0">
        <label class="field-label" for="asf_mongoUri">MongoDB URI</label>
        <input class="field-input" type="text" id="asf_mongoUri"
          placeholder="mongodb://localhost:27017/mydb" autocomplete="off"/>
      </div>`,

    s3: `
      <div class="field-group" style="padding:0">
        <label class="field-label" for="asf_bucket">Bucket</label>
        <input class="field-input" type="text" id="asf_bucket" placeholder="my-data-bucket" autocomplete="off"/>
      </div>
      <div class="field-group" style="padding:0">
        <label class="field-label" for="asf_accessKey">Access Key ID</label>
        <input class="field-input" type="text" id="asf_accessKey" placeholder="AKIA..." autocomplete="off"/>
      </div>
      <div class="field-group" style="padding:0">
        <label class="field-label" for="asf_secretKey">Secret Access Key</label>
        <input class="field-input" type="password" id="asf_secretKey" placeholder="••••••••"/>
      </div>
      <div class="field-group" style="padding:0">
        <label class="field-label" for="asf_region">Region</label>
        <input class="field-input" type="text" id="asf_region" value="eu-central-1" autocomplete="off"/>
      </div>`,

    snowflake: `
      <div class="field-group" style="padding:0">
        <label class="field-label" for="asf_sfAccount">Account</label>
        <input class="field-input" type="text" id="asf_sfAccount" placeholder="xy12345.eu-central-1" autocomplete="off"/>
      </div>
      <div class="asf-row">
        <div class="field-group" style="padding:0;flex:1">
          <label class="field-label" for="asf_sfUser">Kullanıcı</label>
          <input class="field-input" type="text" id="asf_sfUser" placeholder="myuser" autocomplete="off"/>
        </div>
        <div class="field-group" style="padding:0;flex:1">
          <label class="field-label" for="asf_sfPass">Parola</label>
          <input class="field-input" type="password" id="asf_sfPass" placeholder="••••••••"/>
        </div>
      </div>
      <div class="asf-row">
        <div class="field-group" style="padding:0;flex:1">
          <label class="field-label" for="asf_sfDb">Veritabanı</label>
          <input class="field-input" type="text" id="asf_sfDb" placeholder="MY_DB" autocomplete="off"/>
        </div>
        <div class="field-group" style="padding:0;flex:1">
          <label class="field-label" for="asf_sfSchema">Şema</label>
          <input class="field-input" type="text" id="asf_sfSchema" value="PUBLIC" autocomplete="off"/>
        </div>
      </div>
      <div class="asf-row">
        <div class="field-group" style="padding:0;flex:1">
          <label class="field-label" for="asf_sfWh">Warehouse</label>
          <input class="field-input" type="text" id="asf_sfWh" placeholder="COMPUTE_WH" autocomplete="off"/>
        </div>
        <div class="field-group" style="padding:0;flex:1">
          <label class="field-label" for="asf_sfRole">Rol</label>
          <input class="field-input" type="text" id="asf_sfRole" placeholder="SYSADMIN" autocomplete="off"/>
        </div>
      </div>`,
  };

  container.innerHTML = `<div class="asf-fields-wrap">${FIELDS[type] || ""}</div>`;
}

/**
 * Form alanlarından AddSourceRequest payload'u üret.
 */
function _buildAddSourcePayload(sessionId, alias) {
  const type = _asfSelectedType;
  if (!type) {
    const noTypeText = typeof t === "function" ? t("add_source.no_type_selected") : "Kaynak tipi seçilmedi.";
    throw new Error(noTypeText);
  }

  const g = (id) => document.getElementById(id)?.value.trim() || "";
  const base = { session_id: sessionId, source_type: type, alias: alias || undefined };

  switch (type) {
    case "postgresql":
    case "mysql":
      return { ...base, connection_url: g("asf_connUrl") };
    case "mongodb":
      return { ...base, mongodb_uri: g("asf_mongoUri") };
    case "s3":
      return {
        ...base,
        bucket_name:           g("asf_bucket"),
        aws_access_key_id:     g("asf_accessKey"),
        aws_secret_access_key: g("asf_secretKey"),
        aws_region:            g("asf_region") || "eu-central-1",
      };
    case "snowflake":
      return {
        ...base,
        snowflake_account:   g("asf_sfAccount"),
        snowflake_user:      g("asf_sfUser"),
        snowflake_password:  g("asf_sfPass"),
        snowflake_database:  g("asf_sfDb"),
        snowflake_schema:    g("asf_sfSchema") || "PUBLIC",
        snowflake_warehouse: g("asf_sfWh") || undefined,
        snowflake_role:      g("asf_sfRole") || undefined,
      };
    default:
      const unknownTypeText = typeof t === "function" ? t("add_source.unknown_type", { type }) : `Bilinmeyen kaynak tipi: ${type}`;
      throw new Error(unknownTypeText);
  }
}

function _showAddSourceForm() {
  MergeState.addingSource = true;
  // Sidebar sekmeleri — dokunma, form kendi seçicisini kullanıyor
  if (els.addSourceForm) {
    els.addSourceForm.classList.remove("hidden");
    els.addSourceForm.classList.add("visible");
  }
  if (els.btnAddSource) els.btnAddSource.disabled = true;
  if (els.addSourceAlias) els.addSourceAlias.value = "";
  // Type picker'ı doldur (birincil tipi hariç tut)
  _renderAsfTypePicker();
}

function _hideAddSourceForm() {
  MergeState.addingSource = false;
  if (els.addSourceForm) {
    els.addSourceForm.classList.remove("visible");
    els.addSourceForm.classList.add("hidden");
  }
  if (els.btnAddSource) els.btnAddSource.disabled = false;
  _asfSelectedType = null;
}

async function _handleAddSourceConfirm() {
  if (!State.sessionId) return;
  const alias = els.addSourceAlias?.value.trim() || "";

  let payload;
  try {
    payload = _buildAddSourcePayload(State.sessionId, alias);
  } catch (err) {
    const missingInfoText = typeof t === "function" ? t("add_source.missing_info") : "Eksik bilgi";
    showToast("warning", missingInfoText, err.message);
    return;
  }

  const connectingText = typeof t === "function" ? t("add_source.connecting") : "Bağlanıyor…";
  const connectAddText = typeof t === "function" ? t("btn.connect_add") : "Bağlan & Ekle";
  _setLoading(els.btnAddSourceConfirm, true, connectingText);
  try {
    let res;
    try {
      res = await apiAddSource(payload);
    } catch (err) {
      // Session expire olduysa ana kaynağa yeniden bağlan
      const isExpired = err.message && (
        err.message.includes("Oturum bulunamadı") ||
        err.message.includes("süresi doldu") ||
        err.message.includes("404")
      );
      if (isExpired && State._lastConnectPayload) {
        showToast("info", "Oturum yenileniyor", "Bağlantı yeniden kuruluyor…", 3000);
        const reconnect = await apiConnect(State._lastConnectPayload);
        State.sessionId = reconnect.session_id;
        payload.session_id = reconnect.session_id;
        res = await apiAddSource(payload);
      } else {
        throw err;
      }
    }
    _syncSourcesFromBackend(res.sources);

    // Yeni eklenen kaynağın accordion'unu aç + şema çek
    const newSrc = MergeState.sources.find(s => s.sourceId === res.source_id);
    if (newSrc) {
      newSrc.expanded = true;
      newSrc.loading  = true;
    }
    _renderMergeSourceList();

    if (newSrc) {
      const card = els.mergeSourceList?.querySelector(`[data-sid="${CSS.escape(res.source_id)}"]`);
      await _fetchSchemaForSource(newSrc, card);
    }

    const sourceAddedText = typeof t === "function" ? t("add_source.source_added") : "Kaynak eklendi";
    showToast("success", sourceAddedText, res.message);
    _hideAddSourceForm();
  } catch (err) {
    const addErrorText = typeof t === "function" ? t("add_source.add_error") : "Kaynak eklenemedi";
    showToast("error", addErrorText, err.message, 5000);
  } finally {
    _setLoading(els.btnAddSourceConfirm, false, `
      <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2" style="width:10px;height:10px" aria-hidden="true">
        <path d="M1 6l4 4 6-7" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      ${connectAddText}`);
  }
}

/**
 * Backend kaynak listesini MergeState ile senkronize et.
 * Var olan sources'ların tables/schemaData/expanded değerlerini koru.
 */
function _syncSourcesFromBackend(backendSources) {
  const updated = backendSources.map((bs, idx) => {
    const existing = MergeState.sources.find(s => s.sourceId === bs.source_id);
    return {
      sourceId:   bs.source_id,
      sourceType: bs.source_type,
      alias:      bs.alias,
      isPrimary:  idx === 0,
      tables:     existing?.tables     ?? [],
      schemaData: existing?.schemaData ?? null,
      expanded:   existing?.expanded   ?? false,
      loading:    false,
    };
  });
  MergeState.sources = updated;
}

/* ═══════════════════════════════════════════════════════════
   Tüm kaynakların şemasını arka planda yükle
═══════════════════════════════════════════════════════════ */
async function _loadMultiSchema() {
  if (!State.sessionId) return;
  try {
    const multi = await apiGetMultiSchema(State.sessionId);
    if (!multi?.sources) return;

    multi.sources.forEach(ms => {
      const s = MergeState.sources.find(x => x.sourceId === ms.source_id);
      if (s && !s.schemaData) {
        s.schemaData = {
          tables:      ms.tables      || [],
          collections: ms.collections || [],
          files:       ms.files       || [],
          error:       ms.error       || null,
        };
        s.loading = false;
        // Eğer accordion açıksa body'yi güncelle
        if (s.expanded) {
          const card = els.mergeSourceList?.querySelector(`[data-sid="${CSS.escape(s.sourceId)}"]`);
          const body = card?.querySelector(".msrc-body");
          if (body) {
            body.innerHTML = _buildTableList(s);
            body.querySelectorAll(".msrc-cb").forEach(cb => {
              cb.addEventListener("change", () => _onTableCheck(s.sourceId, cb));
            });
            const btnAll  = body.querySelector(".msrc-sel-all");
            const btnNone = body.querySelector(".msrc-sel-none");
            if (btnAll)  btnAll.addEventListener("click",  () => _selectAllTables(s.sourceId, true));
            if (btnNone) btnNone.addEventListener("click", () => _selectAllTables(s.sourceId, false));
          }
        }
      }
    });
  } catch { /* arka plan — sessizce geç */ }
}

/* ═══════════════════════════════════════════════════════════
   "Tüm Kaynaklarla Sorgula" butonu
═══════════════════════════════════════════════════════════ */
function _handleRunMerge() {
  if (MergeState.sources.length < 2) return;
  const labels = MergeState.sources.map(s => s.alias).join(" + ");
  const queryText = typeof t === "function" ? t("merge.query_text", { sources: labels }) : `${labels} kaynaklarındaki verileri karşılaştır ve özet analiz yap`;
  const mergeReadyTitle = typeof t === "function" ? t("toast.merge_ready") : "Birleştirme hazır";
  const mergeReadyMsg = typeof t === "function" ? t("toast.merge_ready_message") : "Gönder tuşuna basarak çoklu kaynak analizini başlatın.";
  els.questionInput.value = queryText;
  _autoResize(els.questionInput);
  els.questionInput.focus();
  showToast("info", mergeReadyTitle, mergeReadyMsg);
}

/* ═══════════════════════════════════════════════════════════
   Data Search
═══════════════════════════════════════════════════════════ */
let _searchDebounce = null;

function _handleDataSearch(e) {
  const q = e.target.value.trim();
  clearTimeout(_searchDebounce);
  if (!q) { _closeSearchResults(); return; }
  _searchDebounce = setTimeout(() => _runDataSearch(q), 250);
}

function _runDataSearch(query) {
  _renderSearchResults(_collectSearchResults(query), query);
}

function _collectSearchResults(query) {
  const ql = query.toLowerCase(), hits = [];
  const sText = els.schemaText?.textContent || "";
  if (sText) {
    sText.split("\n").forEach((line, i) => {
      if (line.toLowerCase().includes(ql))
        hits.push({ type:"schema", text:line.trim(), line:i+1 });
    });
  }
  if (typeof messageHistory !== "undefined") {
    messageHistory.forEach(msg => {
      if ((msg.text||"").toLowerCase().includes(ql)) {
        hits.push({
          type: msg.role === "user" ? "user-msg" : "agent-msg",
          text: _extractSnippet(msg.text, ql), ts: msg.ts,
        });
      }
    });
  }
  return hits.slice(0, 30);
}

function _extractSnippet(text, query) {
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx < 0) return text.slice(0,80) + "…";
  const s = Math.max(0, idx-30), e = Math.min(text.length, idx+query.length+50);
  return (s>0?"…":"") + text.slice(s,e) + (e<text.length?"…":"");
}

function _highlightMatch(text, query) {
  const esc = text.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  return esc.replace(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")})`, "gi"),
    "<mark>$1</mark>");
}

function _renderSearchResults(results, query) {
  const box = els.dataSearchResults;
  if (!box) return;
  if (!results.length) {
    box.innerHTML = `<div class="dsr-empty">Sonuç bulunamadı: "<strong>${query}</strong>"</div>`;
    box.classList.add("open");
    return;
  }
  const typeLabel = { schema:"📋 Şema", "user-msg":"💬 Sen", "agent-msg":"🤖 Analiz" };
  box.innerHTML = results.map(r => `
    <div class="dsr-item" data-text="${(r.text||"").replace(/"/g,"&quot;")}">
      <span style="font-size:10px;opacity:.55;margin-right:6px">${typeLabel[r.type]||""}</span>
      ${_highlightMatch(r.text, query)}
    </div>`).join("");
  box.classList.add("open");
  box.querySelectorAll(".dsr-item").forEach(item => {
    item.addEventListener("click", () => {
      if (item.dataset.text && els.questionInput) {
        els.questionInput.value = item.dataset.text;
        _autoResize(els.questionInput);
        els.questionInput.focus();
      }
      _closeSearchResults();
    });
  });
}

function _closeSearchResults() {
  els.dataSearchResults?.classList.remove("open");
}

/* ═══════════════════════════════════════════════════════════
   Button handlers
═══════════════════════════════════════════════════════════ */
async function handleTestConnection() {
  const lang = typeof getLanguage === "function" ? getLanguage() : "tr";
  const testingText = lang === "tr" ? "Test ediliyor…" : "Testing…";
  _setDot("testing", testingText);
  _setLoading(els.btnTestConn, true, testingText);
  try {
    const result = await apiTestConnection(buildConnectPayload());
    const successText = lang === "tr" ? "Test başarılı" : "Test successful";
    const connSuccessText = lang === "tr" ? "Bağlantı başarılı" : "Connection successful";
    _setDot("connected", successText);
    showToast("success", connSuccessText,
      result.version || result.database || result.bucket || "");
  } catch (err) {
    const failText = lang === "tr" ? "Test başarısız" : "Test failed";
    const connFailText = lang === "tr" ? "Bağlantı testi başarısız" : "Connection test failed";
    _setDot("error", failText);
    showToast("error", connFailText, err.message, 5000);
  } finally {
    const testBtnText = lang === "tr" ? "Test Et" : "Test";
    _setLoading(els.btnTestConn, false, testBtnText);
    if (!State.isConnected) {
      const waitingText = lang === "tr" ? "Bağlantı bekleniyor" : "Waiting for connection";
      setTimeout(() => { if (!State.isConnected) _setDot("", waitingText); }, 3000);
    }
  }
}

async function handleConnect() {
  const lang = typeof getLanguage === "function" ? getLanguage() : "tr";
  const connectingText = lang === "tr" ? "Bağlanıyor…" : "Connecting…";
  _setDot("testing", connectingText);
  _setLoading(els.btnConnect, true, connectingText);
  try {
    const payload = buildConnectPayload();
    const res = await apiConnect(payload);
    State._lastConnectPayload = payload; // session expire olunca otomatik reconnect için
    // res.source_id artık backend'den geliyor (gerçek src_xxx ID)
    _setConnected(res.session_id, res.source_type, res.source_id, _srcLabel(res.source_type));
    const connectedText = lang === "tr" ? "Bağlantı kuruldu" : "Connected";
    showToast("success", connectedText, res.message);

    // Şemayı yükle: sidebar şema paneline + birincil kaynağın accordion'una
    _loadSchema(res.session_id);
    // Birincil kaynağı hemen aç ve şemasını çek
    const primarySrc = MergeState.sources[0];
    if (primarySrc) {
      primarySrc.expanded = true;
      primarySrc.loading  = true;
      _renderMergeSourceList();
      const card = els.mergeSourceList?.querySelector(`[data-sid="${CSS.escape(primarySrc.sourceId)}"]`);
      _fetchSchemaForSource(primarySrc, card);
    }
  } catch (err) {
    const errorText = lang === "tr" ? "Bağlantı hatası" : "Connection error";
    const failedText = lang === "tr" ? "Bağlanılamadı" : "Connection failed";
    _setDot("error", errorText);
    showToast("error", failedText, err.message, 5000);
    const waitingText = lang === "tr" ? "Bağlantı bekleniyor" : "Waiting for connection";
    setTimeout(() => { if (!State.isConnected) _setDot("", waitingText); }, 3000);
  } finally {
    const connectBtnText = lang === "tr" ? "Bağlan" : "Connect";
    _setLoading(els.btnConnect, false, connectBtnText);
  }
}

async function handleDisconnect() {
  if (!State.sessionId) return;
  const lang = typeof getLanguage === "function" ? getLanguage() : "tr";
  _setLoading(els.btnDisconnect, true, "");
  try { 
    await apiDisconnect(State.sessionId); 
    const disconnectedText = lang === "tr" ? "Bağlantı kesildi" : "Disconnected";
    showToast("info", disconnectedText); 
  }
  catch { /* ignore */ }
  finally { 
    _setDisconnected(); 
    const disconnectBtnText = lang === "tr" ? "Bağlantıyı Kes" : "Disconnect";
    _setLoading(els.btnDisconnect, false, disconnectBtnText); 
  }
}

async function _loadSchema(sessionId) {
  const btn = els.btnRefreshSchema;
  if (btn) btn.classList.add("spinning");
  try {
    const schema = await apiGetSchema(sessionId);
    State.schemaData = schema;
    // Birincil kaynağın schemaData güncelle
    if (MergeState.sources[0]?.isPrimary) {
      MergeState.sources[0].schemaData = {
        tables:      schema.tables      || [],
        collections: schema.collections || [],
        files:       schema.files       || [],
      };
    }
    els.schemaText.textContent = schema.schema_text || "(Şema boş)";
    els.schemaPanel.classList.remove("hidden");
  } catch (err) {
    els.schemaText.textContent = `Şema yüklenemedi: ${err.message}`;
    els.schemaPanel.classList.remove("hidden");
  } finally {
    if (btn) btn.classList.remove("spinning");
  }
}

/* ── handleSend — source_selection ile ───────────────────── */
async function handleSend() {
  if (State.isSending || !State.isConnected) return;
  const question = els.questionInput.value.trim();
  if (!question) return;

  State.isSending = true;
  els.questionInput.value = "";
  _autoResize(els.questionInput);
  els.sendBtn.disabled = true;

  addUserMessage(question);
  showProcessing();

  const stepKeys = ["schema","sql","execute","clean","insight"];
  let stepIdx = 0;
  const stepTimer = setInterval(() => {
    if (stepIdx < stepKeys.length) advanceStep(stepKeys[stepIdx++]);
    else clearInterval(stepTimer);
  }, 900);

  if (window.innerWidth <= 768) els.sidebar.classList.add("collapsed");

  const sourceSelection = MergeState.sources.map(s => ({
    source_id: s.sourceId,
    tables:    s.tables || [],
  }));

  try {
    let response;
    try {
      response = await apiAsk(State.sessionId, question, sourceSelection);
    } catch (err) {
      // Session süresi dolmuşsa otomatik yeniden bağlan ve tekrar dene
      const isSessionExpired = err.message && (
        err.message.includes("Oturum bulunamadı") ||
        err.message.includes("süresi doldu") ||
        err.message.includes("404") ||
        err.message.includes("session")
      );
      if (isSessionExpired && State._lastConnectPayload) {
        showToast("info", "Oturum yenileniyor", "Bağlantı yeniden kuruluyor…", 3000);
        try {
          const reconnect = await apiConnect(State._lastConnectPayload);
          State.sessionId = reconnect.session_id;
          response = await apiAsk(State.sessionId, question, sourceSelection);
        } catch (reconnectErr) {
          throw reconnectErr;
        }
      } else {
        throw err;
      }
    }
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
   Helpers
═══════════════════════════════════════════════════════════ */
function _setLoading(btn, on, label) {
  if (!btn) return;
  btn.disabled = on;
  btn.innerHTML = on
    ? `<span class="btn-spinner"></span>${label ? `<span>${label}</span>` : ""}`
    : label;
}

function _autoResize(ta) {
  ta.style.height = "auto";
  ta.style.height = Math.min(ta.scrollHeight, 140) + "px";
}

/* ═══════════════════════════════════════════════════════════
   Event binding
═══════════════════════════════════════════════════════════ */
function _bindEvents() {
  els.sidebarToggle.addEventListener("click", () => els.sidebar.classList.toggle("collapsed"));
  els.menuBtn.addEventListener("click",        () => els.sidebar.classList.toggle("collapsed"));

  document.addEventListener("click", e => {
    if (window.innerWidth > 768) return;
    if (!els.sidebar.classList.contains("collapsed") &&
        !els.sidebar.contains(e.target) &&
        e.target !== els.menuBtn) {
      els.sidebar.classList.add("collapsed");
    }
    if (els.dataSearchResults && !els.dataSearchWrap?.contains(e.target))
      _closeSearchResults();
  });

  // Source tabs — sadece bağlı değilken aktif (add-source formu kendi tipini yönetiyor)
  els.sourceTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      if (!State.isConnected) _switchSource(tab.dataset.src);
    });
  });

  els.btnTestConn.addEventListener("click",   handleTestConnection);
  els.btnConnect.addEventListener("click",    handleConnect);
  els.btnDisconnect.addEventListener("click", handleDisconnect);

  els.btnRefreshSchema?.addEventListener("click", () => {
    if (State.sessionId) { _loadSchema(State.sessionId); _loadMultiSchema(); }
  });

  els.btnClearChat?.addEventListener("click", () => {
    const msg = typeof getLanguage === "function" && getLanguage() === "tr"
      ? "Sohbet ekranı temizlenecek. Devam edilsin mi?"
      : "Chat screen will be cleared. Continue?";
    if (!confirm(msg)) return;
    clearHistory(); showToast("info", typeof getLanguage === "function" && getLanguage() === "tr" ? "Sohbet temizlendi" : "Chat cleared");
  });

  els.btnGenerateReport?.addEventListener("click", async () => {
    const lang = typeof getLanguage === "function" ? getLanguage() : "tr";

    if (!State.sessionId) {
      showToast("error", lang === "tr"
        ? "Lütfen önce bir veri kaynağına bağlanın."
        : "Please connect to a data source first.");
      return;
    }

    const chatHistory = typeof messageHistory !== "undefined" ? messageHistory : [];
    const question    = els.questionInput?.value?.trim() || "";

    if (!question && chatHistory.length === 0) {
      showToast("error", lang === "tr"
        ? "Lütfen bir soru girin veya önce sohbet başlatın."
        : "Please enter a question or start a conversation first.");
      return;
    }

    // ── Sharing modal göster ──────────────────────────────
    const modal      = document.getElementById("reportShareModal");
    const closeBtn   = document.getElementById("closeReportModal");
    const cancelBtn  = document.getElementById("cancelReportShare");
    const confirmBtn = document.getElementById("confirmReportShare");
    if (!modal) return;

    modal.style.display = "flex";

    const closeModal = () => {
      modal.style.display = "none";
      document.getElementById("shareEmails").value   = "";
      document.getElementById("makePublic").checked  = false;
    };

    const handleGenerate = async () => {
      const emailsRaw  = document.getElementById("shareEmails").value;
      const makePublic = document.getElementById("makePublic").checked;
      const shareWithEmails = emailsRaw
        .split(",").map(e => e.trim()).filter(e => e.includes("@"));

      closeModal();
      showToast("info", lang === "tr" ? "Rapor oluşturuluyor…" : "Generating report…");

      // Butonu disable ederek çift tıklamayı engelle
      if (els.btnGenerateReport) els.btnGenerateReport.disabled = true;

      try {
        const response = await apiGenerateReport(
          State.sessionId, question, null, chatHistory, shareWithEmails, makePublic
        );

        if (question) addUserMessage(question);
        addAgentMessage(response);

        // ── Dashboard linki oluştur ────────────────────────
        const reportId   = response.report_id;
        const publicLink = response.public_link; // "/api/v1/reports/public/rpt_xxx"

        if (reportId) {
          // Dashboard URL: her zaman public_id param ile → dashboard sayfası
          const dashBase    = "../dashboard/index.html";
          let   dashUrl;

          if (makePublic && publicLink) {
            // Herkese açık: ?public_id= ile — auth gereksiz
            dashUrl = `${dashBase}?public_id=${encodeURIComponent(reportId)}`;
          } else {
            // Sadece yetkili kullanıcılar: ?report_id= ile (JWT gönderir)
            dashUrl = `${dashBase}?report_id=${encodeURIComponent(reportId)}`;
          }

          // Başarı overlay'ini doldur
          const overlay   = document.getElementById("reportSuccessOverlay");
          const linkInput = document.getElementById("reportSuccessLink");
          if (overlay && linkInput) {
            // Paylaşım linki: public ise tam URL, değilse dashboard URL
            const shareableUrl = makePublic
              ? `${window.location.origin}${publicLink.replace("/api/v1/reports/public/", "")}${dashBase.replace("..", "")}?public_id=${encodeURIComponent(reportId)}`
              : `${window.location.origin.replace(/\/[^/]*$/, "")}${dashUrl.replace("..", "")}`;

            linkInput.value = dashUrl; // göreceli yol daha güvenilir

            overlay.style.display = "flex";

            // Dashboard'a git butonu (yeni bir tane oluştur)
            const existingBtn = overlay.querySelector(".btn-open-dashboard");
            if (!existingBtn) {
              const openBtn = document.createElement("button");
              openBtn.className = "btn-open-dashboard close-overlay-btn";
              openBtn.style.cssText = "background:var(--indigo);margin-right:8px;";
              openBtn.textContent   = lang === "tr" ? "Dashboard'u Aç" : "Open Dashboard";
              openBtn.addEventListener("click", () => window.open(dashUrl, "_blank"));
              const closeOverlayBtn = document.getElementById("closeSuccessOverlay");
              if (closeOverlayBtn) overlay.querySelector(".report-success-content").insertBefore(openBtn, closeOverlayBtn);
            } else {
              existingBtn.onclick = () => window.open(dashUrl, "_blank");
              existingBtn.textContent = lang === "tr" ? "Dashboard'u Aç" : "Open Dashboard";
            }

            // Copy butonu
            const copyBtn = document.getElementById("copySuccessLink");
            if (copyBtn) {
              const newCopy = copyBtn.cloneNode(true);
              copyBtn.parentNode.replaceChild(newCopy, copyBtn);
              newCopy.addEventListener("click", async () => {
                const textToCopy = window.location.origin.split("/chat")[0] + "/" + dashUrl.replace("../", "");
                try { await navigator.clipboard.writeText(textToCopy); }
                catch { /* ignore */ }
                const origHtml = newCopy.innerHTML;
                newCopy.innerHTML = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 8l3 3 7-7" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
                setTimeout(() => { newCopy.innerHTML = origHtml; }, 2000);
                showToast("success", lang === "tr" ? "Link kopyalandı" : "Link copied");
              });
            }

            // Kapat butonu
            const closeOverlay = document.getElementById("closeSuccessOverlay");
            if (closeOverlay) {
              const newClose = closeOverlay.cloneNode(true);
              closeOverlay.parentNode.replaceChild(newClose, closeOverlay);
              newClose.addEventListener("click", () => {
                overlay.style.display = "none";
                linkInput.value = "";
                // eski dashboard butonunu temizle
                overlay.querySelector(".btn-open-dashboard")?.remove();
              });
            }
          }
        }

        // E-posta bildirimi
        if (shareWithEmails.length > 0) {
          showToast("success", lang === "tr"
            ? `Rapor ${shareWithEmails.length} alıcıya gönderildi.`
            : `Report sent to ${shareWithEmails.length} recipients.`);
        }

        showToast("success", lang === "tr"
          ? "Rapor başarıyla oluşturuldu."
          : "Report generated successfully.");

      } catch (error) {
        showToast("error", lang === "tr"
          ? `Rapor oluşturma hatası: ${error.message}`
          : `Report generation error: ${error.message}`);
      } finally {
        if (els.btnGenerateReport) els.btnGenerateReport.disabled = false;
      }
    };

    // Event listener'ları temiz bağla (clone trick)
    const newCloseBtn = closeBtn.cloneNode(true);
    closeBtn.parentNode.replaceChild(newCloseBtn, closeBtn);
    newCloseBtn.addEventListener("click", closeModal);

    const newCancelBtn = cancelBtn.cloneNode(true);
    cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
    newCancelBtn.addEventListener("click", closeModal);

    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
    newConfirmBtn.addEventListener("click", handleGenerate);

    // Modal dışına tıklayınca kapat
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModal();
    });
  });

  els.btnClearHistory?.addEventListener("click", () => {
    const msg = typeof getLanguage === "function" && getLanguage() === "tr" 
      ? "Tüm konuşma geçmişi silinecek. Devam edilsin mi?" 
      : "All conversation history will be deleted. Continue?";
    if (confirm(msg)) {
      clearHistory(); showToast("info", typeof getLanguage === "function" && getLanguage() === "tr" ? "Geçmiş temizlendi" : "History cleared");
    }
  });

  // Merge panel
  els.btnAddSource?.addEventListener("click",        _showAddSourceForm);
  els.btnRunMerge?.addEventListener("click",         _handleRunMerge);
  els.btnAddSourceConfirm?.addEventListener("click", _handleAddSourceConfirm);
  els.btnAddSourceCancel?.addEventListener("click",  _hideAddSourceForm);

  // Data search
  els.dataSearchInput?.addEventListener("input", _handleDataSearch);
  els.dataSearchInput?.addEventListener("keydown", e => {
    if (e.key === "Escape") { els.dataSearchInput.value = ""; _closeSearchResults(); }
  });
  els.dataSearchInput?.addEventListener("focus", () => {
    if (els.dataSearchInput.value.trim()) _runDataSearch(els.dataSearchInput.value.trim());
  });

  // Send
  els.sendBtn.addEventListener("click", handleSend);
  els.questionInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  });
  els.questionInput.addEventListener("input", () => _autoResize(els.questionInput));

  // Suggestion cards
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

  // Auth butonları auth.js tarafından yönetiliyor — burada ekstra listener bağlama

  // Initialize auth UI state
  if (typeof updateAuthUI === "function") updateAuthUI();
}

/* ═══════════════════════════════════════════════════════════
   Boot
═══════════════════════════════════════════════════════════ */
function _boot() {
  _initEls();
  _switchSource("postgresql");
  _setDisconnected();
  // Don't restore history on boot - start fresh with welcome state
  // restoreHistory();
  _setEmptyVisible(true);
  _bindEvents();

  // Session restore (sayfa yenilenince)
  const sid   = sessionStorage.getItem("nx_sid");
  const src   = sessionStorage.getItem("nx_src");
  const srcId = sessionStorage.getItem("nx_sid2");
  if (sid && src) {
    apiGetSchema(sid)
      .then(schema => {
        _setConnected(sid, src, srcId || "primary", _srcLabel(src));
        State.schemaData = schema;
        if (MergeState.sources[0]) {
          MergeState.sources[0].schemaData = {
            tables:      schema.tables      || [],
            collections: schema.collections || [],
            files:       schema.files       || [],
          };
          // Açık bırakıyoruz; tıklayınca açılır
        }
        els.schemaText.textContent = schema.schema_text || "";
        els.schemaPanel.classList.remove("hidden");
        showToast("info", "Önceki oturum geri yüklendi", _srcLabel(src));
        _loadMultiSchema();
      })
      .catch(() => {
        sessionStorage.removeItem("nx_sid");
        sessionStorage.removeItem("nx_src");
        sessionStorage.removeItem("nx_sid2");
      });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", _boot);
} else {
  _boot();
}
