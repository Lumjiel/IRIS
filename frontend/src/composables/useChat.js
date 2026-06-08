import { ref, nextTick } from 'vue';
import { uploadFiles, streamChat, clearContext, saveReport } from '../services/api';
import { getHistory, saveSession } from '../services/history';
import { getThreadId, setThreadId, newThreadId } from '../services/api';

export function useChat(chatContainer) {
    const query = ref('');
    const messages = ref([]);
    const isLoading = ref(false);
    const currentQuery = ref('');
    const searchMode = ref('hybrid');
    const uploadedFiles = ref([]);
    const history = ref([]);
    const activeHistoryId = ref(null);

    let currentAbortController = null;
    let msgIdCounter = 0;

    const getMsgById = (id) => messages.value.find(m => m.id === id);

    const addMessage = (role, type, content, extra = {}) => {
        const msg = { id: ++msgIdCounter, role, type, content, timestamp: Date.now(), status: 'done', streaming: false, ...extra };
        messages.value.push(msg);
        scrollToBottom();
        return msg;
    };

    const finishStatuses = (msgId) => {
        const msg = getMsgById(msgId);
        if (msg?.statuses) msg.statuses.forEach(s => s.active = false);
    };

    const scrollToBottom = () => {
        nextTick(() => {
            const el = chatContainer?.value || document.querySelector('[data-chat-scroll]');
            if (el) el.scrollTop = el.scrollHeight;
        });
    };

    const handleFileSelect = (e, showToast) => {
        const files = Array.from(e.target.files || []);
        const pdfFiles = files.filter(f => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf'));
        if (pdfFiles.length === 0) {
            showToast('仅支持 PDF 文件', 'error');
            return;
        }
        const MAX_SIZE = 20 * 1024 * 1024;
        const oversized = pdfFiles.find(f => f.size > MAX_SIZE);
        if (oversized) {
            showToast(`文件 ${oversized.name} 超过 20MB 限制`, 'error');
            return;
        }
        uploadedFiles.value = pdfFiles;
        e.target.value = '';
    };

    const sendMessage = async (showToast) => {
        const q = query.value.trim();
        if (!q || isLoading.value) return;

        const fileNames = uploadedFiles.value.length > 0
            ? uploadedFiles.value.map(f => f.name)
            : [];

        addMessage('user', 'text', q, { files: fileNames });
        currentQuery.value = q;
        query.value = '';

        isLoading.value = true;
        activeHistoryId.value = null;
        currentAbortController = new AbortController();

        if (uploadedFiles.value.length > 0) {
            try { await uploadFiles(uploadedFiles.value); } catch (e) {
                addMessage('assistant', 'error', `文件上传失败: ${e.message}`);
                isLoading.value = false; return;
            }
        }

        const actualMode = uploadedFiles.value.length === 0 ? 'hybrid' : searchMode.value;
        uploadedFiles.value = [];

        const sMsg = addMessage('assistant', 'stream', '', {
            statuses: [{ text: '准备中...', active: true }],
            streamText: '',
            active: true,
            rounds: [],  // 研究轨迹：每轮的搜索方向
        });
        let round = 0;

        streamChat(
            q, actualMode,
            (data) => {
                const msg = getMsgById(sMsg.id);
                if (!msg) return;

                if (data.step === 'planner_token') {
                    if (!data.data.final && data.data.token) {
                        msg.streamText += data.data.token;
                        scrollToBottom();
                    }
                    return;
                }
                if (data.step === 'writer_token' || data.step === 'refiner_token') {
                    if (!data.data.final && data.data.token) {
                        msg.streamText += data.data.token;
                        // refiner 首次 token 时显示修订状态
                        if (data.step === 'refiner_token' && !msg._refinerStatusShown) {
                            msg._refinerStatusShown = true;
                            if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                            msg.statuses.push({ text: '正在修订报告...', active: true });
                        }
                        scrollToBottom();
                    }
                    return;
                }

                if (data.step === 'planner') {
                    round++;
                    const plans = data.data.plan || [];
                    const status = {
                        text: `第 ${round} 轮 · 拆解了 ${plans.length} 个搜索方向`,
                        active: true,
                        items: plans,
                    };
                    if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                    msg.statuses.push(status);
                    msg.streamText = '';
                    // 记录研究轨迹
                    msg.rounds.push({ number: round, directions: plans });
                    scrollToBottom();
                }
                else if (data.step === 'researcher') {
                    const results = data.data.search_results || [];
                    const sources = results.map(r => {
                        const m = r.match(/### .+?[（(]([^)）]+)[)）]/) || r.match(/### (.+)/);
                        return m ? m[1].trim() : null;
                    }).filter(Boolean);
                    if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                    msg.statuses.push({
                        text: `检索到 ${sources.length || results.length} 个信息源`,
                        active: true,
                        items: sources.length ? sources : results.map((_, i) => `来源 ${i + 1}`),
                    });
                    msg.streamText = '';
                    scrollToBottom();
                }
                else if (data.step === 'writer') {
                    if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                    msg.statuses.push({ text: '正在撰写报告...', active: true });
                    if (data.data.final_report) msg.streamText = data.data.final_report;
                    scrollToBottom();
                }
                else if (data.step === 'reviewer') {
                    if (data.data.review_status === 'FAIL') {
                        const critique = data.data.critique || '需要补充信息';
                        if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                        msg.statuses.push({
                            text: `第 ${round} 轮审查未通过，启动第 ${round + 1} 轮`,
                            active: true,
                            detail: `审查意见：${critique.slice(0, 100)}${critique.length > 100 ? '...' : ''}`,
                        });
                        msg.streamText = '';
                    } else {
                        if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                        msg.statuses.push({ text: '审查通过，报告完成 ✓', active: false });
                        finishStatuses(sMsg.id);
                        msg.type = 'report';
                        msg.content = msg.streamText || '';
                        msg.active = false;
                    }
                    scrollToBottom();
                }
                else if (data.step === 'refiner') {
                    if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                    msg.statuses.push({ text: '修订完成 ✓', active: false });
                    finishStatuses(sMsg.id);
                    if (data.data.final_report) {
                        msg.type = 'report';
                        msg.content = data.data.final_report;
                        msg.streamText = '';
                        msg.active = false;
                    }
                    scrollToBottom();
                }
                else if (data.step === 'error') {
                    finishStatuses(sMsg.id);
                    msg.type = 'error';
                    msg.content = data.data?.message || '研究过程中发生错误';
                    msg.active = false;
                    scrollToBottom();
                }
            },
            () => {
                isLoading.value = false;
                const msg = getMsgById(sMsg.id);
                if (msg) {
                    finishStatuses(sMsg.id);
                    msg.active = false;
                    if (msg.type === 'stream' && msg.streamText) {
                        msg.type = 'report';
                        msg.content = msg.streamText;
                    } else if (msg.type === 'stream' && !msg.streamText) {
                        msg.type = 'error';
                        msg.content = '未能生成报告，请重试';
                    }
                    if (msg.type === 'report') {
                        msg.streamText = '';
                    }
                }
                const finalReport = msg?.streamText || msg?.content || '';
                if (currentQuery.value) {
                    saveSession({
                        query: currentQuery.value,
                        report: finalReport,
                        mode: actualMode,
                        threadId: getThreadId(),
                        messages: messages.value.map(m => ({
                            role: m.role, type: m.type, content: m.content,
                            statuses: m.statuses, streamText: m.streamText,
                            rounds: m.rounds,
                        })),
                    });
                    history.value = getHistory();
                }
            },
            (err) => {
                isLoading.value = false;
                addMessage('assistant', 'error', `请求失败: ${err?.message || '未知错误'}`);
                if (currentQuery.value) {
                    saveSession({
                        query: currentQuery.value,
                        report: '',
                        mode: actualMode,
                        threadId: getThreadId(),
                        messages: messages.value.map(m => ({
                            role: m.role, type: m.type, content: m.content,
                            statuses: m.statuses, streamText: m.streamText,
                        })),
                    });
                    history.value = getHistory();
                }
            },
            currentAbortController?.signal
        );
    };

    const stopResearch = () => {
        if (currentAbortController) currentAbortController.abort();
        isLoading.value = false;
        // 终结当前流式消息，防止卡在"流式中"状态
        const activeMsg = messages.value.findLast(m => m.type === 'stream' && m.active);
        if (activeMsg) {
            finishStatuses(activeMsg.id);
            activeMsg.statuses.push({ text: '已停止', active: false });
            activeMsg.type = activeMsg.streamText ? 'report' : 'error';
            activeMsg.content = activeMsg.streamText || '研究已停止';
            activeMsg.streamText = '';
            activeMsg.active = false;
            // 保存会话（abort 后 onDone 不会调用）
            if (currentQuery.value) {
                saveSession({
                    query: currentQuery.value,
                    report: activeMsg.content || '',
                    mode: searchMode.value,
                    threadId: getThreadId(),
                    messages: messages.value.map(m => ({
                        role: m.role, type: m.type, content: m.content,
                        statuses: m.statuses, streamText: m.streamText,
                        rounds: m.rounds,
                    })),
                });
                history.value = getHistory();
            }
        }
    };

    const copyReport = async (msg) => {
        try { await navigator.clipboard.writeText(msg.content); } catch {}
    };

    const downloadReport = (msg) => {
        const blob = new Blob([msg.content], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `IRIS-${currentQuery.value || 'report'}.md`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const saveToLibrary = async (msg, showToast) => {
        try {
            await saveReport(currentQuery.value, msg.content);
            showToast('已保存到素材库', 'success');
        } catch { showToast('保存失败', 'error'); }
    };

    const viewHistory = (session) => {
        messages.value = [];
        currentQuery.value = session.query;
        activeHistoryId.value = session.id;
        if (session.threadId) setThreadId(session.threadId);
        if (session.messages && session.messages.length > 0) {
            session.messages.forEach(m => {
                addMessage(m.role, m.type, m.content, {
                    statuses: m.statuses,
                    streamText: m.streamText,
                    rounds: m.rounds || [],
                    active: false,
                });
            });
        } else {
            addMessage('user', 'text', session.query);
            addMessage('assistant', 'report', session.report);
        }
        scrollToBottom();
    };

    const newChat = () => {
        messages.value = [];
        currentQuery.value = '';
        activeHistoryId.value = null;
        if (isLoading.value) stopResearch();
        newThreadId();
        try { clearContext(); } catch {}
    };

    return {
        query, messages, isLoading, currentQuery, searchMode,
        uploadedFiles, history, activeHistoryId,
        addMessage, scrollToBottom, handleFileSelect,
        sendMessage, stopResearch, copyReport, downloadReport,
        saveToLibrary, viewHistory, newChat,
        getHistory, getThreadId,
    };
}
