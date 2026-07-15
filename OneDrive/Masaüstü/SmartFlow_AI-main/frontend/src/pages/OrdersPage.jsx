import React, { useState } from 'react';
import { useApiData } from '../hooks/useApiData.jsx';
import { Badge } from '../components/Badge.jsx';

const norm = value => String(value ?? '').toLocaleLowerCase('tr');

export default function OrdersPage() {
  const { orders, resources, loading } = useApiData();
  const [filterStatus, setFilterStatus] = useState('');
  const [filterCargo, setFilterCargo] = useState('');
  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState('order_id');
  const [sortDir, setSortDir] = useState('desc');

  const filters = [
    filterStatus && `Durum: ${filterStatus}`,
    filterCargo && `Kargo: ${filterCargo}`,
    query && `Arama: ${query}`,
  ].filter(Boolean);

  const rows = orders
    .filter(o =>
      (!filterStatus || o.status === filterStatus) &&
      (!filterCargo || o.cargo_status === filterCargo) &&
      (!query || [o.order_id, o.customer_name, o.product_id, o.tracking_number].some(v => norm(v).includes(norm(query))))
    )
    .sort((a, b) => {
      const av = a[sortKey] ?? '';
      const bv = b[sortKey] ?? '';
      const dir = sortDir === 'asc' ? 1 : -1;
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
    setFilterCargo('');
    setQuery('');
  }

  const emptyMessage = loading
    ? 'Yükleniyor...'
    : resources?.orders?.error
      ? 'Sipariş verisi alınamadı. Tekrar deneyin.'
      : filters.length
        ? 'Filtrelerle eşleşen sipariş yok.'
        : 'Sipariş kaydı yok.';

  return (
    <div className="page-content">
      <div className="shdr">
        <div className="stitle">📦 Siparişler <span className="scnt">{rows.length}</span></div>
        <div className="filter-bar">
          <input className="search-input" value={query} onChange={e => setQuery(e.target.value)} placeholder="ID, müşteri veya ürün ara" />
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
            <option value="">Tüm Durumlar</option>
            <option value="Hazırlanıyor">Hazırlanıyor</option>
            <option value="Kargoda">Kargoda</option>
            <option value="Teslim Edildi">Teslim Edildi</option>
          </select>
          <select value={filterCargo} onChange={e => setFilterCargo(e.target.value)}>
            <option value="">Tüm Kargo</option>
            <option value="Gecikmiş">Gecikmiş</option>
            <option value="Zamanında">Zamanında</option>
            <option value="Dağıtımda">Dağıtımda</option>
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
              <th><button className="th-sort" type="button" onClick={() => toggleSort('order_id')}>Sipariş ID</button></th>
              <th>Müşteri</th><th>Ürün</th>
              <th><button className="th-sort" type="button" onClick={() => toggleSort('quantity')}>Adet</button></th>
              <th>Durum</th><th>Kargo Durumu</th>
              <th><button className="th-sort" type="button" onClick={() => toggleSort('estimated_delivery')}>Tahmini Teslimat</button></th>
              <th><button className="th-sort" type="button" onClick={() => toggleSort('delay_days')}>Gecikme</button></th>
              <th>Tarih</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0
              ? <tr><td colSpan={9} className="empty">{emptyMessage}</td></tr>
              : rows.map(o => (
                  <tr key={o.order_id}>
                    <td className="cm">#{o.order_id}</td>
                    <td className="cb">{o.customer_name}</td>
                    <td className="cm">{o.product_id}</td>
                    <td className="cm">{o.quantity}</td>
                    <td><Badge label={o.status} /></td>
                    <td><Badge label={o.cargo_status} /></td>
                    <td className="cm">{o.estimated_delivery}</td>
                    <td>
                      {o.delay_days > 0
                        ? <span style={{ color: 'var(--red)', fontFamily: 'var(--mono)', fontSize: 11 }}>+{o.delay_days}g</span>
                        : <span style={{ color: 'var(--muted)' }}>-</span>}
                    </td>
                    <td className="cm">{o.created_at ? new Date(o.created_at).toLocaleDateString('tr') : '-'}</td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
