<template>
    <transition name="slide-down">
        <div v-if="showWarning" class="fixed top-24 left-1/2 transform -translate-x-1/2 z-50 px-6 py-3 rounded-full shadow-lg flex items-center gap-3 transition-colors duration-300"
            :class="{
                'bg-amber-50 border border-amber-200 text-amber-800': toastType === 'warning',
                'bg-red-50 border border-red-200 text-red-800': toastType === 'error',
                'bg-green-50 border border-green-200 text-green-800': toastType === 'success'
            }"
        >
            <svg v-if="toastType === 'warning'" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-amber-500" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
            <svg v-else-if="toastType === 'error'" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-green-500" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
            <span class="text-sm font-medium">{{ warningMessage }}</span>
            <button @click="showWarning = false" class="hover:opacity-70 transition-opacity">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>
            </button>
        </div>
    </transition>
  <div class="min-h-screen bg-gray-50 text-gray-900 font-sans relative overflow-x-hidden selection:bg-blue-100 selection:text-blue-900">
    
    <div class="fixed top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
        <div class="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-300/30 rounded-full blur-[120px] mix-blend-multiply animate-blob"></div>
        <div class="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-300/30 rounded-full blur-[120px] mix-blend-multiply animate-blob animation-delay-2000"></div>
        <div class="absolute bottom-[-20%] left-[20%] w-[40%] h-[40%] bg-indigo-300/30 rounded-full blur-[120px] mix-blend-multiply animate-blob animation-delay-4000"></div>
    </div>

    <header class="sticky top-0 z-50 border-b border-white/20 bg-white/70 backdrop-blur-xl">
      <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="relative w-10 h-10 flex items-center justify-center bg-gradient-to-tr from-blue-600 to-purple-600 rounded-xl shadow-lg shadow-blue-500/20 text-white">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
          </div>
          <div class="flex flex-col">
            <h1 class="text-2xl font-black tracking-tighter bg-gradient-to-r from-blue-700 via-purple-600 to-indigo-600 bg-clip-text text-transparent" style="font-family: 'Orbitron', sans-serif;">
              IRIS
            </h1>
            <span class="text-[10px] font-semibold text-gray-500 tracking-[0.05em] uppercase -mt-1">
              智能调研洞察系统
            </span>
          </div>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto p-6 lg:p-8 grid grid-cols-1 lg:grid-cols-12 gap-8 mt-4">
      
      <div class="lg:col-span-4 space-y-4">

        <!-- 输入区（常驻） -->
        <div class="bg-white/80 backdrop-blur-xl p-5 rounded-2xl shadow-xl border border-white/40 space-y-4">
            <div>
                <div class="relative group">
                    <div class="absolute -inset-0.5 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl opacity-20 group-hover:opacity-40 transition duration-500 blur"></div>
                    <textarea
                    v-model="query"
                    class="relative w-full p-4 bg-white border-0 rounded-xl shadow-inner text-gray-700 placeholder-gray-400 focus:ring-0 text-sm leading-relaxed resize-none transition-all"
                    rows="3"
                    placeholder="输入研究主题，Ctrl+Enter 快速开始..."
                    :disabled="isLoading"
                    ></textarea>
                </div>

                <button
                    v-if="isLoading"
                    @click="stopResearch"
                    class="mt-3 w-full rounded-xl bg-red-500/90 hover:bg-red-600 px-8 py-3 text-white shadow-lg transition-all hover:shadow-xl"
                >
                    <span class="flex items-center justify-center gap-2 font-medium tracking-wide text-xs">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
                        停止研究
                    </span>
                </button>
                <button
                    v-else
                    @click="startResearch"
                    :disabled="!query"
                    class="mt-3 w-full group relative overflow-hidden rounded-xl bg-gray-900 px-8 py-3 text-white shadow-lg transition-all hover:bg-gray-800 hover:shadow-xl hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none disabled:translate-y-0"
                >
                    <div class="absolute inset-0 bg-gradient-to-r from-blue-600 to-purple-600 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                    <span class="relative flex items-center justify-center gap-2 font-medium tracking-wide text-xs">
                        开始调研
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
                    </span>
                </button>
            </div>
        </div>

        <!-- Tab 切换面板 -->
        <div class="bg-white/80 backdrop-blur-xl rounded-2xl shadow-xl border border-white/40 overflow-hidden">
            <!-- Tab 栏 -->
            <div class="flex border-b border-gray-100">
                <button
                    v-for="tab in sidebarTabs"
                    :key="tab.key"
                    @click="activeSidebarTab = tab.key"
                    class="flex-1 py-2.5 text-[11px] font-bold tracking-wide transition-all duration-200 relative"
                    :class="activeSidebarTab === tab.key ? 'text-blue-600' : 'text-gray-400 hover:text-gray-600'"
                >
                    {{ tab.label }}
                    <div v-if="activeSidebarTab === tab.key" class="absolute bottom-0 left-1/4 right-1/4 h-0.5 bg-blue-500 rounded-full"></div>
                </button>
            </div>

            <!-- Tab 内容 -->
            <div class="max-h-64 overflow-y-auto">
                <!-- 知识库 -->
                <div v-if="activeSidebarTab === 'kb'" class="p-4 space-y-3">
                    <div class="flex items-center justify-between">
                        <span class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">PDF 文档</span>
                        <span class="text-[10px] text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">最多 5 个</span>
                    </div>
                    <div
                        @dragover.prevent="isDragging = true"
                        @dragleave.prevent="isDragging = false"
                        @drop.prevent="handleDrop"
                        class="relative group cursor-pointer border-2 border-dashed rounded-xl p-3 transition-all duration-300 flex flex-col items-center justify-center text-center min-h-[80px]"
                        :class="isDragging ? 'border-blue-500 bg-blue-50/50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50/50'"
                    >
                        <input type="file" multiple accept=".pdf" class="absolute inset-0 opacity-0 cursor-pointer" @change="handleFileSelect" />
                        <div v-if="uploadedFiles.length === 0" class="pointer-events-none flex flex-col items-center">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-blue-400 mb-1"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                            <p class="text-[11px] text-gray-500">拖拽 PDF 到此处</p>
                        </div>
                        <div v-else class="w-full space-y-1.5 pointer-events-none z-10">
                            <div v-for="(file, i) in uploadedFiles" :key="i" class="flex items-center justify-between bg-white px-2.5 py-1.5 rounded-lg shadow-sm border border-gray-100 text-[11px]">
                                <span class="truncate max-w-[140px] text-gray-700 font-medium">{{ file.name }}</span>
                                <svg class="w-3.5 h-3.5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                            </div>
                        </div>
                    </div>
                    <!-- 搜索模式 -->
                    <div class="bg-gray-100/80 p-0.5 rounded-lg flex items-center relative">
                        <div class="absolute top-0.5 bottom-0.5 w-[48%] bg-white rounded-md shadow-sm transition-all duration-300 ease-out z-0" :class="searchMode === 'document' ? 'left-0.5' : 'left-[51%]'"></div>
                        <button @click="setMode('document')" :disabled="uploadedFiles.length === 0" class="flex-1 py-1.5 text-[10px] font-bold tracking-wide rounded-md z-10 transition-colors duration-300 flex items-center justify-center gap-1" :class="searchMode === 'document' ? 'text-blue-600' : 'text-gray-400'">
                            仅文档
                        </button>
                        <button @click="setMode('hybrid')" class="flex-1 py-1.5 text-[10px] font-bold tracking-wide rounded-md z-10 transition-colors duration-300 flex items-center justify-center gap-1" :class="searchMode === 'hybrid' ? 'text-purple-600' : 'text-gray-400'">
                            混合模式
                        </button>
                    </div>
                </div>

                <!-- AI 灵感 -->
                <div v-if="activeSidebarTab === 'ai'" class="">
                    <div class="flex gap-1 px-3 pt-3 overflow-x-auto scrollbar-none">
                        <button v-for="cat in aiNewsCategories" :key="cat.key" @click="aiNewsCategory = cat.key; loadAiNews()" class="shrink-0 px-2 py-0.5 rounded-full text-[10px] font-medium transition-all duration-200" :class="aiNewsCategory === cat.key ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'">
                            {{ cat.label }}
                        </button>
                    </div>
                    <div v-if="aiNewsLoading && aiNews.length === 0" class="p-4 text-center text-[11px] text-gray-400">加载中...</div>
                    <div v-else-if="aiNews.length === 0" class="p-4 text-center text-[11px] text-gray-400">暂无资讯</div>
                    <div v-for="item in aiNews" :key="item.id" @click="useAiNewsTitle(item.title)" class="px-4 py-2 border-b border-gray-50 cursor-pointer hover:bg-blue-50/50 transition-colors group">
                        <div class="flex items-start justify-between gap-2">
                            <p class="text-[11px] font-medium text-gray-700 leading-relaxed line-clamp-2 group-hover:text-blue-600">{{ item.title }}</p>
                            <span class="shrink-0 text-[9px] text-gray-400 mt-0.5">{{ formatAiTime(item.publishedAt) }}</span>
                        </div>
                        <p class="text-[9px] text-gray-400 mt-0.5">{{ item.source }}</p>
                    </div>
                </div>

                <!-- 历史 -->
                <div v-if="activeSidebarTab === 'history'">
                    <div v-if="history.length === 0" class="p-4 text-center text-[11px] text-gray-400">暂无历史记录</div>
                    <div v-for="session in history" :key="session.id" @click="viewHistory(session)" class="flex items-center gap-2 px-4 py-2 cursor-pointer transition-all duration-200 border-b border-gray-50" :class="activeHistoryId === session.id ? 'bg-blue-50/80' : 'hover:bg-gray-50/80'">
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-1.5">
                                <p class="text-[11px] font-medium text-gray-700 truncate">{{ session.query }}</p>
                                <span v-if="session.usedAt" class="shrink-0 text-[9px] bg-green-100 text-green-600 px-1.5 py-0.5 rounded-full font-medium">已用</span>
                            </div>
                            <p class="text-[9px] text-gray-400 mt-0.5">{{ formatTime(session.timestamp) }}</p>
                        </div>
                        <div class="flex items-center gap-0.5">
                            <button @click="toggleUsed(session.id, $event)" class="p-1 text-gray-300 hover:text-green-500 transition-colors rounded" :title="session.usedAt ? '已用于文章' : '标记为已用于文章'">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" /></svg>
                            </button>
                            <button @click="removeHistory(session.id, $event)" class="p-1 text-gray-300 hover:text-red-400 transition-colors rounded">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <StatusFlow :currentStep="currentStep" :startTime="researchStartTime" />

        <!-- 终端日志（可折叠） -->
        <div class="rounded-2xl bg-[#0F172A] border border-slate-800 shadow-2xl overflow-hidden ring-1 ring-white/10">
            <div @click="logCollapsed = !logCollapsed" class="flex items-center gap-1.5 px-4 py-2 bg-slate-900/50 border-b border-slate-800 cursor-pointer">
                <div class="w-2 h-2 rounded-full bg-red-500/80"></div>
                <div class="w-2 h-2 rounded-full bg-yellow-500/80"></div>
                <div class="w-2 h-2 rounded-full bg-green-500/80"></div>
                <span class="ml-2 text-[10px] font-mono text-slate-500">iris@core:~</span>
                <span class="ml-1 text-[9px] text-slate-600">{{ logs.length }} 条</span>
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 ml-auto text-slate-500 transition-transform duration-200" :class="logCollapsed ? '-rotate-90' : ''" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>
            </div>
            <div v-show="!logCollapsed" ref="logsContainer" class="h-28 p-3 overflow-y-auto font-mono text-[10px] leading-4 space-y-0.5 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
                <div v-if="logs.length === 0" class="text-slate-600 italic">等待输入...</div>
                <div v-for="(log, i) in logs" :key="i" class="flex gap-1.5">
                    <span class="text-blue-500 shrink-0">›</span>
                    <span class="text-slate-400 break-all">{{ log }}</span>
                </div>
                <div v-if="isLoading" class="animate-pulse text-blue-500 mt-1">_</div>
            </div>
        </div>
      </div>

      <div class="lg:col-span-8 flex flex-col h-full min-h-[400px] lg:min-h-[700px]">
        <div class="flex-1 bg-white/80 backdrop-blur-xl rounded-2xl shadow-xl border border-white/40 p-8 lg:p-12 relative overflow-hidden flex flex-col">
            
            <div class="absolute top-0 right-0 p-8 opacity-[0.03] pointer-events-none">
                 <h1 class="text-9xl font-black font-sans" style="font-family: 'Orbitron';">IRIS</h1>
            </div>

            <div v-if="!displayedReport && !isLoading" class="flex-1 flex flex-col items-center justify-center text-gray-400 space-y-4">
                <div class="w-20 h-20 rounded-3xl bg-gradient-to-tr from-blue-100 to-purple-100 flex items-center justify-center shadow-inner">
                    <svg class="w-10 h-10 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path></svg>
                </div>
                <div class="text-center space-y-2">
                    <h3 class="text-lg font-medium text-gray-900">开始你的深度调研</h3>
                    <p class="text-sm text-gray-500 max-w-xs">输入一个研究主题，IRIS 会自动规划搜索策略、多源采集信息、撰写结构化报告</p>
                    <p class="text-[10px] text-gray-400 mt-3">Ctrl + Enter 快速开始</p>
                </div>
            </div>

            <div v-else-if="isLoading && !displayedReport" class="flex-1 flex flex-col items-center justify-center relative">
                <div class="relative w-40 h-40 flex items-center justify-center">
                    <div class="absolute inset-0 bg-gradient-to-tr from-blue-500 to-purple-600 rounded-full blur-[60px] opacity-60 animate-pulse"></div>

                    <div class="absolute top-0 -left-4 w-24 h-24 bg-cyan-400 rounded-full blur-[40px] opacity-50 mix-blend-screen animate-blob"></div>
                    <div class="absolute -bottom-4 -right-4 w-24 h-24 bg-indigo-500 rounded-full blur-[40px] opacity-50 mix-blend-screen animate-blob animation-delay-2000"></div>
                    <div class="absolute -bottom-8 left-8 w-20 h-20 bg-purple-400 rounded-full blur-[40px] opacity-50 mix-blend-screen animate-blob animation-delay-4000"></div>

                    <div class="relative z-10 w-3 h-3 bg-white rounded-full shadow-[0_0_20px_rgba(255,255,255,0.8)] animate-ping" style="animation-duration: 2s;"></div>
                </div>

                <div class="mt-12 text-center space-y-2 relative z-10">
                    <h3 class="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-purple-600 tracking-widest animate-pulse">
                        思考中
                    </h3>
                    <p class="text-xs text-slate-400 font-mono uppercase tracking-[0.2em]">
                        分析问题 & 规划策略...
                    </p>
                </div>

                <!-- 骨架屏占位 -->
                <div class="absolute bottom-0 left-0 right-0 p-8 space-y-3 opacity-40">
                    <div class="h-4 bg-gray-200 rounded-full w-3/4 animate-pulse"></div>
                    <div class="h-3 bg-gray-200 rounded-full w-full animate-pulse" style="animation-delay: 0.1s"></div>
                    <div class="h-3 bg-gray-200 rounded-full w-5/6 animate-pulse" style="animation-delay: 0.2s"></div>
                    <div class="h-3 bg-gray-200 rounded-full w-2/3 animate-pulse" style="animation-delay: 0.3s"></div>
                </div>
            </div>

            <div v-else class="prose prose-slate max-w-none prose-headings:font-display prose-headings:font-bold prose-headings:tracking-tight prose-a:text-blue-600 prose-img:rounded-xl relative">
                <!-- TOC 目录按钮 -->
                <button
                    v-if="reportToc.length > 2"
                    @click="tocVisible = !tocVisible"
                    class="absolute top-4 left-4 z-10 flex items-center gap-1.5 px-3 py-1.5 bg-white/80 backdrop-blur-sm rounded-lg text-xs font-medium text-gray-600 hover:text-blue-600 hover:bg-blue-50/80 border border-gray-200/60 shadow-sm transition-all duration-200"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
                    目录
                </button>

                <!-- TOC 浮动面板 -->
                <div
                    v-if="tocVisible && reportToc.length > 2"
                    class="absolute top-14 left-4 z-10 w-56 bg-white/95 backdrop-blur-xl rounded-xl shadow-xl border border-gray-200/60 overflow-hidden"
                >
                    <div class="px-3 py-2 border-b border-gray-100 flex items-center justify-between">
                        <span class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">目录</span>
                        <button @click="tocVisible = false" class="text-gray-400 hover:text-gray-600">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>
                        </button>
                    </div>
                    <nav class="max-h-64 overflow-y-auto py-1">
                        <button
                            v-for="h in reportToc"
                            :key="h.id"
                            @click="scrollToHeading(h.id); tocVisible = false"
                            class="block w-full text-left px-3 py-1.5 text-xs text-gray-600 hover:text-blue-600 hover:bg-blue-50/50 transition-colors truncate"
                            :style="{ paddingLeft: (h.level - 1) * 12 + 12 + 'px' }"
                        >
                            {{ h.title }}
                        </button>
                    </nav>
                </div>

                <!-- 导出工具栏 -->
                <div class="absolute top-4 right-4 flex gap-2 z-20">
                    <div class="relative">
                        <button
                            @click="showCopyMenu = !showCopyMenu"
                            class="flex items-center gap-1.5 px-3 py-1.5 bg-white/80 backdrop-blur-sm rounded-lg text-xs font-medium text-gray-600 hover:text-blue-600 hover:bg-blue-50/80 border border-gray-200/60 shadow-sm transition-all duration-200"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                            {{ copyLabel }}
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-2.5 w-2.5 text-gray-400" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>
                        </button>
                        <div v-if="showCopyMenu" class="absolute top-full right-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
                            <button @click="copyFormat = 'md'; copyMarkdown()" class="block w-full text-left px-4 py-2 text-xs text-gray-700 hover:bg-blue-50 transition-colors whitespace-nowrap">
                                复制 Markdown
                            </button>
                            <button @click="copyFormat = 'html'; copyMarkdown()" class="block w-full text-left px-4 py-2 text-xs text-gray-700 hover:bg-blue-50 transition-colors whitespace-nowrap">
                                复制 HTML
                            </button>
                        </div>
                    </div>
                    <button
                        @click="downloadMarkdown"
                        class="flex items-center gap-1.5 px-3 py-1.5 bg-white/80 backdrop-blur-sm rounded-lg text-xs font-medium text-gray-600 hover:text-purple-600 hover:bg-purple-50/80 border border-gray-200/60 shadow-sm transition-all duration-200"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        下载
                    </button>
                    <button
                        @click="saveToLibrary"
                        class="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-blue-500/90 to-purple-500/90 backdrop-blur-sm rounded-lg text-xs font-medium text-white shadow-sm transition-all duration-200 hover:shadow-md"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                        {{ saveLabel }}
                    </button>
                </div>
                <div v-html="renderedReport"></div>
                <span v-if="isTyping" class="inline-block w-2 h-5 bg-blue-600 ml-1 animate-pulse align-middle"></span>
            </div>

        </div>
      </div>

    </main>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue';
