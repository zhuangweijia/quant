export function toNum(value: any): number {
  if (value === null || value === undefined) return NaN;
  const n = Number(value);
  return isNaN(n) ? NaN : n;
}

export function formatNumber(value: any, decimals: number = 2): string {
  const n = toNum(value);
  if (isNaN(n)) return "-";
  return n.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatPercent(value: any): string {
  const n = toNum(value);
  if (isNaN(n)) return "-";
  const sign = n > 0 ? "+" : "";
  return `${sign}${(n * 100).toFixed(2)}%`;
}

export function formatCurrency(value: any, currency: string = "CNY"): string {
  const n = toNum(value);
  if (isNaN(n)) return "-";
  if (currency === "USD") return `$${formatNumber(n)}`;
  return `¥${formatNumber(n)}`;
}

export function formatCompactNumber(value: any): string {
  const n = toNum(value);
  if (isNaN(n)) return "-";
  if (Math.abs(n) >= 1e8) return `${(n / 1e8).toFixed(2)}亿`;
  if (Math.abs(n) >= 1e4) return `${(n / 1e4).toFixed(2)}万`;
  return formatNumber(n);
}
