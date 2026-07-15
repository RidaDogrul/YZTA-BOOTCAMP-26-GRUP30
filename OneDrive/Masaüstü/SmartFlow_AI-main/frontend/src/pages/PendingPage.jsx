import React, { useState, useEffect } from 'react';
import { useApiData } from '../hooks/useApiData.jsx';
import { Badge } from '../components/Badge.jsx';
import { PriorityChip } from '../components/PriorityChip.jsx';
import { useToast, useDashNote } from '../components/Layout.jsx';
import { updateTaskStatusResult } from '../api/client.js';

const TYPE_IC = { Stok: '⚡', Kargo: '🚚', 'Müşteri Bilgilendirme': '📣', Paketleme: '📦' };
const isPendingApproval = (task) => task.status?.toLocaleLowerCase('tr') === 'onay bekliyor';

export default function PendingPage() {
  const { tasks } = useApiData();
  const showToast = useToast();
  const { pushDashNote } = useDashNote();
  const [localTasks, setLocalTasks] = useState(tasks);
  const [busyIds, setBusyIds] = useState([]);

  useEffect(() => { setLocalTasks(tasks); }, [tasks]);

  const pending = localTasks.filter(isPendingApproval);

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

  async function handleApproveAll() {
    if (pending.length === 0) return;
    const preview = pending.slice(0, 3).map(t => `#${t.task_id} ${t.description}`).join('\n');
    const confirmed = window.confirm(
      `${pending.length} bekleyen aksiyon tamamlandı yapılacak.\n\nEtkilenecek ilk kayıtlar:\n${preview}\n\nDevam edilsin mi?`
    );
    if (!confirmed) return;
    const results = await Promise.all(pending.map(t => updateTaskStatusResult(t.task_id, 'Tamamlandı')));
    const okIds = pending.filter((_, index) => results[index].ok).map(t => t.task_id);
    if (okIds.length > 0) {
      setLocalTasks(prev => prev.map(t => okIds.includes(t.task_id) ? { ...t, status: 'Tamamlandı' } : t));
    }
    if (okIds.length === pending.length) {
      showToast(`${okIds.length} aksiyon onaylandı`, 'success');
      pushDashNote(`${okIds.length} bekleyen aksiyon onaylandı.`);
    } else {
      showToast(`${okIds.length}/${pending.length} aksiyon onaylandı. Başarısız kayıtlar için tekrar deneyin.`, 'warn');
    }
  }

  return (
    <div className="page-content">
      <div className="shdr">
        <div className="stitle">⏳ Onay Bekleyen Aksiyonlar <span className="scnt">{pending.length}</span></div>
        <button className="btn btn-primary btn-sm" onClick={handleApproveAll} disabled={pending.length === 0}>
          ✅ Tümünü Onayla
        </button>
      </div>
      <div className="action-panel">
        {pending.length === 0
          ? <div className="empty">✅ Onay bekleyen aksiyon yok</div>
          : pending.map(t => (
              <div key={t.task_id} className="act">
                <span style={{ fontSize: 18 }}>{TYPE_IC[t.task_type] || '📋'}</span>
                <div className="act-l">
                  <div className="act-t">{t.description}</div>
                  <div className="act-s">{t.task_type} · <Badge label="Onay Bekliyor" /></div>
                </div>
                <div className="act-r">
                  <PriorityChip priority={t.priority} />
                  <button
                    className="btn btn-ghost btn-sm"
                    aria-label={`Görev ${t.task_id} reddet`}
                    disabled={busyIds.includes(t.task_id)}
                    onClick={() => handleReject(t.task_id)}
                  >
                    ✕ Reddet
                  </button>
                  <button
                    className="btn btn-purple btn-sm"
                    aria-label={`Görev ${t.task_id} onayla`}
                    disabled={busyIds.includes(t.task_id)}
                    onClick={() => handleApprove(t.task_id)}
                  >
                    ✓ Onayla
                  </button>
                </div>
              </div>
            ))}
      </div>
    </div>
  );
}