import { uploadFiles, streamChat, clearContext, fetchAihotNews, saveReport } from './services/api';
import { getHistory, saveSession, deleteSession, clearHistory, markAsUsed } from './services/history';
import StatusFlow from './components/StatusFlow.vue';
import MarkdownIt from 'markdown-it';
// 【修复步骤 1】引入数学公式插件 (必须先 npm install markdown-it-katex)
import mk from 'markdown-it-katex';

// 【修复步骤 2】挂载插件
const md = new MarkdownIt({
    html: true,
    linkify: true,
    typographer: true
});
md.use(mk);

// 给标题加 ID，支持 TOC 跳转
md.renderer.rules.heading_open = (tokens, idx) => {
    const token = tokens[idx];
    const content = tokens[idx + 1].content;
    const id = content.replace(/[^\w一-鿿]/g, '-').toLowerCase();
    return `<${token.tag} id="${id}">`;
};
const showWarning = ref(false);
const warningMessage = ref('');
const toastType = ref('warning');
let toastTimer = null;

const showToast = (msg, type = 'warning') => {
    if (toastTimer) clearTimeout(toastTimer);
    warningMessage.value = msg;
    toastType.value = type;
    showWarning.value = true;
    toastTimer = setTimeout(() => {
        showWarning.value = false;
    }, 4000);
};


