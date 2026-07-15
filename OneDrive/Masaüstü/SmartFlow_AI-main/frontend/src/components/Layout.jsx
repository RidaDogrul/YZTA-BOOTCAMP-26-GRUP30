import React, { useState, useEffect, createContext, useContext, useCallback } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { sendAlertResult } from '../api/client.js';

export const ToastContext = createContext(null);

export function useToast() {
  return useContext(ToastContext);
}

export const DashNoteContext = createContext(null);

export function useDashNote() {
  return useContext(DashNoteContext);
}

export const MailModalContext = createContext(null);

export function useMailModal() {
  return useContext(MailModalContext);
}

export const NavBadgeContext = createContext({ late: 0, crit: 0, pend: 0 });

export function useNavBadge() {
  return useContext(NavBadgeContext);
}

const TOAST_PREFIX = {
  success: 'Başarılı:',
  warn: 'Uyarı:',
  error: 'Hata:',
  info: 'Bilgi:',
};

function prefixedMessage(msg, type) {
  const prefix = TOAST_PREFIX[type] || TOAST_PREFIX.info;
  return msg.startsWith(prefix) ? msg : `${prefix} ${msg}`;
}

function Clock() {
  const [t, setT] = useState(new Date().toLocaleTimeString('tr'));
  useEffect(() => {
    const id = setInterval(() => setT(new Date().toLocaleTimeString('tr')), 1000);
    return () => clearInterval(id);
  }, []);
  return <span className="clock">{t}</span>;
}

