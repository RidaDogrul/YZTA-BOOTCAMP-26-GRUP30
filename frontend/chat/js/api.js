/**
 * api.js — Backend API iletişim katmanı
 *
 * Tüm fetch çağrıları burada merkezi olarak yönetilir.
 * Base URL: http://localhost:8000/api/v1
 */

const API_BASE = "http://localhost:8000/api/v1";

/* ─── Generic fetch wrapper ───────────────────────────────── */
async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const defaults = {
    headers: { "Content-Type": "application/json" },
  };
  const config = {
    ...defaults,
    ...options,
    headers: { ...defaults.headers, ...(options.headers || {}) },
  };

  const res = await fetch(url, config);

  // 204 No Content
  if (res.status === 204) return null;

  const data = await res.json();

  if (!res.ok) {
    // FastAPI error format: { detail: "..." }
    const msg = data?.detail || `HTTP ${res.status}`;
    throw new Error(msg);
  }

  return data;
}

/* ═══════════════════════════════════════════════════════════
   Connect-DB Endpoints
═══════════════════════════════════════════════════════════ */

/**
 * POST /connect-db/test
 * Bağlantı bilgilerini test eder, oturum açmaz.
 * @param {Object} payload  ConnectDbRequest
 * @returns {Object}        TestConnectionResponse
 */
async function apiTestConnection(payload) {
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
  return apiFetch("/connect-db/connect", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * GET /connect-db/schema/{session_id}
 * Bağlı kaynağın şemasını getirir.
 * @param {string} sessionId
 * @returns {Object}  SchemaResponse
 */
async function apiGetSchema(sessionId) {
  return apiFetch(`/connect-db/schema/${encodeURIComponent(sessionId)}`);
}

/**
 * DELETE /connect-db/disconnect/{session_id}
 * Oturumu kapatır.
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
 * @param {string} sessionId   Aktif session
 * @param {string} question    Kullanıcının sorusu
 * @returns {Object}           ChatResponse { status, summary, sql_query, chart_data, action_plan }
 */
async function apiAsk(sessionId, question) {
  return apiFetch("/chat/ask", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, question }),
  });
}

/* ═══════════════════════════════════════════════════════════
   Payload Builders — form verilerini API formatına çevirir
═══════════════════════════════════════════════════════════ */

/**
 * Sidebar form alanlarından ConnectDbRequest payload'u üretir.
 * @returns {Object}
 */
function buildConnectPayload() {
  const sourceType = document.getElementById("sourceType").value;
  const base = { source_type: sourceType };

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