// 状态变量
const query = ref('');
const isLoading = ref(false);
const currentStep = ref('idle'); 
const logs = ref([]);
const logsContainer = ref(null);
const uploadedFiles = ref([]); 
const isDragging = ref(false);
const searchMode = ref('hybrid'); 

// 打字机变量
const displayedReport = ref('');
const isTyping = ref(false);
const rawReportSource = ref('');
const displayedLength = ref(0);
let typingInterval = null;

// TOC 目录
const tocVisible = ref(false);
const reportToc = computed(() => {
    const text = rawReportSource.value || '';
    const headings = [];
    const lines = text.split('\n');
    for (const line of lines) {
        const match = line.match(/^(#{1,3})\s+(.+)/);
        if (match) {
            const level = match[1].length;
            const title = match[2].trim();
            const id = title.replace(/[^\w一-鿿]/g, '-').toLowerCase();
            headings.push({ level, title, id });
        }
    }
    return headings;
});

const scrollToHeading = (id) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

// 研究历史
const history = ref([]);
const activeHistoryId = ref(null);

// AI 灵感面板
const aiNews = ref([]);
const aiNewsLoading = ref(false);
const aiNewsQuery = ref('');
const logCollapsed = ref(false);

// 左侧栏 Tab
const activeSidebarTab = ref('ai');
const sidebarTabs = [
    { key: 'kb', label: '知识库' },
    { key: 'ai', label: 'AI 灵感' },
    { key: 'history', label: '历史' },
];

// 保存报告
const saveLabel = ref('保存到素材库');
const watermarkEnabled = ref(true);

onMounted(() => {
    history.value = getHistory();
    loadAiNews();
    // 全局快捷键
    document.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
    document.removeEventListener('keydown', handleKeydown);
});

const handleKeydown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        if (!isLoading.value && query.value) startResearch();
    }
};

