/**
 * 研究历史管理 - 基于 localStorage 的会话持久化
 * 最多保存 50 条记录，每条限制 50KB
 */

const STORAGE_KEY = 'iris_research_history'
const MAX_SESSIONS = 50
const MAX_REPORT_SIZE = 50 * 1024 // 50KB per report

export function getHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function saveSession(session) {
  try {
    const history = getHistory()
    // 截断过长的报告
    const report = session.report && session.report.length > MAX_REPORT_SIZE
      ? session.report.substring(0, MAX_REPORT_SIZE) + '\n\n[报告已截断...]'
      : session.report

    history.unshift({
      id: session.id || crypto.randomUUID(),
      query: session.query,
      report: report,
      mode: session.mode || 'hybrid',
      timestamp: Date.now()
    })

    // 超限时淘汰最早的
    if (history.length > MAX_SESSIONS) {
      history.splice(MAX_SESSIONS)
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(history))
    return true
  } catch {
    return false
  }
}

export function deleteSession(id) {
  try {
    const history = getHistory().filter(s => s.id !== id)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history))
    return true
  } catch {
    return false
  }
}

export function clearHistory() {
  try {
    localStorage.removeItem(STORAGE_KEY)
    return true
  } catch {
    return false
  }
}

export function markAsUsed(id) {
  try {
    const history = getHistory()
    const item = history.find(s => s.id === id)
    if (item) {
      item.usedAt = Date.now()
      localStorage.setItem(STORAGE_KEY, JSON.stringify(history))
    }
    return true
  } catch {
    return false
  }
}
