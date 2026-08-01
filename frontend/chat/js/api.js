/**
 * api.js — Backend API iletişim katmanı
 *
 * Tüm fetch çağrıları burada merkezi olarak yönetilir.
 * Base URL: http://localhost:8000/api/v1
 */

// Production'da aynı origin'den serve edilir (relative URL).
// Lokal geliştirmede localhost:8000'i kullanmak için:
//   window.API_BASE_OVERRIDE = "http://localhost:8000/api/v1"
const API_BASE = window.API_BASE_OVERRIDE || "/api/v1";

/* ═══════════════════════════════════════════════════════════
   Auth Token — localStorage yönetimi
═══════════════════════════════════════════════════════════ */

const AUTH_TOKEN_KEY = "nexus_auth_token";
const AUTH_USER_KEY  = "nexus_auth_user";

/** Token'ı localStorage'a kaydeder. */
function setAuthToken(token) {
  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  }
}

/** Kaydedilmiş token'ı döner; yoksa null. */
function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

/** Geçerli bir token var mı? */
function isAuthenticated() {
  return Boolean(getAuthToken());
}

/** Kullanıcı bilgisini localStorage'a kaydeder. */
function setAuthUser(user) {
  if (user) {
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
  } else {
    localStorage.removeItem(AUTH_USER_KEY);
  }
}

/** Kaydedilmiş kullanıcı bilgisini döner; yoksa null. */
function getAuthUser() {
  const raw = localStorage.getItem(AUTH_USER_KEY);
  try { return raw ? JSON.parse(raw) : null; } catch { return null; }
}

/** Token + kullanıcı bilgisini temizler (logout). */
function clearAuth() {
  setAuthToken(null);
  setAuthUser(null);
}