// 【修复步骤 3】增强渲染逻辑：把后端返回的 \[...\] 替换成插件能识别的 $$...$$
const renderedReport = computed(() => {
    // 打字机模式：从源文本截取已显示部分
    const fullText = rawReportSource.value || displayedReport.value || '';
    const text = isTyping.value ? fullText.substring(0, displayedLength.value) : fullText;

    let raw = text;

    // 1. 预处理：修复 LaTeX 定界符
    raw = raw.replace(/\\\[/g, '$$$').replace(/\\\]/g, '$$$');
    raw = raw.replace(/\\\(/g, '$').replace(/\\\)/g, '$');

    // 2. 额外补丁：有些模型会输出不带反斜杠的 [ formula ]
    raw = raw.replace(/\[\s*(\\text|\\frac|\\sum|\\int)/g, '$$$$ $1');

    // 3. 渲染
    return md.render(raw);
});

const scrollToBottom = async () => {
    await nextTick();
    if (logsContainer.value) logsContainer.value.scrollTop = logsContainer.value.scrollHeight;
};

// --- 文件处理逻辑 ---
const handleFileSelect = async (event) => {
    processFiles(event.target.files);
};

const handleDrop = async (event) => {
    isDragging.value = false;
    processFiles(event.dataTransfer.files);
};

const processFiles = async (files) => {
    if (files.length > 5) {
        showToast("最多只能上传 5 个文件", 'error');
        return;
    }
    
    uploadedFiles.value = Array.from(files);
    
    if (uploadedFiles.value.length > 0) {
        logs.value.push(`[系统] 正在上传 ${files.length} 个文档...`);
        try {
            const res = await uploadFiles(uploadedFiles.value);
            logs.value.push(`[系统] 知识库构建完成，共 ${res.chunks_stored} 个片段`);
            showToast(`知识库构建完成，共 ${res.chunks_stored} 个片段`, 'success');
        } catch (e) {
            logs.value.push(`[错误] 上传失败: ${e.message}`);
            showToast("上传失败: " + e.message, 'error');
            uploadedFiles.value = []; 
        }
    }
};

const setMode = (mode) => {
    searchMode.value = mode;
};

const typeWriterEffect = (text) => {
    isTyping.value = true;
    rawReportSource.value = text;
    displayedReport.value = ''; // 兼容旧引用
    displayedLength.value = 0;

    if (typingInterval) clearInterval(typingInterval);

    const BATCH_SIZE = 20;
    const INTERVAL = 30; // ms

    typingInterval = setInterval(() => {
        if (displayedLength.value < text.length) {
            displayedLength.value = Math.min(displayedLength.value + BATCH_SIZE, text.length);
        } else {
            clearInterval(typingInterval);
            typingInterval = null;
            isTyping.value = false;
        }
    }, INTERVAL);
};

// --- 历史管理 ---
const viewHistory = (session) => {
    if (isLoading.value) return;
    if (typingInterval) clearInterval(typingInterval);
    isTyping.value = false;
    activeHistoryId.value = session.id;
    rawReportSource.value = session.report;
    displayedLength.value = session.report.length;
    displayedReport.value = session.report;
    query.value = session.query;
    currentStep.value = 'done';
    logs.value = [`[历史] 加载: ${session.query}`];
};

const toggleUsed = (id, event) => {
    event.stopPropagation();
    markAsUsed(id);
    history.value = getHistory();
};

const removeHistory = (id, event) => {
    event.stopPropagation();
    deleteSession(id);
    history.value = getHistory();
    if (activeHistoryId.value === id) {
        activeHistoryId.value = null;
        displayedReport.value = '';
        currentStep.value = 'idle';
    }
};

const doClearHistory = () => {
    clearHistory();
    history.value = [];
    activeHistoryId.value = null;
};

const formatTime = (timestamp) => {
    const d = new Date(timestamp);
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
};

const aiNewsCategory = ref('');
const aiNewsCategories = [
    { key: '', label: '全部' },
    { key: 'ai-models', label: '模型' },
    { key: 'ai-products', label: '产品' },
    { key: 'industry', label: '行业' },
    { key: 'paper', label: '论文' },
    { key: 'tip', label: '技巧' },
];

const loadAiNews = async () => {
    aiNewsLoading.value = true;
    try {
        const data = await fetchAihotNews(20, aiNewsQuery.value || null);
        let items = data.items || [];
        if (aiNewsCategory.value) {
            items = items.filter(i => i.category === aiNewsCategory.value);
        }
        aiNews.value = items;
    } catch {
        aiNews.value = [];
    } finally {
        aiNewsLoading.value = false;
    }
};

const useAiNewsTitle = (title) => {
    query.value = title;
};

const formatAiTime = (iso) => {
    if (!iso) return '';
    const d = new Date(iso);
    const now = new Date();
    const diff = now - d;
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    return `${d.getMonth() + 1}/${d.getDate()}`;
};

const saveToLibrary = async () => {
    if (!displayedReport.value || !query.value) return;
    saveLabel.value = '保存中...';
    try {
        await saveReport(query.value, displayedReport.value, watermarkEnabled.value);
        saveLabel.value = '已保存 ✓';
        showToast('报告已保存到素材库', 'success');
        setTimeout(() => { saveLabel.value = '保存到素材库'; }, 2000);
    } catch {
        saveLabel.value = '保存失败';
        showToast('保存失败，请重试', 'error');
        setTimeout(() => { saveLabel.value = '保存到素材库'; }, 2000);
    }
};

// --- 导出功能 ---
const copyLabel = ref('复制');
const copyFormat = ref('md'); // 'md' or 'html'
const showCopyMenu = ref(false);

const copyMarkdown = async () => {
    if (!displayedReport.value) return;
    try {
        const text = copyFormat.value === 'html' ? renderedReport.value : displayedReport.value;
        await navigator.clipboard.writeText(text);
        copyLabel.value = copyFormat.value === 'html' ? '已复制 HTML!' : '已复制!';
        setTimeout(() => { copyLabel.value = '复制'; }, 2000);
        showCopyMenu.value = false;
    } catch {
        copyLabel.value = '失败';
        setTimeout(() => { copyLabel.value = '复制'; }, 2000);
    }
};

const downloadMarkdown = () => {
    if (!displayedReport.value) return;
    const blob = new Blob([displayedReport.value], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `IRIS-${query.value || 'report'}.md`;
    a.click();
    URL.revokeObjectURL(url);
};

// --- 开始/停止研究 ---
let currentAbortController = null;
const researchStartTime = ref(0);

const stopResearch = () => {
    if (currentAbortController) {
        currentAbortController.abort();
        currentAbortController = null;
    }
    isLoading.value = false;
    currentStep.value = 'idle';
    showToast("研究已停止", 'warning');
};

const startResearch = async () => {
    if (!query.value) return;

    isLoading.value = true;
    currentStep.value = 'planner';
    logs.value = [];
    logs.value.push(`[初始化] 系统就绪 | 模式: ${searchMode.value === 'hybrid' ? '混合搜索' : '仅文档'}`);
    displayedReport.value = '';
    activeHistoryId.value = null;

    // 创建 AbortController
    currentAbortController = new AbortController();
    researchStartTime.value = Date.now();
    const actualMode = uploadedFiles.value.length === 0 ? 'hybrid' : searchMode.value;

    try {
        if (uploadedFiles.value.length > 0) {
            logs.value.push(`[系统] 正在上传 ${uploadedFiles.value.length} 个文档...`);
            const res = await uploadFiles(uploadedFiles.value);
            logs.value.push(`[系统] 知识库构建完成，共 ${res.chunks_stored} 个片段`);
            showToast(`知识库构建完成，共 ${res.chunks_stored} 个片段`, 'success');
        } else {
            logs.value.push(`[系统] 正在清空知识库...`);
            await clearContext();
            logs.value.push(`[系统] 知识库已清空，纯网络搜索模式`);
        }

        streamChat(
            query.value,
            actualMode,
            (data) => {
                    // 1. 同步后端当前步骤
                    if (data.step) currentStep.value = data.step;

                    // --- 步骤 1: 规划 (Planner) ---
                    if (data.step === 'planner') {
                        currentStep.value = 'researcher'; // 视觉上跳到下一步
                        logs.value.push(`[规划] 搜索策略: [${data.data.plan.join(', ')}]`);
                    }

                    // --- 步骤 2: 搜索 (Researcher) ---
                    else if (data.step === 'researcher') {
                        const results = data.data.search_results || [];
                        const resultsStr = JSON.stringify(results);

                        // [核心修改] 检测严重警告（熔断停止）
                        if (resultsStr.includes("流程已终止")) {
                            showToast("⛔️ 文档与问题无关，任务已强制停止");
                            logs.value.push(`[系统] 任务终止: 文档与问题无关（仅文档模式）`);
                            currentStep.value = 'done'; // 强制结束状态
                            return; // 关键：直接返回，不再执行下面的代码，防止跳到 writer
                        }

                        // 检测普通警告（自动切换等）
                        if (resultsStr.includes("自动切换为全网搜索")) {
                            showToast("⚠️ 文档与问题无关，已自动切换为全网搜索");
                        } else if (resultsStr.includes("Document Only 模式")) {
                            showToast("⚠️ 文档与问题无关，无法回答");
                        }

                        // 如果没有停止，则正常流转到 writer
                        currentStep.value = 'writer';
                        logs.value.push(`[检索] 数据采集完成，共 ${results.length} 条结果`);
                    }

                    // --- 步骤 3: 写作 (Writer) ---
                    else if (data.step === 'writer') {
                        currentStep.value = 'reviewer';
                        logs.value.push(`[撰写] 正在生成报告...`);
                        if (data.data.final_report) {
                            displayedReport.value = '';
                            typeWriterEffect(data.data.final_report);
                        }
                    }

                    // --- 步骤 4: 审查 (Reviewer) ---
                    else if (data.step === 'reviewer') {
                        if (data.data.review_status === 'FAIL') {
                            logs.value.push(`[审查] 未通过: ${data.data.critique} -> 重新规划`);
                            currentStep.value = 'planner';
                        } else {
                            logs.value.push(`[审查] 通过 ✓`);
                        }
                    }
                    else if (data.step === 'refiner') {
                    currentStep.value = 'writer'; // UI上复用写作状态
                    logs.value.push(`[修订] 根据反馈修改报告...`);
                    if (data.data.final_report) {
                        displayedReport.value = '';
                        // 重新打字输出修改后的报告
                        typeWriterEffect(data.data.final_report);
                    }
                }

                    scrollToBottom();
                },
            () => {
                isLoading.value = false;
                currentStep.value = 'done';
                logs.value.push('[完成] 研究流程结束');
                // 保存到研究历史
                if (displayedReport.value) {
                    const session = {
                        query: query.value,
                        report: displayedReport.value,
                        mode: searchMode.value
                    };
                    saveSession(session);
                    history.value = getHistory();
                }
                scrollToBottom();
            },
            (err) => {
                isLoading.value = false;
                logs.value.push(`[错误] ${err.message}`);
                scrollToBottom();
            },
            currentAbortController?.signal
        );
    } catch (e) {
        isLoading.value = false;
        logs.value.push(`[错误] 初始化失败: ${e.message}`);
        showToast("系统错误: " + e.message, 'error');
    }
};
</script>

<style>
/* 保持原有的动画样式 */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}
.slide-down-enter-from,
.slide-down-leave-to {
  transform: translate(-50%, -100%);
  opacity: 0;
}
@keyframes blob {
    0% { transform: translate(0px, 0px) scale(1); }
    33% { transform: translate(30px, -50px) scale(1.1); }
    66% { transform: translate(-20px, 20px) scale(0.9); }
    100% { transform: translate(0px, 0px) scale(1); }
}
.animate-blob {
    animation: blob 7s infinite;
}
.animation-delay-2000 { animation-delay: 2s; }
.animation-delay-4000 { animation-delay: 4s; }

/* 简单的淡入动画 */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(5px); }
    to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in-up {
    animation: fadeInUp 0.3s ease-out;
}
@import 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css';

