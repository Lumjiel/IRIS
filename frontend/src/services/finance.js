/**
 * 投研分析 API 服务
 *
 * 复用现有 streamChat 的 SSE 基建，封装投研场景的调用。
 * 后端 data_collector 节点会自动从 query 中提取股票代码并拉取数据。
 */
import { streamChat, getThreadId, newThreadId } from './api';

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

/**
 * 提取股票代码（前端轻量提取，用于 UI 显示）
 * @param {string} query
 * @returns {string} 股票代码或空字符串
 */
export function extractStockCode(query) {
  if (!query) return "";
  const patterns = [
    /\b([36]0\d{4})\b/,
    /\b(00\d{4})\b/,
    /(\d{6})/,
  ];
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
  return streamChat(query, "hybrid", callbacks.onData, callbacks.onDone, callbacks.onError, signal);
}

/**
 * 获取股票基本信息（用于 UI 卡片展示）
 * @param {string} stockCode
 */
export async function getStockInfo(stockCode) {
  const response = await fetch(`${API_BASE}/api/stock/${stockCode}/info`);
  if (!response.ok) throw new Error('Failed to fetch stock info');
  return await response.json();
}

/**
 * 获取财务指标（用于 UI 卡片展示）
 * @param {string} stockCode
 */
export async function getFinancialIndicators(stockCode) {
  const response = await fetch(`${API_BASE}/api/stock/${stockCode}/financial`);
  if (!response.ok) throw new Error('Failed to fetch financial indicators');
  return await response.json();
}

/**
 * 获取实时行情（用于 UI 卡片展示）
 * @param {string} stockCode
 */
export async function getStockQuote(stockCode) {
  const response = await fetch(`${API_BASE}/api/stock/${stockCode}/quote`);
  if (!response.ok) throw new Error('Failed to fetch stock quote');
  return await response.json();
}

export { getThreadId, newThreadId };
