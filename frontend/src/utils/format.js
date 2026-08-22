/**
 * 金融数据格式化工具
 * 规则：红色涨(#DC2626) / 绿色跌(#059669) / 三档字号 / 等宽数字
 * 严格遵循 docs/UI_DESIGN_GUIDE.md
 */

/** 解析涨跌幅字符串，返回 { value, direction, colorClass, sign } */
export function parseChange(raw) {
 if (raw == null || raw === "" || raw === "N/A" || raw === "-") {
  return { display: "-", direction: 0, colorClass: "text-slate-400", sign: "" };
 }
 const str = String(raw).replace(/[%\s]/g, "");
 const num = parseFloat(str);
 if (isNaN(num)) {
  return {
   display: String(raw),
   direction: 0,
   colorClass: "text-slate-400",
   sign: "",
  };
 }
 const direction = num > 0 ? 1 : num < 0 ? -1 : 0;
 // A 股习惯：红涨绿跌
 const colorClass =
  direction > 0 ? "text-up" : direction < 0 ? "text-down" : "text-slate-400";
 const sign = direction > 0 ? "+" : "";
 const display =
  direction === 0 ? `${num.toFixed(2)}%` : `${sign}${num.toFixed(2)}%`;
 return { display, direction, colorClass, sign };
}

/** 格式化大数字：亿 / 万亿 */
export function formatBigInt(val) {
 if (val == null || val === "" || val === "N/A" || val === "-") return "-";
 const num =
  typeof val === "number" ? val : parseFloat(String(val).replace(/[,，]/g, ""));
 if (isNaN(num)) return String(val);
 if (num >= 1e8) return `${(num / 1e8).toFixed(2)} 万亿`;
 if (num >= 1e4) return `${(num / 1e4).toFixed(2)} 亿`;
 return num.toLocaleString();
}
/** 格式化同比数据：带箭头 + 颜色 */
export function formatYoY(val) {
  if (val == null || val === "" || val === "N/A" || val === "-") return null;
  const num = typeof val === "number" ? val : parseFloat(String(val).replace(/[%,，]/g, ""));
  if (isNaN(num)) return null;
  const arrow = num > 0 ? "↑" : num < 0 ? "↓" : "";
  const sign = num > 0 ? "+" : "";
  return { arrow, display: `${sign}${num.toFixed(1)}%`, direction: num > 0 ? 1 : num < 0 ? -1 : 0 };
}

/** 格式化价格：保留两位小数 */
export function formatPrice(val) {
 if (val == null || val === "" || val === "N/A" || val === "-") return "-";
 const num =
  typeof val === "number" ? val : parseFloat(String(val).replace(/[,，]/g, ""));
 if (isNaN(num)) return String(val);
 return num.toFixed(2);
}

/** 安全获取嵌套字段 */
export function pick(obj, path, fallback = "-") {
 if (!obj) return fallback;
 const keys = path.split(".");
 let cur = obj;
 for (const k of keys) {
  if (cur == null || typeof cur !== "object") return fallback;
  cur = cur[k];
 }
 return cur == null || cur === "" || cur === "N/A" ? fallback : cur;
}