/* 2. 关键修复：解决 Tailwind 与 KaTeX 的样式冲突 */
/* Tailwind 默认将所有元素设为 border-box，这会破坏 KaTeX 的布局算法 */
.katex * {
    box-sizing: content-box !important;
}

/* 3. 公式滚动条优化 */
.katex-display {
    overflow-x: auto;
    overflow-y: hidden;
    padding: 0.5em 0;
    margin: 1em 0 !important; /* 修正外边距 */
}

/* --- 全局字体优化 --- */
body {
  font-family: theme('fontFamily.sans');
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* --- 舒适阅读风格 --- */
.prose {
  font-size: 1.05rem;
  color: #374151;
  line-height: 1.75;
}

/* 标题 */
.prose h1 {
  @apply text-3xl font-bold text-gray-900 mb-8 pb-4 border-b border-gray-100;
  font-family: theme('fontFamily.sans');
  line-height: 1.3;
}

.prose h2 {
  @apply text-xl font-bold text-gray-800 mt-10 mb-4 flex items-center;
  font-family: theme('fontFamily.sans');
  position: relative;
  padding-left: 1rem;
}
.prose h2::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 1em;
  @apply bg-blue-600 rounded-full;
}

.prose h3 {
  @apply text-lg font-bold text-gray-800 mt-8 mb-3;
  font-family: theme('fontFamily.sans');
}

