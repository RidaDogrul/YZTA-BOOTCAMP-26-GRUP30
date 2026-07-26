/**
 * chart.js — Chart.js 4 entegrasyonu
 * CSS custom property'lerle uyumlu renk paleti ve config.
 */

const PALETTE = [
  "#6366f1","#22c55e","#f59e0b","#ef4444",
  "#06b6d4","#a855f7","#f97316","#14b8a6",
  "#e879f9","#84cc16",
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
        boxWidth: 10, padding: 14,
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
      grid:  { color: "rgba(255,255,255,.04)" },
      border: { color: "rgba(255,255,255,.07)" },
    },
    y: {
      ticks: { color: "#475569", font: { size: 11 } },
      grid:  { color: "rgba(255,255,255,.04)" },
      border: { color: "rgba(255,255,255,.07)" },
    },
  },
};

/* Active instances — destroy before re-render */
const _instances = new Map();

/* ── Type detection ───────────────────────────────────────── */
function _detectType(data) {
  if (!Array.isArray(data) || !data.length) return null;
  const keys    = Object.keys(data[0]);
  const numKeys = keys.filter(k => {
    const v = data[0][k];
    return typeof v === "number" || (v !== null && v !== "" && !isNaN(Number(v)));
  });
  const labelKey = keys.find(k => !numKeys.includes(k)) || keys[0];
  if (!numKeys.length) return null;

  const lk = labelKey.toLowerCase();
  const isTime = ["date","month","period","year","week","gun","ay","tarih","hafta"]
    .some(w => lk.includes(w));

  const isShare = numKeys.some(k => {
    const kl = k.toLowerCase();
    return ["share","percent","oran","yuzde","pay","ratio"].some(w => kl.includes(w));
  });

  return { labelKey, numKeys, isTime, isShare };
}

/* ── Build Chart.js config ────────────────────────────────── */
function buildChartConfig(data) {
  const info = _detectType(data);
  if (!info) return null;
  const { labelKey, numKeys, isTime, isShare } = info;
  const labels = data.map(r => String(r[labelKey]));

  /* Line — time series */
  if (isTime) {
    const datasets = numKeys.map((k, i) => ({
      label: _human(k),
      data:  data.map(r => Number(r[k])),
      borderColor:     PALETTE[i % PALETTE.length],
      backgroundColor: PALETTE[i % PALETTE.length] + "22",
      fill:       numKeys.length === 1,
      tension:    0.38,
      pointRadius: data.length < 25 ? 4 : 2,
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
          data:            data.map(r => Number(r[numKeys[0]])),
          backgroundColor: PALETTE.slice(0, data.length),
          borderColor:     "#07080f",
          borderWidth:     3,
          hoverOffset:     10,
        }],
      },
      options: {
        ...BASE_OPTS,
        cutout: "60%",
        scales: undefined,
        plugins: {
          ...BASE_OPTS.plugins,
          legend: { ...BASE_OPTS.plugins.legend, position: "right", display: true },
        },
      },
    };
  }

  /* Bar — default */
  const datasets = numKeys.map((k, i) => ({
    label:           _human(k),
    data:            data.map(r => Number(r[k])),
    backgroundColor: PALETTE[i % PALETTE.length] + "cc",
    borderColor:     PALETTE[i % PALETTE.length],
    borderWidth:     1,
    borderRadius:    5,
    borderSkipped:   false,
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

/* ── Public render function ───────────────────────────────── */
function renderChart(container, chartData, chartId) {
  const config = buildChartConfig(chartData);
  if (!config) {
    container.innerHTML =
      '<p style="color:#475569;font-size:12px;padding:8px 0">Grafik oluşturulamadı.</p>';
    return;
  }

  if (_instances.has(chartId)) {
    _instances.get(chartId).destroy();
    _instances.delete(chartId);
  }

  const canvas = document.createElement("canvas");
  canvas.id = `c-${chartId}`;
  canvas.style.maxHeight = "260px";
  container.appendChild(canvas);

  _instances.set(chartId, new Chart(canvas, config));
}

/* ── Helpers ──────────────────────────────────────────────── */
function _human(key) {
  return key
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, c => c.toUpperCase());
}
