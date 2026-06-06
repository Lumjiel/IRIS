// frontend/src/services/api.js

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8001/api";

function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
  });
}

// 会话级 ID：页面一刷新就重置，满足"单次会话记忆"需求
const SESSION_THREAD_ID = generateUUID();
/**
 * 批量上传文件
 * @param {Array<File>} files - 文件对象数组
 */
export async function uploadFiles(files) {
    const formData = new FormData();
    // 遍历文件数组，把它们都塞进 'files' 字段里
    files.forEach(file => {
        formData.append('files', file);
    });

    // 发送 POST 请求到 /upload
    const response = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData
    });
    
    if (!response.ok) {
        let msg = "上传失败";
        try {
            const errorData = await response.json();
            msg = errorData.detail || msg;
        } catch {
            msg = `HTTP ${response.status}`;
        }
        throw new Error(msg);
    }
    
    return await response.json();
}
export async function clearContext() {
  const response = await fetch(`${API_BASE}/clear`, {
      method: "POST"
  });
  if (!response.ok) throw new Error("Failed to clear context");
  return await response.json();
}

/**
 * 流式聊天
 * @param {string} query - 问题
 * @param {string} searchMode - 'hybrid' | 'document'
 * @param {function} onMessage - 接收消息回调
 * @param {function} onDone - 完成回调
 * @param {function} onError - 错误回调
 */
export async function streamChat(query, search_mode, onData, onDone, onError, signal) {
  try {
      const response = await fetch(`${API_BASE}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
              query: query,
              search_mode: search_mode,
              thread_id: SESSION_THREAD_ID
          }),
          signal,
      });
      
      if (!response.ok) {
          let msg = "请求失败";
          try { const d = await response.json(); msg = d.detail || msg; } catch { msg = `HTTP ${response.status}`; }
          throw new Error(msg);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let streamDone = false;

      const processLine = (line) => {
          if (!line.startsWith('data: ')) return;
          const dataStr = line.slice(6).trim();
          if (dataStr === '[DONE]') { streamDone = true; return; }
          try { onData(JSON.parse(dataStr)); } catch(e){}
      };

      while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop();
          for (const line of lines) processLine(line);
      }
      // 处理 buffer 中剩余的数据
      if (buffer.trim()) processLine(buffer.trim());
      onDone();
  } catch (error) {
      if (error.name === 'AbortError') return; // 用户主动取消，不报错
      onError(error);
  }
}

/**
 * 获取 AI HOT 新闻
 */
export async function fetchAihotNews(take = 20, query = null) {
  const params = new URLSearchParams({ mode: 'selected', take });
  if (query) params.set('q', query);
  const response = await fetch(`${API_BASE}/aihot/news?${params}`);
  if (!response.ok) throw new Error('Failed to fetch AI news');
  return await response.json();
}

/**
 * 保存报告到创作目录
 */
export async function saveReport(query, report, watermark = true) {
  const response = await fetch(`${API_BASE}/save-report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, report, watermark })
  });
  if (!response.ok) throw new Error('Failed to save report');
  return await response.json();
}