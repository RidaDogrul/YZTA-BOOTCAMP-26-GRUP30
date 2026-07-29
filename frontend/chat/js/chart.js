/**
 * chart.js — Chart.js 4 integration for Chat API chart_data.
 *
 * Sprint 3 - S3-H4 scope:
 * - Render API `chart_data` dynamically with Chart.js.
 * - Detect line/bar/doughnut chart types from the payload shape.
 * - Normalize unsafe or oversized chart payloads before rendering.
 * - Fail gracefully when chart data is empty or unsupported.
 */

const PALETTE = [
  "#6366f1", "#22c55e", "#f59e0b", "#ef4444",
  "#06b6d4", "#a855f7", "#f97316", "#14b8a6",
  "#e879f9", "#84cc16",
];

const MAX_CHART_POINTS = 120;

const TIME_KEYS = [
  "date", "datetime", "timestamp", "month", "period", "year", "week",
  "gun", "ay", "tarih", "hafta", "ds",
];

const SHARE_KEYS = [
  "share", "percent", "percentage", "oran", "yuzde", "pay", "ratio",
];

const BASE_OPTS = {
  responsive: true,
  maintainAspectRatio: true,
  animation: { duration: 420, easing: "easeOutQuart" },
  plugins: {
    legend: {
      labels: {
        color: "#94a3b8",
        font: { family: "'Inter', system-ui, sans-serif", size: 11 },
        boxWidth: 10,
        padding: 14,
      },
    },
    tooltip: {
      backgroundColor: "#0d0f1a",
      borderColor: "rgba(255,255,255,.08)",
      borderWidth: 1,
      titleColor: "#f1f5f9",
      bodyColor: "#94a3b8",
      padding: 10,
      cornerRadius: 8,
    },
  },
  scales: {
    x: {
      ticks: { color: "#475569", font: { size: 11 } },
      grid: { color: "rgba(255,255,255,.04)" },
      border: { color: "rgba(255,255,255,.07)" },
    },
    y: {
      ticks: { color: "#475569", font: { size: 11 } },
      grid: { color: "rgba(255,255,255,.04)" },
      border: { color: "rgba(255,255,255,.07)" },
    },
  },
};

/* Active instances — destroy before re-render */
const _instances = new Map();

/* ── Data normalization ───────────────────────────────────────────── */

function normalizeChartData(data) {
  if (!Array.isArray(data)) return [];

  return data
    .filter(row => row && typeof row === "object" && !Array.isArray(row))
    .slice(0, MAX_CHART_POINTS)
    .map(row => ({ ...row }));
}

function _isNumericValue(value) {
  return typeof value === "number" || (
    value !== null &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function _collectKeys(rows) {
  return [...new Set(rows.flatMap(row => Object.keys(row)))];
}

function _toNumber(value) {
  return _isNumericValue(value) ? Number(value) : 0;
}

function _colorAt(index) {
  return PALETTE[index % PALETTE.length];
}

function _detectType(data) {
  const rows = normalizeChartData(data);
  if (!rows.length) return null;

  const keys = _collectKeys(rows);
  if (!keys.length) return null;

  const numKeys = keys.filter(key =>
    rows.some(row => _isNumericValue(row[key]))
  );

  if (!numKeys.length) return null;

  const labelKey =
    keys.find(key => TIME_KEYS.some(word => key.toLowerCase().includes(word))) ||
    keys.find(key => !numKeys.includes(key)) ||
    keys[0];

  const lk = labelKey.toLowerCase();
  const isTime = TIME_KEYS.some(word => lk.includes(word));

  const isShare = numKeys.some(key => {
    const kl = key.toLowerCase();
    return SHARE_KEYS.some(word => kl.includes(word));
  });

  return { rows, labelKey, numKeys, isTime, isShare };
}

/* ── Build Chart.js config ────────────────────────────────────────── */

function buildChartConfig(data) {
  const info = _detectType(data);
  if (!info) return null;

  const { rows, labelKey, numKeys, isTime, isShare } = info;
  const labels = rows.map(row => String(row[labelKey] ?? ""));

  /* Line — time series */
  if (isTime) {
    const datasets = numKeys.map((key, index) => ({
      label: _human(key),
      data: rows.map(row => _toNumber(row[key])),
      borderColor: _colorAt(index),
      backgroundColor: _colorAt(index) + "22",
      fill: numKeys.length === 1,
      tension: 0.38,
      pointRadius: rows.length < 25 ? 4 : 2,
      pointHoverRadius: 6,
      borderWidth: 2,
    }));

    return {
      type: "line",
      data: { labels, datasets },
      options: {
        ...BASE_OPTS,
        plugins: {
          ...BASE_OPTS.plugins,
          legend: { ...BASE_OPTS.plugins.legend, display: numKeys.length > 1 },
        },
      },
    };
  }

  /* Doughnut — share/percent */
  if (isShare && numKeys.length === 1) {
    return {
      type: "doughnut",
      data: {
        labels,
        datasets: [{
          data: rows.map(row => _toNumber(row[numKeys[0]])),
          backgroundColor: rows.map((_, index) => _colorAt(index)),
          borderColor: "#07080f",
          borderWidth: 3,
          hoverOffset: 10,
        }],
      },
      options: {
        ...BASE_OPTS,
        cutout: "60%",
        scales: undefined,
        plugins: {
          ...BASE_OPTS.plugins,
          legend: {
            ...BASE_OPTS.plugins.legend,
            position: "right",
            display: true,
          },
        },
      },
    };
  }

  /* Bar — default categorical comparison */
  const datasets = numKeys.map((key, index) => ({
    label: _human(key),
    data: rows.map(row => _toNumber(row[key])),
    backgroundColor: _colorAt(index) + "cc",
    borderColor: _colorAt(index),
    borderWidth: 1,
    borderRadius: 5,
    borderSkipped: false,
  }));

  return {
    type: "bar",
    data: { labels, datasets },
    options: {
      ...BASE_OPTS,
      plugins: {
        ...BASE_OPTS.plugins,
        legend: { ...BASE_OPTS.plugins.legend, display: numKeys.length > 1 },
      },
    },
  };
}

/* ── Public render function ───────────────────────────────────────── */

function renderChart(container, chartData, chartId) {
  if (!container) return;

  const config = buildChartConfig(chartData);
  if (!config) {
    container.innerHTML =
      '<p style="color:#475569;font-size:12px;padding:8px 0">Grafik oluşturulamadı. chart_data formatı desteklenmiyor.</p>';
    return;
  }

  if (_instances.has(chartId)) {
    _instances.get(chartId).destroy();
    _instances.delete(chartId);
  }

  container.innerHTML = "";

  const canvas = document.createElement("canvas");
  canvas.id = `c-${chartId}`;
  canvas.style.maxHeight = "260px";
  container.appendChild(canvas);

  _instances.set(chartId, new Chart(canvas, config));
}

/* ── Helpers ──────────────────────────────────────────────────────── */

function _human(key) {
  return String(key)
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, char => char.toUpperCase());
}

/* Expose helpers for manual debugging and lightweight frontend checks. */
if (typeof window !== "undefined") {
  window.DataCleanroomCharts = {
    normalizeChartData,
    buildChartConfig,
    renderChart,
  };
}
