import React from 'react';

const CLS = { Kritik: 'pri-K', Yüksek: 'pri-Y', Orta: 'pri-O', Düşük: 'pri-D' };

export function PriorityChip({ priority }) {
  return <span className={`pri ${CLS[priority] || 'pri-D'}`}>{priority}</span>;
}
