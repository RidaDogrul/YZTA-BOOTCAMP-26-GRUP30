import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const testDir = dirname(fileURLToPath(import.meta.url));
const root = resolve(testDir, '..');

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8');
}

function assertIncludesAll(source, expectedSnippets) {
  for (const snippet of expectedSnippets) {
    assert.ok(source.includes(snippet), `Expected source to include: ${snippet}`);
  }
}

test('package exposes a frontend test command without extra framework dependency', () => {
  const pkg = JSON.parse(read('package.json'));
  assert.equal(pkg.scripts.test, 'node --test tests/*.test.mjs');
});

test('vite build packages the React app and both final static MVP pages', () => {
  const config = read('vite.config.js');

  assertIncludesAll(config, [
    "main: 'index.html'",
    "dashboard: 'dashboard.html'",
    "chat: 'chat.html'",
  ]);
});

test('API client uses the documented final backend endpoints', () => {
  const client = read('src/api/client.js');

  assertIncludesAll(client, [
    "apiFetch('GET', '/api/dashboard/summary')",
    "apiFetch('GET', '/api/tasks')",
    "apiFetch('GET', '/api/orders')",
    "apiFetch('GET', '/api/products')",
    "apiFetch('GET', '/api/shipments')",
    "apiFetch('POST', '/api/tasks/generate'",
    "apiFetch('POST', '/api/alerts/send'",
    "apiFetch('POST', '/api/chat'",
  ]);
  assert.doesNotMatch(client, /\/api\/ai\/tasks\/generate/);
});

test('React router exposes all operational views required by the final document', () => {
  const app = read('src/App.jsx');

  assertIncludesAll(app, [
    'path="/" element={<DashboardPage />}',
    'path="/orders" element={<OrdersPage />}',
    'path="/shipments" element={<ShipmentsPage />}',
    'path="/products" element={<ProductsPage />}',
    'path="/tasks" element={<TasksPage />}',
    'path="/pending" element={<PendingPage />}',
    'path="/chat" element={<ChatPage />}',
  ]);
});

test('React chat page covers Case 1-5 demo prompts and AI metadata', () => {
  const chat = read('src/pages/ChatPage.jsx');

  assertIncludesAll(chat, [
    '142 numaralı siparişim nerede?',
    'Organik zeytinyağı stokta var mı?',
    'Bugünün özetini ver',
    'Kritik stokları listele',
    '128 numaralı sipariş ne zaman teslim?',
    'TypingIndicator',
    'res.intent',
    'res.tool_calls',
    'res.dashboard_note',
  ]);
});

test('React dashboard surfaces final document cards, alerts, briefing, and approvals', () => {
  const dashboard = read('src/pages/DashboardPage.jsx');

  assertIncludesAll(dashboard, [
    'Toplam Sipariş',
    'Hazırlanıyor',
    'Kargoda',
    'Teslim Edildi',
    'Gecikmiş',
    'Kritik Stok',
    'Onay Bekliyor',
    'AI Günlük Brifing',
    'POST /api/tasks/generate',
    'Gecikmiş Siparişler',
    'Kritik Stok Uyarısı',
    'Onay Bekleyen Aksiyonlar',
    'openMailModal',
    'updateTaskStatus',
    'isPendingApproval',
    'shipmentByOrder',
  ]);
  assert.doesNotMatch(dashboard, /\/api\/ai\/tasks\/generate/);
});

test('static chat.html implements the final single-file customer chat deliverable', () => {
  const html = read('chat.html');

  assertIncludesAll(html, [
    'SmartFlow AI - Müşteri Chat',
    'Müşteri Chat Simülasyonu',
    '128 numaralı siparişim nerede?',
    '142 numaralı siparişim neden gelmedi?',
    'Organik zeytinyağı var mı?',
    'Kritik stokları listele',
    'Bugünkü durumu özetle',
    "fetch('/api/chat'",
    'intentBadge',
    'toolList',
    'dashboardNote',
    'typing',
  ]);
});

test('static dashboard.html keeps final dashboard, action, and alert contract intact', () => {
  const html = read('dashboard.html');

  assertIncludesAll(html, [
    'Toplam Sipariş',
    'Hazırlanıyor',
    'Kargoda',
    'Teslim Edildi',
    'Gecikmiş',
    'Kritik Stok',
    'Onay Bekliyor',
    "apiFetch('GET','/api/dashboard/summary')",
    "apiFetch('GET','/api/tasks')",
    "apiFetch('GET','/api/orders')",
    "apiFetch('GET','/api/products')",
    "apiFetch('GET','/api/shipments')",
    "apiFetch('POST','/api/tasks/generate'",
    "apiFetch('POST','/api/alerts/send'",
    "subject:'SmartFlow AI — Yönetici Uyarısı'",
    'openMailModal',
    'sendManagerAlert',
    'isPendingApproval',
  ]);
  assert.doesNotMatch(html, /\/api\/ai\/tasks\/generate/);
});

test('task and pending pages handle approval status using the Turkish-insensitive helper', () => {
  const tasks = read('src/pages/TasksPage.jsx');
  const pending = read('src/pages/PendingPage.jsx');
  const badge = read('src/components/Badge.jsx');

  assertIncludesAll(tasks, [
    'toLocaleLowerCase',
    'onay bekliyor',
    'updateTaskStatus',
  ]);
  assertIncludesAll(pending, [
    'toLocaleLowerCase',
    'onay bekliyor',
    'Tümünü Onayla',
  ]);
  assertIncludesAll(badge, [
    "'Onay Bekliyor': 'purple'",
    "'Onay bekliyor': 'purple'",
  ]);
});