function ToastHub({ toasts, onDismiss }) {
  return (
    <div className="toast-wrap" role="status" aria-live="polite" aria-relevant="additions text">
      {toasts.map(t => (
        <div key={t.id} className={`toast ${t.type}`} role={t.type === 'error' ? 'alert' : 'status'}>
          <span>{prefixedMessage(t.msg, t.type)}</span>
          {t.action && (
            <button
              className="toast-action"
              type="button"
              onClick={() => {
                t.action.onClick();
                onDismiss(t.id);
              }}
            >
              {t.action.label}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

function MailModalEl({ state, onClose, onSend }) {
  const [to, setTo] = useState('');
  const [cc, setCc] = useState('satin.alma@smartflow.com');
  const [subj, setSubj] = useState('');
  const [body, setBody] = useState('');
  const [dirty, setDirty] = useState(false);
  const [errors, setErrors] = useState({});

  function requestClose() {
    if (dirty && !window.confirm('Taslakta kaydedilmemiş değişiklik var. Kapatılsın mı?')) return;
    onClose();
  }

  useEffect(() => {
    if (!state) return;
    setTo(state.to || '');
    setCc(state.cc || 'satin.alma@smartflow.com');
    setSubj(state.subject || 'ACİL: Kritik Stok Uyarısı - Acil Temin Talebi');
    setBody(state.body || '');
    setDirty(false);
    setErrors({});
  }, [state]);

  useEffect(() => {
    if (!state) return undefined;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') requestClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  });

  if (!state) return null;

  function validateDraft() {
    const nextErrors = {};
    const emailLike = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!to.trim()) nextErrors.to = 'Alıcı e-postası zorunlu.';
    else if (!emailLike.test(to.trim())) nextErrors.to = 'Geçerli bir e-posta girin.';
    if (cc.trim() && !emailLike.test(cc.trim())) nextErrors.cc = 'CC için geçerli bir e-posta girin.';
    if (!subj.trim()) nextErrors.subj = 'Konu zorunlu.';
    if (!body.trim()) nextErrors.body = 'Mesaj gövdesi zorunlu.';
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  function handleSubmit(action) {
    if (!validateDraft()) return;
    onSend({
      to: to.trim(),
      cc: cc.trim(),
      subject: subj.trim(),
      body,
      productName: state.productName,
    }, action);
  }

  return (
    <div className="overlay" onClick={e => { if (e.target === e.currentTarget) requestClose(); }}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="supplier-mail-title">
        <div className="mhdr">
          <div className="mtitle" id="supplier-mail-title">
            ✉️ Tedarikçi Mail Taslağı{' '}
            <span className="chip chip-purple" style={{ marginLeft: 6 }}>draft_supplier_email</span>
          </div>
          <button className="mclose" type="button" aria-label="Mail taslağını kapat" onClick={requestClose}>×</button>
        </div>
        <div className="mbody">
          <div className="field">
            <label>Ürün / Konu</label>
            <div style={{ fontSize: 12, color: 'var(--muted)', fontFamily: 'var(--mono)', marginBottom: 4 }}>
              {state.productName || '-'}
            </div>
          </div>
          <div className="field">
            <label>Alıcı</label>
            <input
              value={to}
              onChange={e => { setTo(e.target.value); setDirty(true); }}
              type="email"
              required
              aria-invalid={Boolean(errors.to)}
              aria-describedby={errors.to ? 'mail-to-error' : undefined}
            />
            {errors.to && <div className="field-error" id="mail-to-error">{errors.to}</div>}
          </div>
          <div className="field">
            <label>CC</label>
            <input
              value={cc}
              onChange={e => { setCc(e.target.value); setDirty(true); }}
              type="email"
              aria-invalid={Boolean(errors.cc)}
              aria-describedby={errors.cc ? 'mail-cc-error' : undefined}
            />
            {errors.cc && <div className="field-error" id="mail-cc-error">{errors.cc}</div>}
          </div>
          <div className="field">
            <label>Konu</label>
            <input
              value={subj}
              onChange={e => { setSubj(e.target.value); setDirty(true); }}
              required
              aria-invalid={Boolean(errors.subj)}
              aria-describedby={errors.subj ? 'mail-subj-error' : undefined}
            />
            {errors.subj && <div className="field-error" id="mail-subj-error">{errors.subj}</div>}
          </div>
          <div className="field">
            <label>Mesaj</label>
            <textarea
              value={body}
              onChange={e => { setBody(e.target.value); setDirty(true); }}
              required
              aria-invalid={Boolean(errors.body)}
              aria-describedby={errors.body ? 'mail-body-error' : undefined}
            />
            {errors.body && <div className="field-error" id="mail-body-error">{errors.body}</div>}
          </div>
        </div>
        <div className="mftr">
          <button className="btn btn-ghost" type="button" onClick={requestClose}>İptal</button>
          <button className="btn btn-ghost" type="button" onClick={() => handleSubmit('copy')}>📋 Kopyala</button>
          <button className="btn btn-primary" type="button" onClick={() => handleSubmit('send')}>Taslağı Hazırla</button>
        </div>
      </div>
    </div>
  );
}

export default function Layout() {
  const [toasts, setToasts] = useState([]);
  const [dashNotes, setDashNotes] = useState([]);
  const [mailState, setMailState] = useState(null);
  const [navBadge, setNavBadge] = useState({ late: 0, crit: 0, pend: 0 });

  const dismissToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const showToast = useCallback((msg, type = 'info', options = {}) => {
    const id = Date.now() + Math.random();
    setToasts(prev => [...prev, { id, msg, type, action: options.action }]);
    if (!options.persist) setTimeout(() => dismissToast(id), options.duration || 3500);
    return id;
  }, [dismissToast]);

  const pushDashNote = useCallback((msg) => {
    const id = Date.now() + Math.random();
    setDashNotes(prev => [{ id, msg }, ...prev]);
  }, []);

  const openMailModal = useCallback((productName, to, subject, body, cc) => {
    setMailState({ productName, to, subject, body, cc });
  }, []);

  const closeMailModal = useCallback(() => setMailState(null), []);

  const formatDraft = useCallback((draft) => (
    `To: ${draft.to}\nCC: ${draft.cc || '-'}\nSubject: ${draft.subject}\n\n${draft.body}`
  ), []);

  const handleMailSend = useCallback(async (draft, action) => {
    const draftText = formatDraft(draft);
    if (action === 'copy') {
      try {
        await navigator.clipboard.writeText(draftText);
        closeMailModal();
        showToast('Taslak panoya kopyalandı', 'success');
      } catch {
        showToast('Taslak panoya kopyalanamadı. Tarayıcı iznini kontrol edin.', 'error');
      }
      return;
    }

    closeMailModal();
    showToast(`Mail taslağı hazırlandı -> ${draft.to}`, 'success');
    pushDashNote(`Tedarikçi mail taslağı hazırlandı -> ${draft.to}`);
  }, [closeMailModal, formatDraft, showToast, pushDashNote]);

  const handleManagerAlert = useCallback(async () => {
    showToast('Yönetici uyarısı gönderiliyor', 'info');
    const payload = {
      subject: 'SmartFlow AI - Yönetici Uyarısı',
      body: `Acil durum bildirimi:\n- Gecikmiş sipariş: ${navBadge.late}\n- Kritik stok: ${navBadge.crit}\n- Onay bekleyen: ${navBadge.pend}`,
    };
    const res = await sendAlertResult(payload);
    if (res.ok) {
      showToast('Yönetici uyarısı gönderildi', 'success');
      pushDashNote('Yönetici uyarısı gönderildi - POST /api/alerts/send');
    } else {
      showToast('Yönetici uyarısı gerçek servise ulaşamadı. Demo/fallback modunu kontrol edin.', 'warn');
      pushDashNote('Yönetici uyarısı gönderilemedi - servis bağlantısı kontrol edilmeli');
    }
  }, [navBadge, showToast, pushDashNote]);

  return (
    <ToastContext.Provider value={showToast}>
      <DashNoteContext.Provider value={{ dashNotes, pushDashNote, removeDashNote: (id) => setDashNotes(p => p.filter(n => n.id !== id)) }}>
        <MailModalContext.Provider value={openMailModal}>
          <NavBadgeContext.Provider value={{ navBadge, setNavBadge }}>
            <div className="app">
              <aside className="sidebar" aria-label="Ana navigasyon">
                <div className="logo">
                  <div className="logo-mark">SmartFlow AI</div>
                  <div className="logo-name">Yönetici Paneli</div>
                  <div className="logo-sub">KOBİ Operasyon Asistanı</div>
                </div>

                <span className="nav-section">Genel</span>
                <NavLink to="/" end className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
                  ⬛ Dashboard
                </NavLink>

                <span className="nav-section">Operasyon</span>
                <NavLink to="/orders" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
                  📦 Siparişler <span className="nav-badge red">{navBadge.late || '-'}</span>
                </NavLink>
                <NavLink to="/shipments" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
                  🚚 Kargolar
                </NavLink>
                <NavLink to="/products" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
                  🗃️ Ürünler <span className="nav-badge orange">{navBadge.crit || '-'}</span>
                </NavLink>
                <NavLink to="/tasks" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
                  📋 Görevler
                </NavLink>

                <span className="nav-section">Aksiyonlar</span>
                <NavLink to="/pending" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
                  ⏳ Onay Bekleyenler <span className="nav-badge">{navBadge.pend || '-'}</span>
                </NavLink>
                <button
                  type="button"
                  className="nav-item nav-button"
                  onClick={() => openMailModal('', '', 'ACİL: Kritik Stok Uyarısı - Acil Temin Talebi', '')}
                >
                  ✉️ Tedarikçi Mail
                </button>
                <NavLink to="/chat" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
                  💬 Müşteri Chat
                </NavLink>

                <div className="sidebar-bottom">
                  <div className="user-chip">
                    <div className="avatar">AY</div>
                    <div>
                      <div className="user-name">Ahmet Yılmaz</div>
                      <div className="user-role">Yönetici</div>
                    </div>
                  </div>
                </div>
              </aside>

              <div className="main">
                <div className="topbar">
                  <div className="topbar-left">
                    <div className="live-pill">
                      <div className="live-dot" />
                      <span className="live-text">Canlı</span>
                    </div>
                  </div>
                  <div className="topbar-right">
                    <Clock />
                    <button
                      className="btn btn-purple btn-sm"
                      aria-label="Tedarikçi mail taslağı aç"
                      onClick={() => openMailModal('', '', 'ACİL: Kritik Stok Uyarısı', '')}
                    >
                      ✉️ Tedarikçi Mail
                    </button>
                    <button className="btn btn-danger" aria-label="Yönetici uyarısı gönder" onClick={handleManagerAlert}>
                      🔔 Yönetici Uyarısı Gönder
                    </button>
                  </div>
                </div>

                <Outlet />
              </div>
            </div>

            <MailModalEl state={mailState} onClose={closeMailModal} onSend={handleMailSend} />
            <ToastHub toasts={toasts} onDismiss={dismissToast} />
          </NavBadgeContext.Provider>
        </MailModalContext.Provider>
      </DashNoteContext.Provider>
    </ToastContext.Provider>
  );
}
