export async function apiFetchResult(method, url, body) {
  const receivedAt = new Date().toISOString();
  try {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(10000),
    };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const r = await fetch(url, opts);
    if (!r.ok) {
      return {
        ok: false,
        data: null,
        status: r.status,
        error: `HTTP ${r.status}`,
        source: 'error',
        receivedAt,
      };
    }
    const text = await r.text();
    const data = text ? JSON.parse(text) : null;
    return {
      ok: true,
      data,
      status: r.status,
      error: null,
      source: data == null ? 'empty' : 'api',
      receivedAt,
    };
  } catch (error) {
    return {
      ok: false,
      data: null,
      status: 0,
      error: error?.name === 'TimeoutError' ? 'Timeout' : 'Network error',
      source: 'error',
      receivedAt,
    };
  }
}

async function apiFetch(method, url, body) {
  const result = await apiFetchResult(method, url, body);
  return result.ok ? result.data : null;
}

export const getDashboardSummary = () => apiFetch('GET', '/api/dashboard/summary');
export const getTasks = () => apiFetch('GET', '/api/tasks');
export const getOrders = () => apiFetch('GET', '/api/orders');
export const getProducts = () => apiFetch('GET', '/api/products');
export const getShipments = () => apiFetch('GET', '/api/shipments');
export const getMessages = (limit = 20) => apiFetch('GET', `/api/messages?limit=${limit}`);

export const updateTaskStatus = (id, status) =>
  apiFetch('PATCH', `/api/tasks/${id}`, { status });

export const generateBriefing = () =>
  apiFetch('POST', '/api/tasks/generate', {});

export const sendAlert = (payload) =>
  apiFetch('POST', '/api/alerts/send', payload);

export const sendChat = (message) =>
  apiFetch('POST', '/api/chat', { message });

export const getDashboardSummaryResult = () => apiFetchResult('GET', '/api/dashboard/summary');
export const getTasksResult = () => apiFetchResult('GET', '/api/tasks');
export const getOrdersResult = () => apiFetchResult('GET', '/api/orders');
export const getProductsResult = () => apiFetchResult('GET', '/api/products');
export const getShipmentsResult = () => apiFetchResult('GET', '/api/shipments');
export const getMessagesResult = (limit = 20) => apiFetchResult('GET', `/api/messages?limit=${limit}`);

export const updateTaskStatusResult = (id, status) =>
  apiFetchResult('PATCH', `/api/tasks/${id}`, { status });

export const generateBriefingResult = () =>
  apiFetchResult('POST', '/api/tasks/generate', {});

export const sendAlertResult = (payload) =>
  apiFetchResult('POST', '/api/alerts/send', payload);

export const sendChatResult = (message) =>
  apiFetchResult('POST', '/api/chat', { message });
