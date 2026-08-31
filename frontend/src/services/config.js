/**
 * API 基地址统一解析
 *
 * 优先级：构建时 VITE_API_BASE > 设置页保存的 iris_api_base > ""（同源，走 vite proxy / nginx 反代）。
 * 之前 finance.js 兜底写死 "http://localhost:8000"，与 api.js 的相对路径约定不一致，
 * 导致 Docker/生产环境行情类请求直连浏览器本机 8000 而失败。统一后全站走此函数。
 */
export function getApiBase() {
  if (import.meta.env.VITE_API_BASE) {
    return String(import.meta.env.VITE_API_BASE).replace(/\/+$/, "");
  }
  try {
    const saved = localStorage.getItem("iris_api_base");
    if (saved && saved.trim()) {
      return saved.trim().replace(/\/+$/, "");
    }
  } catch {
    // localStorage 不可用时静默降级为同源
  }
  return "";
}
