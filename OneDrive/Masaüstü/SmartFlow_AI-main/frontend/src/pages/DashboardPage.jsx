import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Chart as ChartJS, ArcElement, Tooltip, Legend,
} from 'chart.js';
import { Doughnut } from 'react-chartjs-2';
import { useApiData } from '../hooks/useApiData.jsx';
import { useToast, useDashNote, useMailModal, useNavBadge } from '../components/Layout.jsx';
import { StatCard } from '../components/StatCard.jsx';
import { Badge } from '../components/Badge.jsx';
import { PriorityChip } from '../components/PriorityChip.jsx';
import { StockBar } from '../components/StockBar.jsx';
import { generateBriefingResult, updateTaskStatusResult } from '../api/client.js';

ChartJS.register(ArcElement, Tooltip, Legend);

function DashNotes() {
  const { dashNotes, removeDashNote } = useDashNote();
  if (!dashNotes.length) return null;
  return (
    <div className="dash-notes">
      {dashNotes.map(n => (
        <div key={n.id} className="dnote">
          <span>🔔</span>
          <span>{n.msg}</span>
          <button className="dnote-close" type="button" aria-label="Dashboard notunu kapat" onClick={() => removeDashNote(n.id)}>×</button>
        </div>
      ))}
    </div>
  );
}

function DataStatusBanner({ loading, hasError, isPartial, resources, lastUpdated, refresh }) {
  if (loading) return <div className="status-banner info">Veriler yükleniyor...</div>;
  if (!hasError) {
    return (
      <div className="status-banner success">
        Gerçek servis verisi yüklendi
        {lastUpdated && <span>Son güncelleme: {new Date(lastUpdated).toLocaleTimeString('tr')}</span>}
      </div>
    );
  }
  const failed = Object.entries(resources || {})
    .filter(([, status]) => status.error)
    .map(([key]) => key)
    .join(', ');
  return (
    <div className={`status-banner ${isPartial ? 'warn' : 'error'}`}>
      {isPartial ? 'Bazı veriler güncellenemedi' : 'Veriler alınamadı'}{failed ? `: ${failed}` : ''}
      <button className="btn btn-ghost btn-sm" type="button" onClick={refresh}>Tekrar dene</button>
    </div>
  );
}

