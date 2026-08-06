export function formatInr(value: number) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);
}

export function formatPct(value: number) {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}
