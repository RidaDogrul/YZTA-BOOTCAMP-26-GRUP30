import React, { useState, useEffect } from 'react';
import { useApiData } from '../hooks/useApiData.jsx';
import { Badge } from '../components/Badge.jsx';
import { PriorityChip } from '../components/PriorityChip.jsx';
import { useToast } from '../components/Layout.jsx';
import { updateTaskStatusResult } from '../api/client.js';

const TYPE_CLS = {
  'Müşteri Bilgilendirme': 'red',
  Paketleme: 'cyan',
  Stok: 'orange',
  Kargo: 'blue',
};
const isPendingApproval = (task) => task.status?.toLocaleLowerCase('tr') === 'onay bekliyor';
const norm = value => String(value ?? '').toLocaleLowerCase('tr');
const priorityRank = { Kritik: 0, Yüksek: 1, Orta: 2, Düşük: 3 };

export default function TasksPage() {
  const { tasks, resources, loading } = useApiData();
  const showToast = useToast();
  const [localTasks, setLocalTasks] = useState(tasks);
  const [filterStatus, setFilterStatus] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterPri, setFilterPri] = useState('');
  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState('priority');
  const [sortDir, setSortDir] = useState('asc');
  const [busyIds, setBusyIds] = useState([]);

  useEffect(() => { setLocalTasks(tasks); }, [tasks]);

  const filters = [
    filterStatus && `Durum: ${filterStatus}`,
    filterType && `Tür: ${filterType}`,
    filterPri && `Öncelik: ${filterPri}`,
    query && `Arama: ${query}`,
  ].filter(Boolean);

  const rows = localTasks
    .filter(t =>
      (!filterStatus || t.status?.toLocaleLowerCase('tr') === filterStatus.toLocaleLowerCase('tr')) &&
      (!filterType || t.task_type === filterType) &&
      (!filterPri || t.priority === filterPri) &&
      (!query || [t.task_id, t.description, t.related_order_id, t.related_product_id].some(v => norm(v).includes(norm(query))))
    )
    .sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1;
      if (sortKey === 'priority') return ((priorityRank[a.priority] ?? 9) - (priorityRank[b.priority] ?? 9)) * dir;
      const av = a[sortKey] ?? '';
      const bv = b[sortKey] ?? '';
      if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir;
      return String(av).localeCompare(String(bv), 'tr') * dir;
    });

  function toggleSort(key) {
    if (sortKey === key) setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
    else {
      setSortKey(key);
      setSortDir('asc');
    }
  }

  function clearFilters() {
    setFilterStatus('');
    setFilterType('');
    setFilterPri('');
    setQuery('');
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

  async function handleApprove(taskId) {
    const task = localTasks.find(x => x.task_id === taskId);
    if (!task || busyIds.includes(taskId)) return;
    setBusyIds(prev => [...prev, taskId]);
    setLocalTasks(prev => prev.map(t => t.task_id === taskId ? { ...t, status: 'Tamamlandı' } : t));
    const res = await updateTaskStatusResult(taskId, 'Tamamlandı');
    setBusyIds(prev => prev.filter(id => id !== taskId));
    if (res.ok) {
      showToast(`Görev #${taskId} onaylandı`, 'success', {
        duration: 5000,
        action: { label: 'Geri al', onClick: () => undoTask(task) },
      });
    } else {
      setLocalTasks(prev => prev.map(t => t.task_id === taskId ? { ...t, status: task.status } : t));
      showToast(`Görev #${taskId} güncellenemedi. Servis durumunu kontrol edin.`, 'error');
    }
  }

  const emptyMessage = loading
    ? 'Yükleniyor...'
    : resources?.tasks?.error
      ? 'Görev verisi alınamadı. Tekrar deneyin.'
      : filters.length
        ? 'Filtrelerle eşleşen görev yok.'
        : 'Görev kaydı yok.';

  return (
    <div className="page-content">
      <div className="shdr">
        <div className="stitle">📋 Görevler <span className="scnt">{rows.length}</span></div>
        <div className="filter-bar">
          <input className="search-input" value={query} onChange={e => setQuery(e.target.value)} placeholder="Görev, ID veya ilişki ara" />
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
            <option value="">Tüm Durumlar</option>
            <option value="Bekliyor">Bekliyor</option>
            <option value="Devam Ediyor">Devam Ediyor</option>
            <option value="Onay bekliyor">Onay bekliyor</option>
            <option value="Tamamlandı">Tamamlandı</option>
          </select>
          <select value={filterType} onChange={e => setFilterType(e.target.value)}>
            <option value="">Tüm Türler</option>
            <option value="Müşteri Bilgilendirme">Müşteri Bilgilendirme</option>
            <option value="Paketleme">Paketleme</option>
            <option value="Stok">Stok</option>
            <option value="Kargo">Kargo</option>
          </select>
          <select value={filterPri} onChange={e => setFilterPri(e.target.value)}>
            <option value="">Tüm Öncelikler</option>
            <option value="Kritik">Kritik</option>
            <option value="Yüksek">Yüksek</option>
            <option value="Orta">Orta</option>
            <option value="Düşük">Düşük</option>
          </select>
          {filters.length > 0 && <button className="btn btn-ghost btn-sm" type="button" onClick={clearFilters}>Filtreleri temizle</button>}
        </div>
      </div>
      <div className="filter-summary">{rows.length} sonuç, {filters.length} filtre aktif</div>
      {filters.length > 0 && (
        <div className="filter-chips">
          {filters.map(f => <span key={f} className="filter-chip">{f}</span>)}
        </div>
      )}
      <div className="table-panel">
        <table>
          <thead>
            <tr>
              <th><button className="th-sort" type="button" onClick={() => toggleSort('task_id')}>ID</button></th><th>Görev</th><th>Tür</th><th>İlişki</th>
              <th><button className="th-sort" type="button" onClick={() => toggleSort('priority')}>Öncelik</button></th><th>Durum</th><th>İşlem</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0
              ? <tr><td colSpan={7} className="empty">{emptyMessage}</td></tr>
              : rows.map(t => (
                  <tr key={t.task_id}>
                    <td className="cm">#{t.task_id}</td>
                    <td className="cb">{t.description}</td>
                    <td><Badge label={t.task_type} color={TYPE_CLS[t.task_type] || 'gray'} /></td>
                    <td className="cm">{t.related_order_id ? `#Sip-${t.related_order_id}` : t.related_product_id || '-'}</td>
                    <td><PriorityChip priority={t.priority} /></td>
                    <td><Badge label={t.status} /></td>
                    <td>
                      {isPendingApproval(t)
                        ? <button className="btn btn-purple btn-sm" aria-label={`Görev ${t.task_id} onayla`} disabled={busyIds.includes(t.task_id)} onClick={() => handleApprove(t.task_id)}>✓ Onayla</button>
                        : <button className="btn btn-ghost btn-sm" aria-label={`Görev ${t.task_id} durumunu göster`} onClick={() => showToast(`Görev #${t.task_id} - ${t.status}`, 'info')}>Detay</button>}
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
