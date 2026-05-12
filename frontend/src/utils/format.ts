export function formatNumber(value: number, decimals: number = 2): string {
  if (value === null || value === undefined || isNaN(value)) return "-";
  return value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatPercent(value: number): string {
  if (value === null || value === undefined || isNaN(value)) return "-";
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(2)}%`;
}

export function formatCurrency(value: number, currency: string = "CNY"): string {
  if (value === null || value === undefined || isNaN(value)) return "-";
  if (currency === "USD") return `$${formatNumber(value)}`;
  return `¥${formatNumber(value)}`;
}

export function formatCompactNumber(value: number): string {
  if (Math.abs(value) >= 1e8) return `${(value / 1e8).toFixed(2)}亿`;
  if (Math.abs(value) >= 1e4) return `${(value / 1e4).toFixed(2)}万`;
  return formatNumber(value);
}