/* ─── Generic fetch wrapper ───────────────────────────────── */
async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;

  // Eğer token varsa Authorization başlığını otomatik ekle
  const authHeaders = {};
  const token = getAuthToken();
  if (token) {
    authHeaders["Authorization"] = `Bearer ${token}`;
  }

  const defaults = {
    headers: { "Content-Type": "application/json" },
  };
  const config = {
    ...defaults,
    ...options,
    headers: { ...defaults.headers, ...authHeaders, ...(options.headers || {}) },
  };

  const res = await fetch(url, config);

  // 204 No Content
  if (res.status === 204) return null;

  // Token süresi dolduysa oturumu kapat
  if (res.status === 401) {
    clearAuth();
    if (typeof updateAuthUI === "function") updateAuthUI();
  }

  // Body'yi güvenli şekilde parse et — boş veya HTML gelebilir
  let data = null;
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      data = await res.json();
    } catch {
      data = null;
    }
  } else {
    // JSON olmayan response (HTML hata sayfası vb.) — text olarak oku
    const text = await res.text().catch(() => "");
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}${text ? ": " + text.slice(0, 200) : ""}`);
    }
    return null;
  }

  if (!res.ok) {
    const msg = data?.detail || `HTTP ${res.status}`;
    throw new Error(msg);
  }

  return data;
}

/* ═══════════════════════════════════════════════════════════
   Auth Endpoints
═══════════════════════════════════════════════════════════ */

/**
 * POST /auth/register
 * Yeni kullanıcı kaydı. Başarılı olursa TokenResponse döner.
 * @param {string} email
 * @param {string} password
 * @param {string} [fullName]
 * @returns {Object} { access_token, token_type, email, full_name }
 */
async function apiRegister(email, password, fullName = null) {
  const payload = { email, password };
  if (fullName) payload.full_name = fullName;
  return apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * POST /auth/login
 * E-posta + şifre ile giriş. Başarılı olursa TokenResponse döner.
 * @param {string} email
 * @param {string} password
 * @returns {Object} { access_token, token_type, email, full_name }
 */
async function apiLogin(email, password) {
  return apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

/**
 * GET /auth/me
 * Mevcut token ile kullanıcı bilgilerini getirir.
 * @returns {Object} { email, full_name }
 */
async function apiGetMe() {
  return apiFetch("/auth/me");
}

/**
 * Frontend logout — sunucuya istek atmadan token'ı temizler.
 */
function apiLogout() {
  clearAuth();
}

/* ═══════════════════════════════════════════════════════════
   Connect-DB Endpoints
═══════════════════════════════════════════════════════════ */

/**
 * Kullanıcı localhost/127.0.0.1 içeren bir URL girerse
 * ilgili input alanının altında uyarı gösterir.
 * Cloud Run veya Docker dışı ortamlarda gerçek host girilmesi gerekir.
 */
function _warnIfLocalhost(payload) {
  const localhostPattern = /localhost|127\.0\.0\.1/i;
  const urlValue = payload.connection_url || payload.mongodb_uri || "";
  const isLocal = localhostPattern.test(urlValue);

  // connection_url hint
  const urlHint = document.getElementById("connectionUrlHint");
  if (urlHint) {
    if (isLocal && (payload.source_type === "mysql" || payload.source_type === "postgresql")) {
      urlHint.textContent = "⚠ 'localhost' bu sunucudan erişilemez. Docker içinde servis adını kullanın (örn: mysql, postgres).";
      urlHint.style.display = "block";
    } else {
      urlHint.style.display = "none";
    }
  }

  // mongodb_uri hint
  const mongoHint = document.getElementById("mongodbUriHint");
  if (mongoHint) {
    if (isLocal && payload.source_type === "mongodb") {
      mongoHint.textContent = "⚠ 'localhost' bu sunucudan erişilemez. Docker içinde 'mongo' servis adını kullanın (örn: mongodb://mongo:27017/mydb).";
      mongoHint.style.display = "block";
    } else {
      mongoHint.style.display = "none";
    }
  }
}

/**
 * POST /connect-db/test
 * Bağlantı bilgilerini test eder, oturum açmaz.
 * @param {Object} payload  ConnectDbRequest
 * @returns {Object}        TestConnectionResponse
 */
async function apiTestConnection(payload) {
  _warnIfLocalhost(payload);
  return apiFetch("/connect-db/test", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * POST /connect-db/connect
 * Oturum açar, session_id döner.
 * @param {Object} payload  ConnectDbRequest
 * @returns {Object}        ConnectDbResponse  { status, source_type, message, session_id }
 */
async function apiConnect(payload) {
  _warnIfLocalhost(payload);
  return apiFetch("/connect-db/connect", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * GET /connect-db/schema/{session_id}
 * Bağlı (birincil) kaynağın şemasını getirir.
 * @param {string} sessionId
 * @returns {Object}  SchemaResponse
 */
async function apiGetSchema(sessionId) {
  return apiFetch(`/connect-db/schema/${encodeURIComponent(sessionId)}`);
}

/**
 * GET /connect-db/multi-schema/{session_id}
 * Session'daki TÜM kaynakların şemalarını tek seferde getirir.
 * Her kaynak için tablo/koleksiyon listesi de döner.
 * @param {string} sessionId
 * @returns {Object}  MultiSourceSchemaResponse
 *   { session_id, sources: [{ source_id, source_type, alias, schema_text, tables, collections, files, error }] }
 */
async function apiGetMultiSchema(sessionId) {
  return apiFetch(`/connect-db/multi-schema/${encodeURIComponent(sessionId)}`);
}

/**
 * POST /connect-db/add-source
 * Mevcut bir oturuma yeni bir veri kaynağı ekler.
 * @param {Object} payload  AddSourceRequest
 *   { session_id, alias?, source_type, connection_url?, mongodb_uri?, ... }
 * @returns {Object}  AddSourceResponse
 *   { ok, session_id, source_id, source_type, alias, message, sources[] }
 */
async function apiAddSource(payload) {
  return apiFetch("/connect-db/add-source", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * DELETE /connect-db/remove-source/{session_id}/{source_id}
 * Oturumdan bir veri kaynağını kaldırır (birincil kaynak kaldırılamaz).
 * @param {string} sessionId
 * @param {string} sourceId
 * @returns {Object}  RemoveSourceResponse
 */
async function apiRemoveSource(sessionId, sourceId) {
  return apiFetch(
    `/connect-db/remove-source/${encodeURIComponent(sessionId)}/${encodeURIComponent(sourceId)}`,
    { method: "DELETE" }
  );
}

/**
 * DELETE /connect-db/disconnect/{session_id}
 * Oturumu tamamen kapatır.
 * @param {string} sessionId
 * @returns {Object}  DisconnectResponse
 */
async function apiDisconnect(sessionId) {
  return apiFetch(`/connect-db/disconnect/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
}

/* ═══════════════════════════════════════════════════════════
   Chat Endpoint
═══════════════════════════════════════════════════════════ */

