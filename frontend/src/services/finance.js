/**
 * 投研分析 API 服务
 *
 * 复用现有 streamChat 的 SSE 基建，封装投研场景的调用。
 * 后端 data_collector 节点会自动从 query 中提取股票代码并拉取数据。
 */
import { streamChat, getThreadId, newThreadId } from "./api";
import { getApiBase } from "./config";

/**
 * 获取 API 基地址（同源相对路径 / 构建 env / 设置页自定义）
 * 注意：以前这里兜底写死 http://localhost:8000，与 api.js 不一致，Docker/生产必挂；
 * 统一走 config.getApiBase() 后全站一致。
 */
const apiBase = getApiBase;

/**
 * 提取股票代码（前端轻量提取，用于 UI 显示）
 * @param {string} query
 * @returns {string} 股票代码或空字符串
 */
export function extractStockCode(query) {
 if (!query) return "";
 const patterns = [/\b([36]0\d{4})\b/, /\b(00\d{4})\b/, /(\d{6})/];
 for (var i = 0; i < patterns.length; i++) {
  var match = query.match(patterns[i]);
  if (match) return match[1];
 }
 return "";
}

/**
 * 投研分析流式调用
 * @param {string} query - 用户查询（如 "分析复星医药 600196"）
 * @param {object} callbacks - { onData, onDone, onError, onStep }
 * @param {AbortSignal} signal
 */
export function streamResearch(query, callbacks, signal) {
 // 投研模式固定使用 hybrid（网络搜索 + 本地文档）
 return streamChat(
  query,
  "hybrid",
  callbacks.onData,
  callbacks.onDone,
  callbacks.onError,
  signal,
 );
}

/**
 * 获取股票基本信息（用于 UI 卡片展示）
 * @param {string} stockCode
 */
export async function getStockInfo(stockCode) {
 const response = await fetch(`${apiBase()}/api/stock/${stockCode}/info`);
 if (!response.ok) throw new Error("Failed to fetch stock info");
 return await response.json();
}

/**
 * 获取财务指标（用于 UI 卡片展示）
 * @param {string} stockCode
 */
export async function getFinancialIndicators(stockCode) {
 const response = await fetch(`${apiBase()}/api/stock/${stockCode}/financial`);
 if (!response.ok) throw new Error("Failed to fetch financial indicators");
 return await response.json();
}

/**
 * 获取实时行情（用于 UI 卡片展示）
 * @param {string} stockCode
 */
export async function getStockQuote(stockCode) {
 const response = await fetch(`${apiBase()}/api/stock/${stockCode}/quote`);
 if (!response.ok) throw new Error("Failed to fetch stock quote");
 return await response.json();
}

/**
 * 批量行情快照（行情页轮询用）：三大指数 + 自选股一次拉回。
 * @param {string[]} codes 6 位股票代码数组（≤30）
 * @returns {{indexes: Array, stocks: Array, errors: Array, updated_at: number}}
 */
export async function getMarketSnapshot(codes) {
 const qs = (codes || []).join(",");
 const response = await fetch(
  `${apiBase()}/api/market/snapshot?codes=${encodeURIComponent(qs)}`
 );
 if (!response.ok) throw new Error("Failed to fetch market snapshot");
 return await response.json();
}

/**
 * 获取日 K 收盘价序列（Sparkline 30 日走势用）
 * @param {string} stockCode
 * @returns {Promise<{code, kline: number[], dates: string[]}>}
 */
export async function getStockKline(stockCode) {
 const response = await fetch(
  `${apiBase()}/api/stock/${stockCode}/kline?days=30`
 );
 if (!response.ok) throw new Error("Failed to fetch stock kline");
 return await response.json();
}

/**
 * 热门标的（东财人气榜，失败回退实时涨幅排序）
 * @param {number} take
 * @returns {Promise<{items: Array, source: string}>}
 */
export async function getMarketHot(take = 6) {
 const response = await fetch(`${apiBase()}/api/market/hot?take=${take}`);
 if (!response.ok) throw new Error("Failed to fetch market hot");
 return await response.json();
}

/**
 * 指数日 K 收盘价序列（行情页指数卡 Sparkline 用）
 * 注意：指数代码与个股重叠（000001=上证指数 vs 平安银行），走独立端点。
 * @param {string} indexCode 如 "000001" / "399001" / "399006"
 * @returns {Promise<{code, name, kline: number[], dates: string[]}>}
 */
export async function getIndexKline(indexCode) {
 const response = await fetch(
  `${apiBase()}/api/index/${indexCode}/kline?days=30`
 );
 if (!response.ok) throw new Error("Failed to fetch index kline");
 return await response.json();
}

/**
 * 股票名称解析（自选股只输代码时自动补全名称）
 * @param {string} stockCode 6 位代码
 * @returns {Promise<string>} 名称，失败返回代码本身
 */
export async function getStockName(stockCode) {
 try {
  const info = await getStockInfo(stockCode);
  const name =
   info?.stock_info?.name ||
   info?.name ||
   info?.stock_name ||
   info?.stock_code_name ||
   "";
  return name || stockCode;
 } catch {
  return stockCode;
 }
}

export { getThreadId, newThreadId };
