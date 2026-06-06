/**
 * 研究历史管理 - 基于 localStorage 的会话持久化
 * 支持保存消息列表、thread_id，实现刷新恢复 + 多轮对话
 */

const STORAGE_KEY = 'iris_research_history'
const MAX_SESSIONS = 50
const MAX_REPORT_SIZE = 50 * 1024

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
    const report = session.report && session.report.length > MAX_REPORT_SIZE
      ? session.report.substring(0, MAX_REPORT_SIZE) + '\n\n[报告已截断...]'
      : session.report

    // 查找是否已有同 thread_id 的会话（多轮对话更新）
    const existingIdx = history.findIndex(s => s.threadId === session.threadId)
    const entry = {
      id: session.id || crypto.randomUUID(),
      threadId: session.threadId,
      query: session.query,
      report: report,
      messages: session.messages || [],
      mode: session.mode || 'hybrid',
      timestamp: Date.now()
    }

    if (existingIdx >= 0) {
      // 更新已有会话（保留原始 id）
      entry.id = history[existingIdx].id
      history[existingIdx] = entry
    } else {
      history.unshift(entry)
      if (history.length > MAX_SESSIONS) history.splice(MAX_SESSIONS)
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
