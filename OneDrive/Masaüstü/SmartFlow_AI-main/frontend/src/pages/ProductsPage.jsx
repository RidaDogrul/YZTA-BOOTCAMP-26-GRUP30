import React, { useState } from 'react';
import { useApiData } from '../hooks/useApiData.jsx';
import { Badge } from '../components/Badge.jsx';
import { useMailModal } from '../components/Layout.jsx';

const norm = value => String(value ?? '').toLocaleLowerCase('tr');

export default function ProductsPage() {
  const { products, resources, loading } = useApiData();
  const openMailModal = useMailModal();
  const [filter, setFilter] = useState('');
  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState('stock_count');
  const [sortDir, setSortDir] = useState('asc');

  const filters = [
    filter && `Stok: ${filter === 'kritik' ? 'Kritik' : 'Normal'}`,
    query && `Arama: ${query}`,
  ].filter(Boolean);

  const rows = products
    .filter(p => {
      if (filter === 'kritik' && p.stock_count > p.critical_threshold) return false;
      if (filter === 'normal' && p.stock_count <= p.critical_threshold) return false;
      if (query && ![p.product_id, p.product_name, p.supplier_email].some(v => norm(v).includes(norm(query)))) return false;
      return true;
    })
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

  function handleMailFor(p) {
    const body = `Sayın Tedarikçi Yetkilisi,\n\n"${p.product_name}" (${p.product_id}) ürünümüzün stoğu kritik seviyeye düşmüştür.\n\nMevcut stok: ${p.stock_count} adet\nKritik eşik: ${p.critical_threshold} adet\n\nEn kısa sürede fiyat ve teslim süresi bilgisini paylaşabilir misiniz?\n\nSaygılarımla,\nSatın Alma - SmartFlow AI`;
    openMailModal(p.product_name, p.supplier_email, `ACİL: ${p.product_name} - Stok Yenileme Talebi`, body);
  }

  function clearFilters() {
    setFilter('');
    setQuery('');
  }

  const emptyMessage = loading
    ? 'Yükleniyor...'
    : resources?.products?.error
      ? 'Ürün verisi alınamadı. Tekrar deneyin.'
      : filters.length
        ? 'Filtrelerle eşleşen ürün yok.'
        : 'Ürün kaydı yok.';

  return (
    <div className="page-content">
      <div className="shdr">
        <div className="stitle">🗃️ Ürünler <span className="scnt">{rows.length}</span></div>
        <div className="filter-bar">
          <input className="search-input" value={query} onChange={e => setQuery(e.target.value)} placeholder="Ürün, ID veya tedarikçi ara" />
          <select value={filter} onChange={e => setFilter(e.target.value)}>
            <option value="">Tümü</option>
            <option value="kritik">Kritik Stok</option>
            <option value="normal">Normal Stok</option>
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
              <th>Ürün ID</th><th><button className="th-sort" type="button" onClick={() => toggleSort('product_name')}>Ürün Adı</button></th><th>Fiyat</th>
              <th><button className="th-sort" type="button" onClick={() => toggleSort('stock_count')}>Stok</button></th><th>Min Eşik</th><th>Stok Durumu</th>
              <th>Müsait</th><th>Tedarikçi</th><th>İşlem</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0
              ? <tr><td colSpan={9} className="empty">{emptyMessage}</td></tr>
              : rows.map(p => {
                  const pct = Math.round(p.stock_count / p.critical_threshold * 100);
                  const col = pct < 10 ? 'var(--red)' : pct < 20 ? 'var(--orange)' : pct < 50 ? 'var(--yellow)' : 'var(--green)';
                  const severity = pct < 10 ? 'Kritik' : pct < 20 ? 'Düşük' : pct < 50 ? 'İzle' : 'Normal';
                  const isCrit = p.stock_count <= p.critical_threshold;
                  return (
                    <tr key={p.product_id}>
                      <td className="cm">{p.product_id}</td>
                      <td className="cb">{p.product_name}</td>
                      <td className="cm">₺{p.price}</td>
                      <td>
                        <span style={{ fontFamily: 'var(--mono)', fontSize: 12, color: col, fontWeight: 600 }}>
                          {p.stock_count}
                        </span>
                      </td>
                      <td className="cm">{p.critical_threshold}</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 150 }}>
                          <div className="sb" style={{ flex: 1 }}>
                            <div className="sbf" style={{ width: `${Math.min(pct, 100)}%`, background: col }} />
                          </div>
                          <span className="sbp">{severity} %{pct}</span>
                        </div>
                      </td>
                      <td><Badge label={p.available ? 'Var' : 'Yok'} color={p.available ? 'green' : 'red'} /></td>
                      <td className="cm" style={{ fontSize: 10 }}>{p.supplier_email}</td>
                      <td>
                        <button
                          className="btn btn-ghost btn-sm"
                          aria-label={`${p.product_name} için mail taslağı aç`}
                          style={isCrit ? { background: 'rgba(249,115,22,.12)', color: 'var(--orange)', border: '1px solid rgba(249,115,22,.25)' } : {}}
                          onClick={() => handleMailFor(p)}
                        >
                          {isCrit ? '⚡ Mail taslağı' : '✉️ Mail'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
