import { ref, nextTick } from 'vue';
import { uploadFiles, streamChat, clearContext, saveReport, ttsSynthesize, exportPdf } from '../services/api';
import { getHistory, saveSession } from '../services/history';
import { getThreadId, setThreadId, newThreadId } from '../services/api';
import { useStats } from './useStats';

export function useChat(chatContainer) {
    const query = ref('');
    const messages = ref([]);
    const isLoading = ref(false);
    const currentQuery = ref('');
    const searchMode = ref('hybrid');
    const uploadedFiles = ref([]);
    const history = ref([]);
    const activeHistoryId = ref(null);
    const activeSkill = ref('');
    const pendingHitlResponse = ref('');  // 用户点击 HITL 按钮后待发送的决策

    const { stats, avgTime, recordResearch } = useStats();
    let currentAbortController = null;
    let msgIdCounter = 0;
    let streamStartTime = 0;

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
        streamStartTime = Date.now();

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
            currentPhase: 0,  // 研究进度阶段：0=准备 1=搜索 2=分析 3=撰写 4=完成
            intent: '', intentConfidence: null, entities: [], toolTrace: [],
        });
        let round = 0;

        streamChat(
            q, actualMode,
            (data) => {
                const msg = getMsgById(sMsg.id);
                if (!msg) return;

                // 意图识别结果（router 节点）
                if (data.step === 'router') {
                    msg.intent = data.data.intent || '';
                    msg.intentConfidence = data.data.intent_confidence ?? null;
                    msg.entities = data.data.entities || [];
                    if (data.data.active_skill) activeSkill.value = data.data.active_skill;
                    return;
                }

                // ReAct 工具调用轨迹
                if (data.step === 'tool_call') {
                    if (data.data.tool_call_request) {
                        const t = data.data.tool_call_request;
                        msg.toolTrace.push({ tool: t.tool, arguments: t.arguments, status: 'calling' });
                        if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                        msg.statuses.push({ text: `正在调用工具 ${t.tool}...`, active: true });
                        msg.currentPhase = 2;
                    } else {
                        if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                        msg.statuses.push({ text: '工具结果已整合，生成回答 ✓', active: false });
                        finishStatuses(sMsg.id);
                        msg.type = 'report';
                        msg.content = msg.streamText || data.data.final_report || '';
                        msg.active = false;
                    }
                    return;
                }
                if (data.step === 'tool_execute') {
                    const last = msg.toolTrace[msg.toolTrace.length - 1];
                    if (last) { last.status = 'done'; }
                    return;
                }

                // 意图澄清（clarify）
                if (data.step === 'clarify_token') {
                    if (!data.data.final && data.data.token) {
                        msg.streamText += data.data.token;
                        scrollToBottom();
                    }
                    return;
                }
                if (data.step === 'clarify') {
                    finishStatuses(sMsg.id);
                    msg.type = 'clarify';
                    msg.content = msg.streamText || data.data.clarify_question || '';
                    msg.active = false;
                    return;
                }

                // 汇总节点
                if (data.step === 'synthesize') {
                    if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                    msg.statuses.push({ text: '正在汇总检索结果...', active: true });
                    return;
                }

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
                    msg.currentPhase = 1;
                    const plans = data.data.plan || [];
                    const subtasks = data.data.plan_structure || [];
                    const status = {
                        text: `第 ${round} 轮 · 拆解了 ${plans.length} 个搜索方向`,
                        active: true,
                        items: plans,
                        subtasks: subtasks,
                    };
                    if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                    msg.statuses.push(status);
                    // 记录子任务（供卡片展示）
                    msg.subtasks = subtasks;
                    msg.streamText = '';
                    // 记录研究轨迹
                    msg.rounds.push({ number: round, directions: plans });
                    scrollToBottom();
                }
                else if (data.step === 'researcher') {
                    msg.currentPhase = 2;
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
                    msg.currentPhase = 3;
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
                            text: `第 ${round} 轮审查未通过，等待你的决定`,
                            active: true,
                            detail: `审查意见：${critique.slice(0, 100)}${critique.length > 100 ? '...' : ''}`,
                        });
                        msg.streamText = '';
                    } else {
                        if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                        msg.statuses.push({ text: '审查通过，报告完成 ✓', active: false });
                        finishStatuses(sMsg.id);
                        msg.currentPhase = 4;
                        msg.type = 'report';
                        msg.content = msg.streamText || '';
                        msg.active = false;
                    }
                    scrollToBottom();
                }
                else if (data.step === 'hitl_token') {
                    if (!data.data.final && data.data.token) {
                        msg.hitlText = (msg.hitlText || '') + data.data.token;
                    }
                    return;
                }
                else if (data.step === 'hitl_gate') {
                    finishStatuses(sMsg.id);
                    msg.hitl = { question: data.data.hitl_question || msg.hitlText || '报告未通过审查' };
                    msg.active = false;
                    msg._hitlPending = true;
                    return;
                }

                else if (data.step === 'refiner') {
                    msg.currentPhase = 4;
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
                // 跟踪激活的 Skill
                if (data.data?.active_skill !== undefined) {
                    activeSkill.value = data.data.active_skill || '';
                }
            },
            () => {
                isLoading.value = false;
                const durationSeconds = Math.round((Date.now() - streamStartTime) / 1000);
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
                if (msg?.type === 'report' && finalReport) {
                    const sourceMatches = finalReport.match(/\[\d+\]/g);
                    recordResearch(durationSeconds, sourceMatches ? sourceMatches.length : 0);
                }
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
            currentAbortController?.signal,
            activeSkill.value,
            pendingHitlResponse.value,
        );
        pendingHitlResponse.value = '';
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

    const downloadPdf = async (msg) => {
        try {
            const blob = await exportPdf(msg.content, currentQuery.value || 'report');
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `IRIS-${currentQuery.value || 'report'}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            console.error('PDF export failed:', e);
        }
    };

    const saveToLibrary = async (msg, showToast) => {
        try {
            await saveReport(currentQuery.value, msg.content);
            showToast('已保存到素材库', 'success');
        } catch { showToast('保存失败', 'error'); }
    };

    // TTS 朗读
    let _currentAudio = null;
    const ttsReport = async (msg) => {
        // 如果正在播放，停止
        if (msg._ttsPlaying && _currentAudio) {
            _currentAudio.pause();
            _currentAudio = null;
            msg._ttsPlaying = false;
            return;
        }
        // 停止其他正在播放的
        if (_currentAudio) {
            _currentAudio.pause();
            _currentAudio = null;
            messages.value.forEach(m => { if (m._ttsPlaying) m._ttsPlaying = false; });
        }
        try {
            msg._ttsPlaying = true;
            // 截取前 3000 字（TTS 有长度限制）
            const text = msg.content.substring(0, 3000);
            const blob = await ttsSynthesize(text);
            const url = URL.createObjectURL(blob);
            _currentAudio = new Audio(url);
            _currentAudio.onended = () => {
                msg._ttsPlaying = false;
                _currentAudio = null;
                URL.revokeObjectURL(url);
            };
            _currentAudio.onerror = () => {
                msg._ttsPlaying = false;
                _currentAudio = null;
                URL.revokeObjectURL(url);
            };
            _currentAudio.play();
        } catch (e) {
            msg._ttsPlaying = false;
            console.error('TTS failed:', e);
        }
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
        activeSkill.value = '';
        pendingHitlResponse.value = '';
        if (isLoading.value) stopResearch();
        newThreadId();
        try { clearContext(); } catch {}
    };

    const clearSkill = () => { activeSkill.value = ''; };

    const sendHitlChoice = (choice) => {
        pendingHitlResponse.value = choice;
        query.value = choice;
        sendMessage(() => {});
    };

    return {
        query, messages, isLoading, currentQuery, searchMode,
        uploadedFiles, history, activeHistoryId, activeSkill,
        stats, avgTime,
        addMessage, scrollToBottom, handleFileSelect,
        sendMessage, stopResearch, copyReport, downloadReport, downloadPdf,
        saveToLibrary, ttsReport, viewHistory, newChat, clearSkill, sendHitlChoice,
        getHistory, getThreadId,
    };
}