/**
 * POST /chat/ask
 * Doğal dil sorusunu ajana gönderir.
 *
 * Tek kaynak modu (sourceSelection boş):
 *   apiAsk(sessionId, question)
 *
 * Çoklu kaynak modu (sourceSelection dolu):
 *   apiAsk(sessionId, question, [
 *     { source_id: "src_001", tables: ["orders"] },
 *     { source_id: "src_002", tables: [] },        // tüm tablolar
 *   ])
 *
 * @param {string}   sessionId       Aktif session
 * @param {string}   question        Kullanıcının sorusu
 * @param {Array}    [sourceSelection]  [{source_id, tables:[]}]
 * @returns {Object} ChatResponse
 *   { status, summary, sql_query, chart_data, action_plan, sources_queried }
 */
async function apiAsk(sessionId, question, sourceSelection = []) {
  const language = typeof getLanguage === "function" ? getLanguage() : "tr";
  return apiFetch("/chat/ask", {
    method: "POST",
    body: JSON.stringify({
      session_id:       sessionId,
      question,
      language,
      source_selection: sourceSelection,
    }),
  });
}

/* ═══════════════════════════════════════════════════════════
   Reports Endpoint
═══════════════════════════════════════════════════════════ */

/**
 * POST /reports/generate
 * InsightGeneratorAgent kullanarak rapor oluşturur.
 * @param {string} sessionId  Aktif session
 * @param {string} question  Rapor sorusu
 * @param {string} [language] Rapor dili (tr/en)
 * @param {Array} [chatHistory] Sohbet geçmişi
 * @returns {Object} ChatResponse formatında rapor içeriği
 */
async function apiGenerateReport(sessionId, question, language = null, chatHistory = [], shareWithEmails = [], makePublic = false) {
  const lang = language || (typeof getLanguage === "function" ? getLanguage() : "tr");
  return apiFetch("/reports/generate", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      question,
      language: lang,
      chat_history: chatHistory,
      share_with_emails: shareWithEmails,
      make_public: makePublic,
    }),
  });
}

/**
 * GET /reports/public/{report_id}
 * Herkese açık raporu getirir — auth gerekmez.
 * @param {string} reportId
 * @returns {Object} ChatResponse formatında rapor içeriği
 */
async function apiGetPublicReport(reportId) {
  return apiFetch(`/reports/public/${encodeURIComponent(reportId)}`);
}

/**
 * GET /reports/{report_id}
 * Authenticated raporu getirir — JWT gerektirir.
 * @param {string} reportId
 * @returns {Object} ChatResponse formatında rapor içeriği
 */
async function apiGetReport(reportId) {
  return apiFetch(`/reports/${encodeURIComponent(reportId)}`);
}



/**
 * Sidebar form alanlarından ConnectDbRequest / AddSourceRequest payload'u üretir.
 *
 * @param {string|null} [sessionId]  Verilirse AddSourceRequest formatında üretir.
 * @param {string|null} [alias]      Kaynak için kullanıcı dostu ad.
 * @returns {Object}
 */
function buildConnectPayload(sessionId = null, alias = null) {
  const sourceType = document.getElementById("sourceType").value;
  const base = { source_type: sourceType };
  if (sessionId) base.session_id = sessionId;
  if (alias)     base.alias      = alias;

  switch (sourceType) {
    case "postgresql":
    case "mysql":
      return {
        ...base,
        connection_url: document.getElementById("connectionUrl").value.trim(),
      };

    case "mongodb":
      return {
        ...base,
        mongodb_uri: document.getElementById("mongodbUri").value.trim(),
      };

    case "s3":
      return {
        ...base,
        bucket_name:           document.getElementById("bucketName").value.trim(),
        aws_access_key_id:     document.getElementById("awsAccessKey").value.trim(),
        aws_secret_access_key: document.getElementById("awsSecretKey").value.trim(),
        aws_region:            document.getElementById("awsRegion").value.trim() || "eu-central-1",
      };

    case "snowflake":
      return {
        ...base,
        snowflake_account:   document.getElementById("sfAccount").value.trim(),
        snowflake_user:      document.getElementById("sfUser").value.trim(),
        snowflake_password:  document.getElementById("sfPassword").value.trim(),
        snowflake_database:  document.getElementById("sfDatabase").value.trim(),
        snowflake_schema:    document.getElementById("sfSchema").value.trim() || "PUBLIC",
        snowflake_warehouse: document.getElementById("sfWarehouse").value.trim() || undefined,
        snowflake_role:      document.getElementById("sfRole").value.trim() || undefined,
      };

    default:
      throw new Error(`Bilinmeyen kaynak tipi: ${sourceType}`);
  }
}
