/**
 * 研究历史管理 - 基于 localStorage 的会话持久化
 * 支持保存消息列表、thread_id，实现刷新恢复 + 多轮对话
 *
 * 删除语义（tombstone）：被删除的会话按 thread_id 记入删除标记。
 * 只要 threadId 在标记里，saveSession 就拒绝写回——防止删除后
 * 该会话因一次新的流式响应完成而被"复活"（历史删不掉的根因）。
 */

const STORAGE_KEY = 'iris_research_history'
const DELETED_KEY = 'iris_deleted_threads'
const MAX_SESSIONS = 50
const MAX_REPORT_SIZE = 50 * 1024
const MAX_DELETED_MARKS = 200

export function getHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

/** 读取被删除的 threadId 集合 */
function getDeletedThreads() {
  try {
    const raw = localStorage.getItem(DELETED_KEY)
    const arr = raw ? JSON.parse(raw) : []
    return new Set(Array.isArray(arr) ? arr : [])
  } catch {
    return new Set()
  }
}

function persistDeletedThreads(set) {
  try {
    // 防膨胀：只保留最近 200 个标记
    const arr = [...set].slice(-MAX_DELETED_MARKS)
    localStorage.setItem(DELETED_KEY, JSON.stringify(arr))
  } catch {
    // localStorage 不可用时静默降级
  }
}

/** 该 threadId 是否已被用户删除（被删会话不得再写回） */
export function isDeletedThread(threadId) {
  return threadId ? getDeletedThreads().has(threadId) : false
}

function markDeletedThread(threadId) {
  if (!threadId) return
  const set = getDeletedThreads()
  set.add(threadId)
  persistDeletedThreads(set)
}

export function saveSession(session) {
  try {
    // 已被用户删除的会话：拒绝写回（防复活）
    if (isDeletedThread(session.threadId)) return false

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
    const history = getHistory()
    const target = history.find(s => s.id === id)
    if (target) markDeletedThread(target.threadId) // 标记，防止同 thread 复活
    const filtered = history.filter(s => s.id !== id)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered))
    return true
  } catch {
    return false
  }
}

export function clearHistory() {
  try {
    // 清空列表前把现有所有 threadId 标记为删除，防止当前/历史会话复活
    const history = getHistory()
    const set = getDeletedThreads()
    history.forEach(s => s.threadId && set.add(s.threadId))
    persistDeletedThreads(set)
    localStorage.removeItem(STORAGE_KEY)
    return true
  } catch {
    return false
  }
}

/** 按 id 取一条会话（HistoryView 加载用） */
export function getSessionById(id) {
  return getHistory().find(s => s.id === id) || null
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