/* 正文 */
.prose p {
  @apply text-justify mb-5 leading-relaxed text-gray-700;
}

/* 重点文字 */
.prose strong {
  @apply font-bold text-gray-900;
}

/* 摘要/引用块 */
.prose blockquote {
  font-style: normal !important;
  @apply my-8 pl-6 pr-4 py-5;
  @apply bg-gray-50 rounded-r-lg border-l-4 border-blue-500;
  @apply text-gray-700 text-base leading-relaxed; 
}

/* 列表 */
.prose ul {
  @apply list-disc list-outside ml-6 space-y-2 mb-6 text-gray-700;
}
.prose ol {
  @apply list-decimal list-outside ml-6 space-y-2 mb-6 text-gray-700;
}

/* 表格 */
.prose table {
  @apply w-full text-left border-collapse my-8 rounded-lg overflow-hidden border border-gray-200;
}
.prose thead {
  @apply bg-gray-50;
}
.prose th {
  @apply px-4 py-3 font-semibold text-gray-900 text-sm uppercase tracking-wide border-b border-gray-200;
}
.prose td {
  @apply px-4 py-3 text-sm text-gray-600 border-b border-gray-100;
}
.prose tr:hover td {
  @apply bg-blue-50/30 transition-colors;
}

/* 代码块 */
.prose pre {
  @apply bg-[#1e293b] text-gray-100 rounded-xl p-5 my-6 overflow-x-auto shadow-lg;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
}
.prose code {
  @apply text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded text-sm font-medium mx-0.5;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
}
.prose pre code {
  @apply bg-transparent text-gray-100 p-0 text-xs;
}

/* KaTeX 字体微调 */
.katex {
  font-size: 1.15em;
  font-family: 'Times New Roman', serif;
}
</style>