<template>
  <div class="h-screen bg-gray-50 flex flex-col">
    <!-- 顶栏 -->
    <header class="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-3 shrink-0">
      <button @click="$emit('back')" class="flex items-center gap-1.5 text-sm text-gray-500 hover:text-blue-600 transition-colors">
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        返回对话
      </button>
      <span class="text-base font-bold text-gray-800">账号管理</span>
    </header>

    <div class="flex-1 flex min-h-0">
      <!-- 左侧导航 -->
      <nav class="w-52 bg-white border-r border-gray-200 py-4 flex flex-col shrink-0 overflow-y-auto">
        <div class="px-4 mb-3 flex items-center gap-3">
          <div class="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm">IR</div>
          <div>
            <p class="text-sm font-semibold text-gray-800">IRIS 用户</p>
            <p class="text-[11px] text-gray-400">智能调研系统</p>
          </div>
        </div>
        <div class="px-2 space-y-0.5 flex-1">
          <button v-for="item in navItems" :key="item.key" @click="section = item.key"
            class="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[13px] transition-colors"
            :class="section === item.key ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-50'">
            <span class="text-base">{{ item.icon }}</span>
            <span class="flex-1 text-left">{{ item.label }}</span>
            <svg v-if="section === item.key" class="w-3.5 h-3.5 text-blue-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
          </button>
        </div>
      </nav>

      <!-- 右侧内容 -->
      <main class="flex-1 overflow-y-auto p-6">
        <div class="max-w-2xl">
          <h2 class="text-lg font-bold text-gray-800 mb-1">{{ currentNav?.label }}</h2>
          <p class="text-[12px] text-gray-400 mb-5">{{ currentNav?.desc }}</p>

          <!-- 知识库 -->
          <template v-if="section === 'kb'">
            <div class="bg-white rounded-xl border border-gray-100 p-5">
              <div class="flex items-center justify-between">
                <p class="text-sm font-medium text-gray-700">上传文档</p>
                <button @click="$refs.fileInput.click()" class="px-3 py-1.5 text-[12px] text-white bg-blue-500 hover:bg-blue-600 rounded-lg transition-colors">选择文件</button>
                <input ref="fileInput" type="file" multiple accept=".pdf" class="hidden" @change="(e) => $emit('fileSelect', e)" />
              </div>
              <p class="text-[11px] text-gray-400 mt-2">支持 PDF，用于文档检索模式（RAG）</p>
              <div v-if="uploadedFiles.length" class="mt-3 flex flex-wrap gap-1.5">
                <span v-for="(f,i) in uploadedFiles" :key="i" class="text-[11px] px-2 py-1 rounded-full bg-green-50 text-green-600">{{ f.name }}</span>
              </div>
            </div>
          </template>

          <!-- Skills -->
          <template v-if="section === 'skills'">
            <div class="bg-white rounded-xl border border-gray-100 p-5">
              <div class="flex items-center justify-between mb-4">
                <p class="text-sm font-medium text-gray-700">调研技能</p>
                <button @click="$refs.skillFileInput.click()" class="px-3 py-1.5 text-[12px] border border-gray-200 text-gray-600 hover:bg-gray-50 rounded-lg transition-colors">上传 SKILL.md</button>
                <input ref="skillFileInput" type="file" accept=".md" class="hidden" @change="handleUploadSkillFile" />
              </div>
              <p class="text-[11px] text-gray-400 mb-4">也可以在对话里说「帮我创建一个XX的skill」直接创建</p>
              <div v-if="loadingSkills" class="text-center text-[12px] text-gray-400 py-8">加载中...</div>
              <div v-else-if="skills.length === 0" class="text-center text-[12px] text-gray-300 py-8">暂无 Skills</div>
              <div v-else class="divide-y divide-gray-50">
                <div v-for="skill in skills" :key="skill.name" class="flex items-center justify-between py-3">
                  <div class="min-w-0">
                    <p class="text-[13px] font-medium text-gray-700">{{ skill.name }} <span v-if="skill.is_builtin" class="text-[10px] px-1.5 py-0.5 bg-blue-100 text-blue-600 rounded-full">内置</span></p>
                    <p class="text-[11px] text-gray-400 mt-0.5 truncate">{{ skill.description }}</p>
                  </div>
                  <button v-if="!skill.is_builtin" @click="handleDeleteSkill(skill.name)" class="text-[12px] text-gray-300 hover:text-red-400">删除</button>
                </div>
              </div>
            </div>
          </template>

          <!-- 工具 -->
          <template v-if="section === 'tools'">
            <div class="bg-white rounded-xl border border-gray-100 p-5">
              <p class="text-sm font-medium text-gray-700 mb-4">可用工具</p>
              <div v-if="loadingTools" class="text-center text-[12px] text-gray-400 py-8">加载中...</div>
              <div v-else class="divide-y divide-gray-50">
                <div v-for="tool in tools" :key="tool.name" class="py-3">
                  <p class="text-[13px] font-medium text-gray-700">{{ tool.name }}</p>
                  <p class="text-[11px] text-gray-400 mt-0.5">{{ tool.description }}</p>
                </div>
              </div>
            </div>
          </template>

          <!-- 记忆 -->
          <template v-if="section === 'memory'">
            <div class="bg-white rounded-xl border border-gray-100 p-5">
              <p class="text-sm font-medium text-gray-700 mb-4">记忆搜索</p>
              <div class="flex gap-1.5 mb-3">
                <input v-model="memoryQuery" @keyup.enter="handleSearchMemory" type="text" placeholder="搜索记忆..." class="flex-1 px-3 py-2 text-[12px] border border-gray-200 rounded-lg focus:outline-none focus:border-blue-400" />
                <button @click="handleSearchMemory" class="px-4 py-2 text-[12px] text-white bg-blue-500 hover:bg-blue-600 rounded-lg transition-colors">搜索</button>
              </div>
              <div class="flex gap-1.5 mb-4">
                <button v-for="k in ['','episodic','semantic','procedural']" :key="k" @click="memoryKind = k"
                  class="px-2.5 py-1 rounded-full text-[11px] transition-colors"
                  :class="memoryKind === k ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'">{{ memoryKindLabel(k) }}</button>
              </div>
              <div v-if="searchingMemory" class="text-center text-[12px] text-gray-400 py-8">搜索中...</div>
              <div v-else-if="memoryResults.length === 0" class="text-center text-[12px] text-gray-300 py-8">暂无记忆</div>
              <div v-else class="divide-y divide-gray-50">
                <div v-for="m in memoryResults" :key="m.id" class="flex items-start justify-between gap-3 py-3">
                  <p class="text-[12px] text-gray-600 leading-relaxed flex-1">{{ m.content }}</p>
                  <button @click="handleDeleteMemory(m.id)" class="text-[12px] text-gray-300 hover:text-red-400 shrink-0">删除</button>
                </div>
              </div>
            </div>
          </template>

          <!-- 素材库 -->
          <template v-if="section === 'materials'">
            <div class="bg-white rounded-xl border border-gray-100 p-5">
              <p class="text-sm font-medium text-gray-700 mb-4">已保存的报告</p>
              <div v-if="materials.length === 0" class="text-center text-[12px] text-gray-300 py-8">暂无素材</div>
              <div v-else class="divide-y divide-gray-50">
                <div v-for="m in materials" :key="m.filename" @click="$emit('viewMaterial', m)" class="flex items-center justify-between py-3 cursor-pointer hover:bg-gray-50 rounded-lg px-2 -mx-2">
                  <div class="min-w-0">
                    <p class="text-[13px] font-medium text-gray-700 truncate">{{ m.filename.replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/\.md$/, '') }}</p>
                    <p class="text-[11px] text-gray-400 mt-0.5">{{ m.filename.split('-').slice(0,3).join('-') }}</p>
                  </div>
                  <button @click.stop="$emit('deleteMaterial', m.filename)" class="text-[12px] text-gray-300 hover:text-red-400">删除</button>
                </div>
              </div>
            </div>
          </template>

          <!-- 设置：Cell 风格设置行 -->
          <template v-if="section === 'settings'">
            <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
              <div class="flex items-center justify-between px-5 py-4 active:bg-gray-50 transition-colors">
                <div class="flex items-center gap-3">
                  <span class="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center text-base">✍️</span>
                  <div>
                    <p class="text-sm font-medium text-gray-700">写作风格</p>
                    <p class="text-[11px] text-gray-400 mt-0.5">影响报告的行文方式</p>
                  </div>
                </div>
                <div class="flex gap-1.5">
                  <button v-for="s in styleOptions" :key="s.value" @click="updatePref('style', s.value)" class="px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors" :class="preferences.style === s.value ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'">{{ s.label }}</button>
                </div>
              </div>
              <div class="h-px bg-gray-50 mx-5"></div>
              <div class="flex items-center justify-between px-5 py-4 active:bg-gray-50 transition-colors">
                <div class="flex items-center gap-3">
                  <span class="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center text-base">🌐</span>
                  <div>
                    <p class="text-sm font-medium text-gray-700">报告语言</p>
                    <p class="text-[11px] text-gray-400 mt-0.5">报告使用语言</p>
                  </div>
                </div>
                <div class="flex gap-1.5">
                  <button v-for="l in langOptions" :key="l.value" @click="updatePref('language', l.value)" class="px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors" :class="preferences.language === l.value ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'">{{ l.label }}</button>
                </div>
              </div>
              <div class="h-px bg-gray-50 mx-5"></div>
              <div class="flex items-center justify-between px-5 py-4 active:bg-gray-50 transition-colors">
                <div class="flex items-center gap-3">
                  <span class="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center text-base">🔍</span>
                  <div>
                    <p class="text-sm font-medium text-gray-700">默认搜索模式</p>
                    <p class="text-[11px] text-gray-400 mt-0.5">上传文档后的检索方式</p>
                  </div>
                </div>
                <div class="flex gap-1.5">
                  <button @click="updatePref('searchMode', 'hybrid')" class="px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors" :class="preferences.searchMode === 'hybrid' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'">混合</button>
                  <button @click="updatePref('searchMode', 'document')" class="px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors" :class="preferences.searchMode === 'document' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'">仅文档</button>
                </div>
              </div>
            </div>
            <p class="text-[11px] text-gray-400 mt-3 px-1">💡 记忆偏好：系统会记住你的写作偏好并在每次调研自动应用，可在「记忆」中查看历史记忆。</p>
          </template>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { listSkills, createSkill, deleteSkill, searchMemory, deleteMemoryItem, listTools } from '../services/api';

