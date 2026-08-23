// frontend/src/services/api.js

// 默认相对路径：开发走 vite proxy，Docker 生产走 nginx 反代（见 deploy/nginx.conf）。
// 仅特殊部署（前后端不同域）才需要设置 VITE_API_BASE。
const API_BASE = import.meta.env.VITE_API_BASE || "";

export function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
  });
}

// 会话级 ID：可持久化，支持刷新后恢复
let _threadId;
try {
  _threadId = localStorage.getItem('iris_thread_id') || crypto.randomUUID();
  localStorage.setItem('iris_thread_id', _threadId);
} catch {
  // localStorage 不可用时降级为内存模式
  _threadId = generateUUID();
}

export function getThreadId() { return _threadId; }
export function setThreadId(id) {
  _threadId = id;
  try {
    localStorage.setItem('iris_thread_id', id);
  } catch {
    // localStorage 不可用时静默降级
  }
}
export function newThreadId() {
  const id = crypto.randomUUID();
  _threadId = id;
  try {
    localStorage.setItem('iris_thread_id', id);
  } catch {
    // localStorage 不可用时静默降级
  }
  return id;
}

/**
 * 批量上传文件
 * @param {Array<File>} files - 文件对象数组
 */
export async function uploadFiles(files) {
    const formData = new FormData();
    files.forEach(file => {
        formData.append('files', file);
    });

    const response = await fetch(`${API_BASE}/api/upload`, {
        method: 'POST',
        body: formData,
    });
    if (!response.ok) throw new Error('Upload failed');
    return await response.json();
}

export async function clearContext() {
  const response = await fetch(`${API_BASE}/api/clear`, {
      method: "POST"
  });
  if (!response.ok) throw new Error('Clear failed');
  return await response.json();
}

/**
 * 流式聊天
 * @param {string} query - 用户查询
 * @param {string} search_mode - 搜索模式 (document/hybrid)
 * @param {function} onData - 数据回调
 * @param {function} onDone - 完成回调
 * @param {function} onError - 错误回调
 * @param {AbortSignal} signal - 中止信号
 */
export async function streamChat(query, search_mode, onData, onDone, onError, signal) {
  let prefs = {};
  try {
    prefs = JSON.parse(localStorage.getItem('iris_preferences') || '{}');
  } catch {
    // JSON 解析失败时静默降级
  }
  
  try {
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        search_mode,
        thread_id: getThreadId(),
        // 后端 ChatRequest 契约为顶层 style/language 字段（preferences 对象会被 Pydantic 忽略）
        style: prefs.style || 'detailed',
        language: prefs.language || 'zh',
      }),
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let finished = false;
    // 完成守卫：onDone 只触发一次（[DONE] 行 / type=done 事件 / reader 结束三路任一）
    const finish = () => {
      if (!finished) {
        finished = true;
        onDone();
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const payload = line.slice(6);
          if (payload.trim() === '[DONE]') {
            finish();
            continue;
          }
          try {
            const data = JSON.parse(payload);
            onData(data);
            if (data.type === 'done') {
              finish();
            }
          } catch {
            // JSON 解析失败时跳过该行
          }
        }
      }
    }
    // 流自然结束（后端 [DONE] 可能被代理吞掉）：兜底触发完成回调，避免 isLoading 永久挂起
    finish();
  } catch (error) {
    if (error.name === 'AbortError') {
      onDone();
      return;
    }
    onError(error);
  }
}

/**
 * 获取 AI HOT 新闻
 */
export async function fetchAihotNews(take = 20, query = null) {
  const params = new URLSearchParams({ mode: 'selected', take });
  if (query) params.set('q', query);
  const response = await fetch(`${API_BASE}/api/aihot/news?${params}`);
  if (!response.ok) throw new Error('Failed to fetch news');
  return await response.json();
}

/**
 * 保存报告到创作目录
 */
export async function saveReport(query, report, watermark = true) {
  const response = await fetch(`${API_BASE}/api/save-report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, report, watermark }),
  });
  if (!response.ok) throw new Error('Failed to save report');
  return await response.json();
}

export async function listMaterials() {
  const response = await fetch(`${API_BASE}/api/materials`);
  if (!response.ok) throw new Error('Failed to list materials');
  return await response.json();
}

export async function deleteMaterial(filename) {
  const response = await fetch(`${API_BASE}/api/materials/${encodeURIComponent(filename)}`, { method: 'DELETE' });
  if (!response.ok) throw new Error('Failed to delete material');
  return await response.json();
}

export async function getMaterial(filename) {
  const response = await fetch(`${API_BASE}/api/materials/${encodeURIComponent(filename)}`);
  if (!response.ok) throw new Error('Failed to get material');
  return await response.json();
}

/**
 * 获取会话记忆摘要
 */
export async function getMemory(threadId) {
  const response = await fetch(`${API_BASE}/api/memory/${encodeURIComponent(threadId)}`);
  if (!response.ok) return { summary: '', turns: 0 };
  return await response.json();
}

/**
 * 清空会话记忆摘要（保留报告）
 */
export async function resetMemory(threadId) {
  const response = await fetch(`${API_BASE}/api/memory/${encodeURIComponent(threadId)}/reset`, {
    method: 'POST'
  });
  if (!response.ok) throw new Error('Failed to reset memory');
  return await response.json();
}

/**
 * TTS 语音合成
 */
export async function ttsSynthesize(text, voice = 'longtian_v3') {
  const response = await fetch(`${API_BASE}/api/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, voice }),
  });
  if (!response.ok) throw new Error('TTS failed');
  return await response.blob();
}
