import React from 'react';

export function StockBar({ stock, threshold }) {
  const pct = Math.min(Math.round((stock / threshold) * 100), 100);
  const col = pct < 10 ? 'var(--red)' : pct < 20 ? 'var(--orange)' : pct < 50 ? 'var(--yellow)' : 'var(--green)';
  const label = pct < 10 ? 'Kritik' : pct < 20 ? 'Dusuk' : pct < 50 ? 'Izle' : 'Normal';
  return (
    <div className="sbw">
      <div className="sb">
        <div className="sbf" style={{ width: `${pct}%`, background: col }} />
      </div>
      <span className="sbp">{label} %{pct}</span>
    </div>
  );
}