function TodayFocus({ items }) {
  if (!items.length) {
    return (
      <div className="focus-panel">
        <div className="focus-head">
          <div>
            <div className="stitle">Bugün Önce Yap</div>
            <div className="focus-sub">Kritik operasyon görünmüyor.</div>
          </div>
        </div>
        <div className="empty">✅ Bugün için acil karar kuyruğu temiz.</div>
      </div>
    );
  }

  return (
    <div className="focus-panel">
      <div className="focus-head">
        <div>
          <div className="stitle">Bugün Önce Yap <span className="scnt">{items.length}</span></div>
          <div className="focus-sub">Gecikme, stok ve onay riskine göre sıralandı.</div>
        </div>
      </div>
      <div className="focus-list">
        {items.map(item => (
          <div key={item.id} className={`focus-item ${item.tone}`}>
            <div className="focus-rank">{item.rank}</div>
            <div className="focus-body">
              <div className="focus-title">{item.title}</div>
              <div className="focus-meta">{item.reason}</div>
              <div className="focus-feedforward">{item.feedforward}</div>
            </div>
            <button className="btn btn-ghost btn-sm" type="button" onClick={item.onAction}>
              {item.action}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

const isPendingApproval = (task) => task.status?.toLocaleLowerCase('tr') === 'onay bekliyor';

export default function DashboardPage() {
  const {
    summary, tasks, orders, products, shipments, loading, refresh,
    resources, hasError, isPartial, lastUpdated,
  } = useApiData();
  const showToast = useToast();
  const { pushDashNote } = useDashNote();
  const openMailModal = useMailModal();
  const { setNavBadge } = useNavBadge();
  const navigate = useNavigate();

  const [briefing, setBriefing] = useState(null);
  const [briefLoading, setBriefLoading] = useState(true);
  const [localTasks, setLocalTasks] = useState(tasks);
  const [busyIds, setBusyIds] = useState([]);

  useEffect(() => { setLocalTasks(tasks); }, [tasks]);

  useEffect(() => {
    const late = orders.filter(o => o.cargo_status === 'Gecikmiş').length;
    const crit = products.filter(p => p.stock_count <= p.critical_threshold).length;
    const pend = localTasks.filter(isPendingApproval).length;
    setNavBadge({ late, crit, pend });
  }, [orders, products, localTasks, setNavBadge]);

  useEffect(() => {
    loadBriefing();
  }, []);

  async function loadBriefing(manual = false) {
    setBriefLoading(true);
    const result = await generateBriefingResult();
    setBriefing(result.ok ? result.data : null);
    setBriefLoading(false);
    if (manual) {
      showToast(result.ok ? 'Brifing güncellendi' : 'AI brifing servisine ulaşılamadı; özet fallback veriden gösteriliyor', result.ok ? 'success' : 'warn');
    }
  }

  async function undoTask(task) {
    const res = await updateTaskStatusResult(task.task_id, task.status);
    if (res.ok) {
      setLocalTasks(prev => prev.map(t => t.task_id === task.task_id ? { ...t, status: task.status } : t));
      showToast(`Görev #${task.task_id} geri alındı`, 'info');
    } else {
      showToast(`Görev #${task.task_id} geri alınamadı`, 'error');
    }
  }

  async function changeTaskStatus(taskId, nextStatus, toastType) {
    const task = localTasks.find(x => x.task_id === taskId);
    if (!task || busyIds.includes(taskId)) return;
    setBusyIds(prev => [...prev, taskId]);
    setLocalTasks(prev => prev.map(t => t.task_id === taskId ? { ...t, status: nextStatus } : t));
    const res = await updateTaskStatusResult(taskId, nextStatus);
    setBusyIds(prev => prev.filter(id => id !== taskId));
    if (res.ok) {
      showToast(`Görev #${taskId} ${nextStatus.toLocaleLowerCase('tr')}`, toastType, {
        duration: 5000,
        action: { label: 'Geri al', onClick: () => undoTask(task) },
      });
      pushDashNote(`Görev #${taskId} güncellendi: "${task.description}"`);
    } else {
      setLocalTasks(prev => prev.map(t => t.task_id === taskId ? { ...t, status: task.status } : t));
      showToast(`Görev #${taskId} güncellenemedi. Servis durumunu kontrol edin.`, 'error');
    }
  }

  async function handleApprove(taskId) {
    await changeTaskStatus(taskId, 'Tamamlandı', 'success');
  }

  async function handleReject(taskId) {
    await changeTaskStatus(taskId, 'İptal', 'warn');
  }

  const lateOrders = orders.filter(o => o.cargo_status === 'Gecikmiş');
  const critProds = products.filter(p => p.stock_count <= p.critical_threshold);
  const pendTasks = localTasks.filter(isPendingApproval);
  const pend = pendTasks.length;
  const shipmentByOrder = new Map(shipments.map(s => [s.order_id, s]));

  const focusItems = [
    ...lateOrders
      .sort((a, b) => (b.delay_days || 0) - (a.delay_days || 0))
      .slice(0, 2)
      .map(o => ({
        id: `late-${o.order_id}`,
        tone: 'danger',
        title: `#${o.order_id} gecikmiş sipariş`,
        reason: `${o.customer_name} · ${o.delay_days || shipmentByOrder.get(o.order_id)?.delay_days || 0} gün gecikme`,
        feedforward: 'Müşteri etkisi yüksek; bilgilendirme aksiyonu açılacak.',
        action: 'Not oluştur',
        onAction: () => pushDashNote(`Sipariş #${o.order_id} için müşteri bilgilendirme aksiyonu oluşturuldu.`),
      })),
    ...critProds
      .sort((a, b) => (a.stock_count / a.critical_threshold) - (b.stock_count / b.critical_threshold))
      .slice(0, 2)
      .map(p => ({
        id: `stock-${p.product_id}`,
        tone: 'warn',
        title: `${p.product_name} kritik stok`,
        reason: `${p.product_id} · ${p.stock_count}/${p.critical_threshold} adet`,
        feedforward: 'Tedarikçi mail taslağı açılacak; gerçek gönderim yapılmaz.',
        action: 'Mail taslağı',
        onAction: () => {
          const body = `Sayın Tedarikçi Yetkilisi,\n\n"${p.product_name}" (${p.product_id}) ürünümüzün stoğu kritik seviyeye düşmüştür.\n\nMevcut stok: ${p.stock_count} adet\nKritik eşik: ${p.critical_threshold} adet\n\nEn kısa sürede fiyat ve teslim süresi bilgisini paylaşabilir misiniz?\n\nSaygılarımla,\nSatın Alma - SmartFlow AI`;
          openMailModal(p.product_name, p.supplier_email, `ACİL: ${p.product_name} - Stok Yenileme Talebi`, body);
        },
      })),
    ...pendTasks
      .sort((a, b) => ['Kritik', 'Yüksek', 'Orta', 'Düşük'].indexOf(a.priority) - ['Kritik', 'Yüksek', 'Orta', 'Düşük'].indexOf(b.priority))
      .slice(0, 2)
      .map(t => ({
        id: `task-${t.task_id}`,
        tone: 'info',
        title: `Görev #${t.task_id} onay bekliyor`,
        reason: `${t.task_type} · ${t.priority}`,
        feedforward: 'Onay ekranında etkiyi kontrol ederek tamamlayabilirsiniz.',
        action: 'Onaylara git',
        onAction: () => navigate('/pending'),
      })),
  ].slice(0, 5).map((item, index) => ({ ...item, rank: index + 1 }));

  const typeIc = { Stok: '⚡', Kargo: '🚚', 'Müşteri Bilgilendirme': '📣', Paketleme: '📦' };

  const chartValues = summary
    ? [summary.delivered_orders, summary.in_cargo_orders, summary.preparing_orders, summary.delayed_orders]
    : [0, 0, 0, 0];
  const chartData = {
    labels: ['Teslim', 'Kargoda', 'Hazırlanıyor', 'Gecikmiş'].map((label, index) => `${label} (${chartValues[index]})`),
    datasets: [{
      data: chartValues,
      backgroundColor: ['#22c55e22', '#3b82f622', '#eab30822', '#ef444422'],
      borderColor: ['#22c55e', '#60a5fa', '#eab308', '#f87171'],
      borderWidth: 1.5,
      hoverOffset: 5,
    }],
  };

  const chartOptions = {
    responsive: true,
    cutout: '68%',
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          color: '#94a3b8',
          font: { family: "'IBM Plex Mono',monospace", size: 11 },
          padding: 14, boxWidth: 10, boxHeight: 10,
        },
      },
      tooltip: {
        backgroundColor: '#13161d', borderColor: '#1f2330', borderWidth: 1,
        titleColor: '#e2e8f0', bodyColor: '#94a3b8',
        titleFont: { family: "'IBM Plex Mono',monospace", size: 11 },
        bodyFont: { family: "'IBM Plex Mono',monospace", size: 11 },
      },
    },
  };

  const shipMap = { 'Teslim Edildi': 'green', Dağıtımda: 'blue', 'Kargoya Verildi': 'cyan', Depoda: 'yellow', Gecikmiş: 'red' };

  return (
    <div className="page-content">
      <DataStatusBanner loading={loading} hasError={hasError} isPartial={isPartial} resources={resources} lastUpdated={lastUpdated} refresh={refresh} />
      <DashNotes />
      <TodayFocus items={focusItems} />

      <div className="stat-grid">
        <StatCard icon="📦" value={summary?.total_orders} label="Toplam Sipariş" delta={summary ? `${summary.total_orders} sipariş` : '-'} deltaClass="d-neu" color="#64748b" />
        <StatCard icon="🔧" value={summary?.preparing_orders} label="Hazırlanıyor" delta={summary ? `${summary.preparing_orders} aktif` : '-'} deltaClass="d-neu" color="#eab308" />
        <StatCard icon="🚚" value={summary?.in_cargo_orders} label="Kargoda" delta={summary ? `${summary.in_cargo_orders} yolda` : '-'} deltaClass="d-neu" color="#22d3ee" />
        <StatCard icon="✅" value={summary?.delivered_orders} label="Teslim Edildi" delta={summary ? `+${Math.max(0, summary.delivered_orders - 8)} dün` : '-'} deltaClass="d-up" color="#22c55e" />
        <StatCard icon="⏰" value={summary?.delayed_orders} label="Gecikmiş" delta={summary?.delayed_orders > 0 ? 'acil' : 'normal'} deltaClass="d-down" color="#f87171" />
        <StatCard icon="⚡" value={summary?.critical_stock_products} label="Kritik Stok" delta={summary?.critical_stock_products > 0 ? 'eşik altı' : 'normal'} deltaClass="d-warn" color="#fb923c" />
        <StatCard icon="⏳" value={pend} label="Onay Bekliyor" delta={pend > 0 ? 'onay gerek' : 'temiz'} deltaClass="d-pur" color="#c084fc" />
      </div>

      <div className="ai-panel fi">
        <div className="aihdr">
          <div className="ailbl">
            🤖 AI Günlük Brifing
            <span className="chip chip-blue">Gemini</span>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={() => loadBriefing(true)} disabled={briefLoading}>
            {briefLoading ? '...' : '↻ Yenile'}
          </button>
        </div>
        {briefLoading ? (
          <div className="brief-body loading">
            <div className="spinner" />
            <span>AI brifingi hazırlanıyor...</span>
          </div>
        ) : (
          <div className="brief-body">
            {briefing?.briefing
              ? briefing.briefing.split('\n').map((l, i) => <span key={i}>{l}<br /></span>)
              : summary?.ai_summary || 'Brifing yüklenemedi.'}
          </div>
        )}
        <details className="diagnostics">
          <summary>Teknik çağrı detayları</summary>
          <div className="bftr">
            <span className="bftr-meta">Son güncelleme: {new Date().toLocaleTimeString('tr')} · POST /api/tasks/generate</span>
            <div className="tool-tags">
              {['get_order_status', 'check_stock_alerts', 'generate_daily_briefing'].map(t => (
                <span key={t} className="chip chip-purple">{t}</span>
              ))}
            </div>
          </div>
        </details>
      </div>

      <div className="two-col">
        <div>
          <div className="shdr">
            <div className="stitle">⏰ Gecikmiş Siparişler <span className="scnt">{lateOrders.length}</span></div>
          </div>
          <div className="alert-panel">
            {lateOrders.length === 0
              ? <div className="empty">✅ Gecikmiş sipariş yok</div>
              : lateOrders.map(o => {
                  const shipment = shipmentByOrder.get(o.order_id);
                  return (
                    <div key={o.order_id} className="ai-row">
                      <span className="ai-ic">🔴</span>
                      <div className="ai-bd">
                        <div className="ai-t">#{o.order_id} - {o.customer_name}</div>
                        <div className="ai-m">Adet: {o.quantity} · ETA: {shipment?.estimated_delivery || o.estimated_delivery} · <span style={{ color: 'var(--red)' }}>{shipment?.delay_days || o.delay_days || 0} gün gecikmiş</span></div>
                      </div>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                        <Badge label="Gecikmiş" />
                        <button className="btn btn-ghost btn-sm" onClick={() => pushDashNote(`Sipariş #${o.order_id} - ${o.customer_name} için bilgilendirme aksiyonu oluşturuldu`)}>
                          Bilgilendirme notu
                        </button>
                      </div>
                    </div>
                  );
                })}
          </div>
        </div>
        <div>
          <div className="shdr">
            <div className="stitle">⚡ Kritik Stok Uyarısı <span className="scnt">{critProds.length}</span></div>
          </div>
          <div className="alert-panel">
            {critProds.length === 0
              ? <div className="empty">✅ Kritik stok yok</div>
              : critProds.map(p => (
                  <div key={p.product_id} className="ai-row">
                    <span className="ai-ic">⚡</span>
                    <div className="ai-bd">
                      <div className="ai-t">{p.product_name}</div>
                      <div className="ai-m">{p.product_id} · Stok: <span style={{ color: 'var(--red)' }}>{p.stock_count}</span> / Min: {p.critical_threshold}</div>
                      <StockBar stock={p.stock_count} threshold={p.critical_threshold} />
                    </div>
                    <button
                      className="btn btn-ghost btn-sm"
                      aria-label={`${p.product_name} için mail taslağı aç`}
                      onClick={() => {
                        const body = `Sayın Tedarikçi Yetkilisi,\n\n"${p.product_name}" (${p.product_id}) ürünümüzün stoğu kritik seviyeye düşmüştür.\n\nMevcut stok: ${p.stock_count} adet\nKritik eşik: ${p.critical_threshold} adet\n\nEn kısa sürede fiyat ve teslim süresi bilgisini paylaşabilir misiniz?\n\nSaygılarımla,\nSatın Alma - SmartFlow AI`;
                        openMailModal(p.product_name, p.supplier_email, `ACİL: ${p.product_name} - Stok Yenileme Talebi`, body);
                      }}
                    >
                      ✉️ Mail taslağı
                    </button>
                  </div>
                ))}
          </div>
        </div>
      </div>

      <div>
        <div className="shdr">
          <div className="stitle">⏳ Onay Bekleyen Aksiyonlar <span className="scnt">{pend}</span></div>
        </div>
        <div className="action-panel">
          {pendTasks.length === 0
            ? <div className="empty">✅ Onay bekleyen aksiyon yok</div>
            : pendTasks.map(t => (
                <div key={t.task_id} className="act">
                  <span style={{ fontSize: 18 }}>{typeIc[t.task_type] || '📋'}</span>
                  <div className="act-l">
                    <div className="act-t">{t.description}</div>
                    <div className="act-s">{t.task_type} · <Badge label="Onay Bekliyor" /></div>
                  </div>
                  <div className="act-r">
                    <PriorityChip priority={t.priority} />
                    <button className="btn btn-ghost btn-sm" aria-label={`Görev ${t.task_id} reddet`} disabled={busyIds.includes(t.task_id)} onClick={() => handleReject(t.task_id)}>✕ Reddet</button>
                    <button className="btn btn-purple btn-sm" aria-label={`Görev ${t.task_id} onayla`} disabled={busyIds.includes(t.task_id)} onClick={() => handleApprove(t.task_id)}>✓ Onayla</button>
                  </div>
                </div>
              ))}
        </div>
      </div>

      <div className="secondary-section">
        <div className="two-col">
          <div>
            <div className="shdr">
              <div className="stitle">🚚 Son Kargolar</div>
            </div>
            <div className="table-panel">
              <table>
                <thead>
                  <tr>
                    <th>Takip No</th><th>Sipariş</th><th>Firma</th><th>Durum</th><th>ETA</th>
                  </tr>
                </thead>
                <tbody>
                  {shipments.slice(0, 5).map(s => (
                    <tr key={s.shipment_id}>
                      <td className="cm">{s.tracking_number}</td>
                      <td className="cb">#{s.order_id}</td>
                      <td className="cm">{s.carrier}</td>
                      <td><Badge label={s.actual_status} color={shipMap[s.actual_status] || 'gray'} /></td>
                      <td className="cm">{s.estimated_delivery}</td>
                    </tr>
                  ))}
                  {shipments.length === 0 && <tr><td colSpan={5} className="empty">{resources?.shipments?.error ? 'Kargo verisi alınamadı.' : 'Kargo kaydı yok.'}</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
          <div>
            <div className="shdr"><div className="stitle">📊 Sipariş Dağılımı</div></div>
            <div className="alert-panel" style={{ padding: 16 }}>
              <Doughnut data={chartData} options={chartOptions} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