const props = defineProps({
    uploadedFiles: { type: Array, default: () => [] },
    materials: { type: Array, default: () => [] },
});
const emit = defineEmits(['back', 'fileSelect', 'loadMaterials', 'viewMaterial', 'deleteMaterial']);

const navItems = [
    { key: 'kb', label: '知识库', icon: '📁', desc: '上传与管理 PDF 文档，供文档检索使用' },
    { key: 'skills', label: 'Skills', icon: '🧩', desc: '管理你的调研技能（策略模板）' },
    { key: 'tools', label: '工具', icon: '🛠️', desc: '系统可调用的工具列表' },
    { key: 'memory', label: '记忆', icon: '🧠', desc: '搜索和管理四层记忆' },
    { key: 'materials', label: '素材库', icon: '📚', desc: '已保存到素材库的报告' },
    { key: 'settings', label: '设置', icon: '⚙️', desc: '写作偏好与默认行为' },
];
const section = ref('settings');
const currentNav = computed(() => navItems.find(i => i.key === section.value));

const switchSection = (key) => {
    section.value = key;
    if (key === 'skills') loadSkills();
    if (key === 'tools') loadTools();
    if (key === 'materials') emit('loadMaterials');
};

// Skills
const skills = ref([]);
const loadingSkills = ref(false);
const loadSkills = async () => {
    loadingSkills.value = true;
    try { const d = await listSkills(); skills.value = d.skills || []; } catch { skills.value = []; }
    loadingSkills.value = false;
};
const handleUploadSkillFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
        const text = await file.text();
        const skillName = file.name.replace(/\.md$/i, '').replace(/[^a-zA-Z0-9_]/g, '_');
        const descMatch = text.match(/^>\s*(.+)/m);
        const bodyStart = text.indexOf('\n', text.indexOf('\n') + 1);
        await createSkill({ name: skillName, description: descMatch ? descMatch[1].trim() : `从 ${file.name} 导入`, prompt_template: bodyStart > 0 ? text.slice(bodyStart).trim() : text.trim(), tools: [], memory_policy: 'none' });
        await loadSkills();
    } catch (e) { alert('上传失败: ' + (e.message || '')); }
    event.target.value = '';
};
const handleDeleteSkill = async (name) => {
    try { await deleteSkill(name); skills.value = skills.value.filter(s => s.name !== name); } catch {}
};

