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
  return apiFetch("/chat/ask", {
    method: "POST",
    body: JSON.stringify({
      session_id:       sessionId,
      question,
      source_selection: sourceSelection,
    }),
  });
}

/* ═══════════════════════════════════════════════════════════
   Payload Builders — form verilerini API formatına çevirir
═══════════════════════════════════════════════════════════ */

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
