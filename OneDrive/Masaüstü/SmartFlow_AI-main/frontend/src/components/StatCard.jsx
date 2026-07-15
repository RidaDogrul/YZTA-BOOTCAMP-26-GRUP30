import React from 'react';

export function StatCard({ icon, value, label, delta, deltaClass, color }) {
  return (
    <div className="stat-card fi" style={{ '--ca': color }}>
      <span className="stat-icon">{icon}</span>
      <div className="stat-value">{value ?? <span className="sk" style={{ width: 36, height: 22, display: 'block' }} />}</div>
      <div className="stat-label">{label}</div>
      <span className={`stat-delta ${deltaClass || 'd-neu'}`}>{delta || '—'}</span>
    </div>
  );
}