// Tools
const tools = ref([]);
const loadingTools = ref(false);
const loadTools = async () => {
    loadingTools.value = true;
    try { const d = await listTools(); tools.value = d.tools || []; } catch { tools.value = []; }
    loadingTools.value = false;
};

// Memory
const memoryQuery = ref('');
const memoryKind = ref('');
const memoryResults = ref([]);
const searchingMemory = ref(false);
const handleSearchMemory = async () => {
    if (!memoryQuery.value.trim()) return;
    searchingMemory.value = true;
    try { const d = await searchMemory(memoryQuery.value, memoryKind.value || null); memoryResults.value = d.results || []; }
    catch { memoryResults.value = []; }
    searchingMemory.value = false;
};
const handleDeleteMemory = async (id) => {
    try { await deleteMemoryItem(id); memoryResults.value = memoryResults.value.filter(m => m.id !== id); } catch {}
};
const memoryKindLabel = (k) => ({ '': '全部', episodic: '情景', semantic: '语义', procedural: '程序' }[k] || k);

// 设置
const STORAGE_KEY = 'iris_preferences';
const preferences = ref(JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'));
if (!preferences.value.style) preferences.value.style = 'detailed';
if (!preferences.value.language) preferences.value.language = 'zh';
if (!preferences.value.searchMode) preferences.value.searchMode = 'hybrid';
const styleOptions = [
    { value: 'detailed', label: '详细' }, { value: 'concise', label: '简洁' },
    { value: 'formal', label: '正式' }, { value: 'casual', label: '通俗' },
];
const langOptions = [{ value: 'zh', label: '中文' }, { value: 'en', label: 'English' }];
const updatePref = (key, value) => { preferences.value[key] = value; localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences.value)); };

onMounted(() => { emit('loadMaterials'); loadSkills(); loadTools(); });
</script>