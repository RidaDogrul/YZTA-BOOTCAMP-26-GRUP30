import React from 'react';

const COLOR_MAP = {
  green: 'b-green',
  blue: 'b-blue',
  yellow: 'b-yellow',
  red: 'b-red',
  orange: 'b-orange',
  purple: 'b-purple',
  cyan: 'b-cyan',
  gray: 'b-gray',
};

const STATUS_COLOR = {
  'Hazırlanıyor': 'yellow',
  'Kargoda': 'blue',
  'Teslim Edildi': 'green',
  'Gecikmiş': 'red',
  'Zamanında': 'green',
  'Dağıtımda': 'blue',
  'Kargoya Verildi': 'cyan',
  'Depoda': 'yellow',
  'Bekliyor': 'gray',
  'Devam Ediyor': 'blue',
  'Onay Bekliyor': 'purple',
  'Onay bekliyor': 'purple',
  'Tamamlandı': 'green',
  'İptal': 'gray',
};

export function Badge({ label, color }) {
  const cls = color ? COLOR_MAP[color] || 'b-gray' : COLOR_MAP[STATUS_COLOR[label]] || 'b-gray';
  return (
    <span className={`badge ${cls}`}>
      <span className="bd" />
      {label}
    </span>
  );
}
