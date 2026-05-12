export const MARKET_LABELS: Record<string, string> = {
  a_stock: "A股",
  us_stock: "美股",
  crypto: "加密货币",
};

export const STATUS_LABELS: Record<string, { type: string; label: string }> = {
  draft: { type: "info", label: "草稿" },
  running: { type: "success", label: "运行中" },
  stopped: { type: "warning", label: "已停止" },
  pending: { type: "info", label: "待成交" },
  submitted: { type: "", label: "已提交" },
  partial_filled: { type: "warning", label: "部分成交" },
  filled: { type: "success", label: "已成交" },
  cancelled: { type: "danger", label: "已撤单" },
  rejected: { type: "danger", label: "已拒绝" },
};

export const SIDE_LABELS: Record<string, string> = {
  buy: "买入",
  sell: "卖出",
};

export const TIMEFRAME_OPTIONS = [
  { label: "1分钟", value: "1m" },
  { label: "5分钟", value: "5m" },
  { label: "15分钟", value: "15m" },
  { label: "30分钟", value: "30m" },
  { label: "1小时", value: "1h" },
  { label: "4小时", value: "4h" },
  { label: "日线", value: "1d" },
  { label: "周线", value: "1w" },
];
