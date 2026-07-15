import React, { useState } from 'react';
import { useApiData } from '../hooks/useApiData.jsx';
import { Badge } from '../components/Badge.jsx';

const norm = value => String(value ?? '').toLocaleLowerCase('tr');

export default function ShipmentsPage() {
  const { shipments, resources, loading } = useApiData();
  const [filter, setFilter] = useState('');
  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState('shipment_id');
  const [sortDir, setSortDir] = useState('desc');

  const filters = [
    filter && `Durum: ${filter}`,
    query && `Arama: ${query}`,
  ].filter(Boolean);

  const rows = shipments
    .filter(s =>
      (!filter || s.actual_status === filter) &&
      (!query || [s.shipment_id, s.order_id, s.carrier, s.tracking_number, s.last_location].some(v => norm(v).includes(norm(query))))
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
    setFilter('');
    setQuery('');
  }

  const emptyMessage = loading
    ? 'Yükleniyor...'
    : resources?.shipments?.error
      ? 'Kargo verisi alınamadı. Tekrar deneyin.'
      : filters.length
        ? 'Filtrelerle eşleşen kargo yok.'
        : 'Kargo kaydı yok.';

  return (
    <div className="page-content">
      <div className="shdr">
        <div className="stitle">🚚 Kargolar <span className="scnt">{rows.length}</span></div>
        <div className="filter-bar">
          <input className="search-input" value={query} onChange={e => setQuery(e.target.value)} placeholder="Takip no, firma veya konum ara" />
          <select value={filter} onChange={e => setFilter(e.target.value)}>
            <option value="">Tüm Durumlar</option>
            <option value="Teslim Edildi">Teslim Edildi</option>
            <option value="Dağıtımda">Dağıtımda</option>
            <option value="Kargoya Verildi">Kargoya Verildi</option>
            <option value="Gecikmiş">Gecikmiş</option>
            <option value="Depoda">Depoda</option>
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
              <th><button className="th-sort" type="button" onClick={() => toggleSort('shipment_id')}>Kargo ID</button></th><th>Sipariş</th><th>Firma</th><th>Takip No</th>
              <th>Durum</th><th>Son Konum</th><th><button className="th-sort" type="button" onClick={() => toggleSort('delay_days')}>Gecikme (gün)</button></th><th>ETA</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0
              ? <tr><td colSpan={8} className="empty">{emptyMessage}</td></tr>
              : rows.map(s => (
                  <tr key={s.shipment_id}>
                    <td className="cm">#{s.shipment_id}</td>
                    <td className="cm">#{s.order_id}</td>
                    <td className="cm">{s.carrier}</td>
                    <td className="cm">{s.tracking_number}</td>
                    <td><Badge label={s.actual_status} /></td>
                    <td className="cm">{s.last_location}</td>
                    <td>
                      {s.delay_days > 0
                        ? <span style={{ color: 'var(--red)', fontFamily: 'var(--mono)', fontSize: 11 }}>+{s.delay_days}</span>
                        : <span style={{ color: 'var(--muted)' }}>-</span>}
                    </td>
                    <td className="cm">{s.estimated_delivery}</td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
