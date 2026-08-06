<template>
  <aside class="w-64 bg-white border-r border-gray-200 flex flex-col shrink-0 transition-transform duration-300" :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0 fixed lg:relative z-30 h-full'">
    <div class="px-5 py-4 border-b border-gray-100">
      <h1 class="text-lg font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">IRIS</h1>
      <p class="text-[10px] text-gray-400 mt-0.5">智能调研系统</p>
    </div>

    <div class="px-3 pt-3 flex gap-2">
      <button @click="$emit('newChat')" class="flex-1 flex items-center gap-2 px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 transition-colors">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        新建调研
      </button>
    </div>

    <div class="flex border-b border-gray-100 mt-2 mx-3">
      <button v-for="tab in tabs" :key="tab.key" @click="activeTab = tab.key; if(tab.key==='materials') $emit('loadMaterials')" class="flex-1 py-2 text-[11px] font-bold transition-colors relative" :class="activeTab === tab.key ? 'text-blue-600' : 'text-gray-400'">
        {{ tab.label }}
        <div v-if="activeTab === tab.key" class="absolute bottom-0 left-1/4 right-1/4 h-0.5 bg-blue-500 rounded-full"></div>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-3 py-2 space-y-1">
      <!-- 知识库 -->
      <template v-if="activeTab === 'kb'">
        <div class="border-2 border-dashed rounded-xl p-3 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50/30 transition-all" :class="uploadedFiles.length > 0 ? 'border-green-300 bg-green-50/30' : 'border-gray-200'" @click="$refs.fileInput.click()">
          <input ref="fileInput" type="file" multiple accept=".pdf" class="hidden" @change="(e) => $emit('fileSelect', e)" />
          <div v-if="uploadedFiles.length === 0">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6 mx-auto text-gray-300 mb-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <p class="text-[11px] text-gray-400">上传 PDF 文档</p>
          </div>
          <div v-else class="space-y-1">
            <div v-for="(f, i) in uploadedFiles" :key="i" class="flex items-center gap-2 text-[11px] text-gray-600">
              <svg class="w-3 h-3 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
              <span class="truncate">{{ f.name }}</span>
            </div>
          </div>
        </div>
      </template>

      <!-- 素材库 -->
      <template v-if="activeTab === 'materials'">
        <div v-if="materials.length === 0" class="text-center text-[11px] text-gray-300 py-8">暂无素材<br><span class="text-[10px]">调研完成后点击「💾 保存素材库」</span></div>
        <div v-for="m in materials" :key="m.filename" class="group px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer" @click="$emit('viewMaterial', m)">
          <div class="flex items-center justify-between">
            <p class="text-[11px] font-medium text-gray-700 truncate flex-1">{{ m.filename.replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/\.md$/, '') }}</p>
            <button @click.stop="$emit('deleteMaterial', m.filename)" class="text-[10px] text-gray-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all px-1">✕</button>
          </div>
          <p class="text-[10px] text-gray-400 mt-0.5">{{ m.filename.split('-').slice(0, 3).join('-') }} · {{ formatSize(m.size) }}</p>
        </div>
      </template>

      <!-- 历史 -->
      <template v-if="activeTab === 'history'">
        <div v-if="history.length === 0" class="text-center text-[11px] text-gray-300 py-8">暂无历史</div>
        <div v-for="s in history" :key="s.id" @click="$emit('viewHistory', s)" class="px-3 py-2 rounded-lg cursor-pointer transition-colors text-[11px]" :class="activeHistoryId === s.id ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-50 text-gray-600'">
          <p class="truncate font-medium">{{ s.query }}</p>
          <p class="text-[10px] text-gray-400 mt-0.5">{{ formatTime(s.timestamp) }}</p>
        </div>
      </template>

      <!-- Skills -->
      <template v-if="activeTab === 'skills'">
        <!-- 创建 Skill 按钮 -->
        <button @click="showCreateSkill = true" class="w-full px-3 py-2 bg-blue-500 text-white text-[11px] font-medium rounded-lg hover:bg-blue-600 transition-colors flex items-center justify-center gap-1.5">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          创建 Skill
        </button>
        <!-- 上传 SKILL.md 按钮 -->
        <button @click="$refs.skillFileInput.click()" class="w-full px-3 py-1.5 mt-1.5 border border-gray-200 text-gray-600 text-[11px] font-medium rounded-lg hover:bg-gray-50 transition-colors flex items-center justify-center gap-1.5">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          上传 SKILL.md
        </button>
        <input ref="skillFileInput" type="file" accept=".md" class="hidden" @change="handleUploadSkillFile" />

        <div v-if="loadingSkills" class="text-center text-[11px] text-gray-400 py-8">加载中...</div>
        <div v-else-if="skills.length === 0" class="text-center text-[11px] text-gray-300 py-8">暂无 Skills</div>
        <div v-else class="space-y-2 mt-2">
          <div v-for="skill in skills" :key="skill.name" class="px-3 py-2 rounded-lg transition-colors group" :class="expandedSkill === skill.name ? 'bg-gray-50' : 'hover:bg-gray-50'">
            <div class="flex items-center justify-between">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1.5">
                  <button @click="expandedSkill = expandedSkill === skill.name ? '' : skill.name" class="text-[11px] font-medium text-gray-700 truncate text-left">
                    {{ skill.name }}
                  </button>
                  <span v-if="skill.is_builtin" class="text-[9px] px-1.5 py-0.5 bg-blue-100 text-blue-600 rounded-full">builtin</span>
                  <span v-if="skill.required_tools && skill.required_tools.length > 0" class="text-[9px] px-1.5 py-0.5 bg-purple-100 text-purple-600 rounded-full">{{ skill.required_tools.length }} 工具</span>
                </div>
                <p class="text-[10px] text-gray-400 mt-0.5 truncate">{{ skill.description }}</p>
              </div>
              <div class="flex items-center gap-1.5">
                <!-- 启用/禁用开关 -->
                <button @click="toggleSkillEnabled(skill)" class="relative h-5 w-9 rounded-full transition-colors shrink-0" :class="isSkillEnabled(skill.name) ? (skill.is_builtin ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-500') : 'bg-gray-300'">
                  <span class="absolute top-0.5 size-4 rounded-full bg-white shadow transition-all" :class="isSkillEnabled(skill.name) ? 'left-4' : 'left-0.5'"></span>
                </button>
                <button v-if="!skill.is_builtin" @click="handleDeleteSkill(skill.name)" class="text-[10px] text-gray-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all px-1">✕</button>
              </div>
            </div>
            <!-- 展开区域：prompt 模板预览 + 工具列表 -->
            <div v-if="expandedSkill === skill.name" class="mt-2 pt-2 border-t border-gray-100 space-y-1.5">
              <div v-if="skill.prompt_template" class="text-[10px] text-gray-500 leading-relaxed">
                <span class="font-medium text-gray-600">Prompt：</span>
                {{ skill.prompt_template.length > 100 ? skill.prompt_template.slice(0, 100) + '...' : skill.prompt_template }}
              </div>
              <div v-if="skill.required_tools && skill.required_tools.length > 0" class="flex flex-wrap gap-1">
                <span v-for="tool in skill.required_tools" :key="tool" class="text-[9px] px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded-full">{{ tool }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- 创建 Skill 对话框 -->
      <Teleport to="body">
        <div v-if="showCreateSkill" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="showCreateSkill = false">
          <div class="bg-white rounded-xl shadow-xl w-full max-w-[480px] mx-4 overflow-hidden">
            <div class="px-5 py-4 border-b border-gray-100">
              <h3 class="text-sm font-bold text-gray-800">创建 Skill</h3>
              <p class="text-[10px] text-gray-400 mt-0.5">自定义你的智能调研技能</p>
            </div>
            <div class="px-5 py-4 space-y-3">
              <div>
                <label class="text-[10px] font-bold text-gray-500 uppercase tracking-wider">名称 <span class="text-red-400">*</span></label>
                <input v-model="newSkill.name" @input="validateSkillName" type="text" placeholder="my_skill" class="mt-1 w-full px-3 py-2 text-[11px] border border-gray-200 rounded-lg focus:outline-none focus:border-blue-400" :class="newSkillNameError ? 'border-red-300' : ''" />
                <p v-if="newSkillNameError" class="text-[10px] text-red-500 mt-1">{{ newSkillNameError }}</p>
                <p v-else class="text-[9px] text-gray-400 mt-1">仅允许字母、数字、下划线</p>
              </div>
              <div>
                <label class="text-[10px] font-bold text-gray-500 uppercase tracking-wider">描述</label>
                <textarea v-model="newSkill.description" rows="2" placeholder="简要描述这个 Skill 的用途" class="mt-1 w-full px-3 py-2 text-[11px] border border-gray-200 rounded-lg focus:outline-none focus:border-blue-400 resize-none"></textarea>
              </div>
              <div>
                <label class="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Prompt 模板 <span class="text-red-400">*</span></label>
                <textarea v-model="newSkill.prompt_template" rows="4" placeholder="你是一个专业的研究分析师，擅长..." class="mt-1 w-full px-3 py-2 text-[11px] border border-gray-200 rounded-lg focus:outline-none focus:border-blue-400 resize-none font-mono"></textarea>
              </div>
              <div>
                <label class="text-[10px] font-bold text-gray-500 uppercase tracking-wider">所需工具</label>
                <div class="flex flex-wrap gap-1.5 mt-1">
                  <button v-for="tool in availableTools" :key="tool.name" @click="toggleNewSkillTool(tool.name)" class="px-2 py-1 text-[10px] rounded-full transition-colors border" :class="newSkill.tools.includes(tool.name) ? 'bg-blue-100 text-blue-700 border-blue-200' : 'bg-gray-50 text-gray-500 border-gray-200 hover:text-gray-700'">
                    {{ tool.name }}
                  </button>
                  <span v-if="availableTools.length === 0" class="text-[10px] text-gray-400">暂无可用工具</span>
                </div>
              </div>
              <div>
                <label class="text-[10px] font-bold text-gray-500 uppercase tracking-wider">记忆策略</label>
                <div class="flex gap-1.5 mt-1">
                  <button v-for="mp in memoryPolicyOptions" :key="mp.value" @click="newSkill.memory_policy = mp.value" class="px-2 py-1 text-[10px] rounded-full transition-colors" :class="newSkill.memory_policy === mp.value ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:text-gray-700'">
                    {{ mp.label }}
                  </button>
                </div>
              </div>
            </div>
            <div class="px-5 py-3 border-t border-gray-100 flex justify-end gap-2">
              <button @click="showCreateSkill = false" class="px-4 py-1.5 text-[11px] text-gray-600 rounded-lg hover:bg-gray-50 transition-colors">取消</button>
              <button @click="handleCreateSkill" :disabled="!canCreateSkill || creatingSkill" class="px-4 py-1.5 text-[11px] text-white rounded-lg transition-colors" :class="canCreateSkill && !creatingSkill ? 'bg-blue-500 hover:bg-blue-600' : 'bg-gray-300 cursor-not-allowed'">
                {{ creatingSkill ? '创建中...' : '创建' }}
              </button>
            </div>
            <!-- 错误提示 -->
            <div v-if="createSkillError" class="px-5 pb-3">
              <p class="text-[11px] text-red-500 bg-red-50 px-3 py-2 rounded-lg border border-red-100">{{ createSkillError }}</p>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- 记忆搜索 -->
      <template v-if="activeTab === 'memory'">
        <div class="space-y-2">
          <!-- 添加记忆按钮 -->
          <div class="flex justify-between items-center">
            <span class="text-[11px] text-gray-500 font-medium">记忆管理</span>
            <button @click="showAddMemory = !showAddMemory" class="px-2.5 py-1 text-[10px] bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
              {{ showAddMemory ? '取消' : '+ 添加记忆' }}
            </button>
          </div>

          <!-- 添加记忆面板 -->
          <div v-if="showAddMemory" class="p-3 bg-blue-50 rounded-lg border border-blue-100">
            <textarea v-model="newMemoryContent" placeholder="输入记忆内容..." rows="3" class="w-full px-2.5 py-1.5 text-[11px] border border-gray-200 rounded-lg focus:outline-none focus:border-blue-400 resize-none"></textarea>
            <p v-if="newMemoryError" class="text-[10px] text-red-500 mt-1">{{ newMemoryError }}</p>
            <div class="flex gap-1.5 mt-2">
              <button @click="newMemoryKind = 'episodic'" class="px-2 py-1 text-[10px] rounded-full transition-colors" :class="newMemoryKind === 'episodic' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:text-gray-700'">情景</button>
              <button @click="newMemoryKind = 'semantic'" class="px-2 py-1 text-[10px] rounded-full transition-colors" :class="newMemoryKind === 'semantic' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500 hover:text-gray-700'">语义</button>
              <button @click="newMemoryKind = 'procedural'" class="px-2 py-1 text-[10px] rounded-full transition-colors" :class="newMemoryKind === 'procedural' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-500 hover:text-gray-700'">程序</button>
            </div>
            <div class="flex justify-end gap-2 mt-2">
              <button @click="showAddMemory = false" class="px-3 py-1 text-[10px] text-gray-500 hover:text-gray-700 transition-colors">取消</button>
              <button @click="handleCreateMemory" :disabled="creatingMemory" class="px-3 py-1 text-[10px] bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50">{{ creatingMemory ? '保存中...' : '保存' }}</button>
            </div>
          </div>

          <div class="flex gap-1.5">
            <input v-model="memoryQuery" @keyup.enter="handleSearchMemory" type="text" placeholder="搜索记忆..." class="flex-1 px-2.5 py-1.5 text-[11px] border border-gray-200 rounded-lg focus:outline-none focus:border-blue-400" />
            <button @click="handleSearchMemory" class="px-2.5 py-1.5 text-[11px] bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">搜索</button>
          </div>
          <div class="flex gap-1.5">
            <button @click="memoryKind = ''" class="px-2 py-1 text-[10px] rounded-full transition-colors" :class="memoryKind === '' ? 'bg-gray-200 text-gray-700' : 'bg-gray-100 text-gray-500 hover:text-gray-700'">全部</button>
            <button @click="memoryKind = 'episodic'" class="px-2 py-1 text-[10px] rounded-full transition-colors" :class="memoryKind === 'episodic' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:text-gray-700'">情景</button>
            <button @click="memoryKind = 'semantic'" class="px-2 py-1 text-[10px] rounded-full transition-colors" :class="memoryKind === 'semantic' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500 hover:text-gray-700'">语义</button>
            <button @click="memoryKind = 'procedural'" class="px-2 py-1 text-[10px] rounded-full transition-colors" :class="memoryKind === 'procedural' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-500 hover:text-gray-700'">程序</button>
          </div>
          <div v-if="searchingMemory" class="text-center text-[11px] text-gray-400 py-4">搜索中...</div>
          <div v-else-if="memoryResults.length === 0 && memoryQuery" class="text-center text-[11px] text-gray-300 py-4">未找到相关记忆</div>
          <div v-else-if="memoryResults.length === 0" class="text-center text-[11px] text-gray-300 py-4">暂无记忆<br><span class="text-[10px]">点击上方「+ 添加记忆」创建</span></div>
          <div v-else class="space-y-3">
            <div v-for="group in memoryGrouped" :key="group.kind">
              <div class="flex items-center gap-1.5 mb-1.5">
                <span class="text-[10px] font-bold px-1.5 py-0.5 rounded-full" :class="memoryKindColor(group.kind)">{{ memoryKindLabel(group.kind) }}</span>
                <span class="text-[9px] text-gray-400">{{ group.items.length }}</span>
              </div>
              <div v-for="m in group.items" :key="m.id" class="px-3 py-2 rounded-lg bg-gray-50 group cursor-pointer" @click="editingMemoryId !== m.id && toggleMemoryExpand(m.id)">
                <template v-if="editingMemoryId === m.id">
                  <textarea v-model="editingMemoryContent" rows="3" class="w-full px-2 py-1 text-[11px] border border-blue-300 rounded-lg focus:outline-none focus:border-blue-400 resize-none" @click.stop></textarea>
                  <div class="flex gap-1.5 mt-1.5">
                    <button v-for="k in ['episodic','semantic','procedural']" :key="k" @click.stop="editingMemoryKind = k" class="px-2 py-0.5 text-[9px] rounded-full transition-colors" :class="editingMemoryKind === k ? memoryKindColor(k) : 'bg-gray-100 text-gray-500'">{{ memoryKindLabel(k) }}</button>
                  </div>
                  <div class="flex justify-end gap-2 mt-1.5">
                    <button @click.stop="cancelEditMemory" class="text-[10px] text-gray-400 hover:text-gray-600">取消</button>
                    <button @click.stop="saveEditMemory" :disabled="savingMemoryEdit" class="text-[10px] text-white bg-blue-500 hover:bg-blue-600 px-2.5 py-0.5 rounded-lg disabled:opacity-50">{{ savingMemoryEdit ? '保存中...' : '保存' }}</button>
                  </div>
                </template>
                <template v-else>
                  <div class="flex items-start justify-between gap-2">
                    <div class="flex-1 min-w-0">
                      <p class="text-[11px] text-gray-600 leading-relaxed" :class="{ 'line-clamp-2': expandedMemoryId !== m.id }">{{ m.content }}</p>
                      <div class="flex items-center gap-2 mt-1">
                        <span class="text-[9px] text-gray-400">{{ formatRelativeTime(m.created_at) }}</span>
                        <span v-if="m.thread_id" class="text-[9px] text-gray-300">话题:{{ m.thread_id.slice(0, 8) }}</span>
                      </div>
                    </div>
                    <div class="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-all">
                      <button @click.stop="startEditMemory(m)" class="text-[10px] text-gray-300 hover:text-blue-400 px-1">✎</button>
                      <button @click.stop="handleDeleteMemory(m.id)" class="text-[10px] text-gray-300 hover:text-red-400 px-1">✕</button>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Tools -->
      <template v-if="activeTab === 'tools'">
        <div v-if="loadingTools" class="text-center text-[11px] text-gray-400 py-8">加载中...</div>
        <div v-else-if="tools.length === 0" class="text-center text-[11px] text-gray-300 py-8">暂无工具</div>
        <div v-else class="space-y-1">
          <div v-for="tool in tools" :key="tool.name" class="rounded-lg transition-colors" :class="expandedTool === tool.name ? 'bg-gray-50' : 'hover:bg-gray-50'">
            <button @click="toggleTool(tool.name)" class="w-full px-3 py-2 text-left">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-1.5">
                  <p class="text-[11px] font-medium text-gray-700">{{ tool.name }}</p>
                  <span v-if="toolResult[tool.name]" class="w-1.5 h-1.5 rounded-full bg-green-400"></span>
                </div>
                <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3 text-gray-400 transition-transform" :class="expandedTool === tool.name ? 'rotate-180' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
              </div>
              <p class="text-[10px] text-gray-400 mt-0.5">{{ tool.description }}</p>
            </button>
            <div v-if="expandedTool === tool.name" class="px-3 pb-3 space-y-2">
              <div class="flex gap-1.5">
                <input
                  :value="getToolInput(tool.name)"
                  @input="toolInputs[tool.name] = $event.target.value"
                  @keyup.enter="handleExecuteTool(tool)"
                  type="text"
                  placeholder="输入查询..."
                  class="flex-1 px-2.5 py-1.5 text-[11px] border border-gray-200 rounded-lg focus:outline-none focus:border-blue-400 bg-white"
                />
                <button
                  @click="handleExecuteTool(tool)"
                  :disabled="toolLoading === tool.name || !getToolInput(tool.name).trim()"
                  class="px-2.5 py-1.5 text-[11px] text-white rounded-lg transition-colors flex items-center gap-1 shrink-0"
                  :class="toolLoading === tool.name || !getToolInput(tool.name).trim() ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-500 hover:bg-blue-600'"
                >
                  <svg v-if="toolLoading === tool.name" class="animate-spin w-3 h-3" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" class="opacity-25"/><path d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" fill="currentColor" class="opacity-75"/></svg>
                  <svg v-else-if="toolError[tool.name]" class="w-3 h-3 text-red-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                  <svg v-else-if="toolResult[tool.name] && !toolError[tool.name]" class="w-3 h-3 text-green-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                  执行
                </button>
              </div>
              <div v-if="toolError[tool.name]" class="px-2.5 py-2 text-[11px] text-red-600 bg-red-50 rounded-lg border border-red-100">
                {{ toolError[tool.name] }}
              </div>
              <div v-if="toolResult[tool.name]" class="rounded-lg border border-gray-200 bg-white overflow-hidden">
                <button @click="toolResultExpanded[tool.name] = !toolResultExpanded[tool.name]" class="w-full px-2.5 py-1.5 flex items-center justify-between text-[10px] text-gray-400 hover:bg-gray-50 transition-colors">
                  <span>结果</span>
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3 transition-transform" :class="toolResultExpanded[tool.name] ? 'rotate-180' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                </button>
                <div v-show="toolResultExpanded[tool.name] !== false" class="px-2.5 pb-2.5 max-h-[300px] overflow-y-auto">
                  <div class="prose prose-xs max-w-none text-[11px] text-gray-600 leading-relaxed" v-html="renderMd(toolResult[tool.name])"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- 设置 -->
      <template v-if="activeTab === 'settings'">
        <div class="space-y-3 py-1">
          <p class="text-[10px] text-gray-400 uppercase tracking-wider font-bold">写作风格</p>
          <div class="flex flex-wrap gap-1.5">
            <button v-for="s in styleOptions" :key="s.value" @click="updatePref('style', s.value)" class="px-2.5 py-1 rounded-full text-[10px] font-medium transition-colors" :class="preferences.style === s.value ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:text-gray-700'">{{ s.label }}</button>
          </div>

          <p class="text-[10px] text-gray-400 uppercase tracking-wider font-bold mt-3">报告语言</p>
          <div class="flex gap-1.5">
            <button v-for="l in langOptions" :key="l.value" @click="updatePref('language', l.value)" class="px-2.5 py-1 rounded-full text-[10px] font-medium transition-colors" :class="preferences.language === l.value ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:text-gray-700'">{{ l.label }}</button>
          </div>

          <p class="text-[10px] text-gray-400 uppercase tracking-wider font-bold mt-3">默认搜索模式</p>
          <div class="flex gap-1.5">
            <button @click="updatePref('searchMode', 'hybrid')" class="px-2.5 py-1 rounded-full text-[10px] font-medium transition-colors" :class="preferences.searchMode === 'hybrid' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-500 hover:text-gray-700'">混合模式</button>
            <button @click="updatePref('searchMode', 'document')" class="px-2.5 py-1 rounded-full text-[10px] font-medium transition-colors" :class="preferences.searchMode === 'document' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:text-gray-700'">仅文档</button>
          </div>

          <div class="mt-4 pt-3 border-t border-gray-100">
            <p class="text-[10px] text-gray-400 uppercase tracking-wider font-bold">记忆管理</p>
            <p class="text-[10px] text-gray-400 mt-1">使用左侧「记忆」标签页搜索和管理四层记忆。</p>
          </div>
        </div>
      </template>
    </div>

    <!-- 本会话统计 -->
    <div class="border-t border-gray-200 p-3 mt-auto">
      <div class="text-[10px] text-gray-400 mb-1">📊 本会话统计</div>
      <div class="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
        <div class="text-gray-500">研究次数</div>
        <div class="text-gray-700 font-medium">{{ stats.researchCount }}</div>
        <div class="text-gray-500">生成报告</div>
        <div class="text-gray-700 font-medium">{{ stats.reportCount }}</div>
        <div class="text-gray-500">平均耗时</div>
        <div class="text-gray-700 font-medium">{{ avgTime }}分钟</div>
        <div class="text-gray-500">引用来源</div>
        <div class="text-gray-700 font-medium">{{ stats.sourceCount }}</div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, watch, reactive, computed } from 'vue';
import { listSkills, createSkill, updateSkill, deleteSkill, searchMemory, deleteMemoryItem, createMemory, updateMemory, listTools, executeTool } from '../services/api';
import MarkdownIt from 'markdown-it';

const md = new MarkdownIt({ html: false, breaks: true, linkify: true });

defineProps({
    sidebarOpen: Boolean,
    uploadedFiles: { type: Array, default: () => [] },
    materials: { type: Array, default: () => [] },
    history: { type: Array, default: () => [] },
    activeHistoryId: { type: [String, Number, null], default: null },

    stats: { type: Object, default: () => ({ researchCount: 0, reportCount: 0, totalTime: 0, sourceCount: 0 }) },
    avgTime: { type: Number, default: 0 },
});

defineEmits(['newChat', 'fileSelect', 'loadMaterials', 'viewMaterial', 'deleteMaterial', 'viewHistory', 'updatePreference']);

const activeTab = ref('kb');
const tabs = [
    { key: 'kb', label: '知识库' },
    { key: 'skills', label: 'Skills' },
    { key: 'tools', label: '工具' },
    { key: 'memory', label: '记忆' },
    { key: 'materials', label: '素材库' },
    { key: 'history', label: '历史' },
    { key: 'settings', label: '设置' },
];

// === Skills ===
const skills = ref([]);
const loadingSkills = ref(false);
const expandedSkill = ref('');
const showCreateSkill = ref(false);
const creatingSkill = ref(false);
const createSkillError = ref('');
const newSkillNameError = ref('');
const skillEnabledState = ref({});
const SKILL_ENABLED_KEY = 'iris_skill_enabled';

// 加载启用状态
const loadSkillEnabledState = () => {
    try {
        skillEnabledState.value = JSON.parse(localStorage.getItem(SKILL_ENABLED_KEY) || '{}');
    } catch { skillEnabledState.value = {}; }
};
const saveSkillEnabledState = () => {
    localStorage.setItem(SKILL_ENABLED_KEY, JSON.stringify(skillEnabledState.value));
};
const isSkillEnabled = (name) => {
    if (!(name in skillEnabledState.value)) return true;
    return skillEnabledState.value[name];
};
const toggleSkillEnabled = async (skill) => {
    if (skill.is_builtin) return;
    const newState = !isSkillEnabled(skill.name);
    skillEnabledState.value[skill.name] = newState;
    saveSkillEnabledState();
    try {
        await updateSkill(skill.name, { memory_policy: skill.memory_policy });
    } catch {
        skillEnabledState.value[skill.name] = !newState;
        saveSkillEnabledState();
    }
};

// 可用工具列表
const availableTools = ref([]);
const loadAvailableTools = async () => {
    try {
        const data = await listTools();
        availableTools.value = data.tools || [];
    } catch { availableTools.value = []; }
};

// 新 Skill 表单
const newSkill = reactive({
    name: '',
    description: '',
    prompt_template: '',
    tools: [],
    memory_policy: 'none',
});
const memoryPolicyOptions = [
    { value: 'none', label: '无' },
    { value: 'read_episodic', label: '读取情景记忆' },
    { value: 'write_semantic', label: '写入语义记忆' },
];
const validateSkillName = () => {
    const v = newSkill.name;
    if (!v) { newSkillNameError.value = ''; return; }
    if (!/^[a-zA-Z0-9_]+$/.test(v)) {
        newSkillNameError.value = '名称仅允许字母、数字和下划线';
    } else {
        newSkillNameError.value = '';
    }
};
const toggleNewSkillTool = (toolName) => {
    const idx = newSkill.tools.indexOf(toolName);
    if (idx >= 0) newSkill.tools.splice(idx, 1);
    else newSkill.tools.push(toolName);
};
const canCreateSkill = computed(() => {
    return newSkill.name.trim() && !newSkillNameError.value && newSkill.prompt_template.trim();
});

const handleCreateSkill = async () => {
    if (!canCreateSkill.value || creatingSkill.value) return;
    creatingSkill.value = true;
    createSkillError.value = '';
    try {
        await createSkill({
            name: newSkill.name.trim(),
            description: newSkill.description.trim(),
            prompt_template: newSkill.prompt_template.trim(),
            tools: newSkill.tools.length > 0 ? [...newSkill.tools] : [],
            memory_policy: newSkill.memory_policy,
        });
        showCreateSkill.value = false;
        newSkill.name = '';
        newSkill.description = '';
        newSkill.prompt_template = '';
        newSkill.tools = [];
        newSkill.memory_policy = 'none';
        await loadSkills();
    } catch (err) {
        createSkillError.value = err.message || '创建失败，请检查名称是否已存在';
    } finally {
        creatingSkill.value = false;
    }
};

// 上传 SKILL.md 文件
const handleUploadSkillFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
        const text = await file.text();
        const nameMatch = text.match(/^#\s+(.+)/m);
        const skillName = file.name.replace(/\.md$/i, '').replace(/[^a-zA-Z0-9_]/g, '_');
        const descMatch = text.match(/^>\s*(.+)/m);
        const desc = descMatch ? descMatch[1].trim() : '';
        const bodyStart = text.indexOf('\n', text.indexOf('\n') + 1);
        const promptTemplate = bodyStart > 0 ? text.slice(bodyStart).trim() : text.trim();
        await createSkill({
            name: skillName,
            description: desc || `从 ${file.name} 导入`,
            prompt_template: promptTemplate,
            tools: [],
            memory_policy: 'none',
        });
        await loadSkills();
    } catch (err) {
        createSkillError.value = err.message || '上传失败';
        showCreateSkill.value = true;
    }
    event.target.value = '';
};

const loadSkills = async () => {
    loadingSkills.value = true;
    try {
        const data = await listSkills();
        skills.value = data.skills || [];
    } catch { skills.value = []; }
    loadingSkills.value = false;
};

const handleDeleteSkill = async (name) => {
    try {
        await deleteSkill(name);
        skills.value = skills.value.filter(s => s.name !== name);
    } catch {}
};

loadSkillEnabledState();

// === Memory Search ===
const memoryQuery = ref('');
const memoryKind = ref('');
const memoryResults = ref([]);
const searchingMemory = ref(false);
const handleSearchMemory = async () => {
    if (!memoryQuery.value.trim()) return;
    searchingMemory.value = true;
    try {
        const data = await searchMemory(memoryQuery.value, memoryKind.value || null);
        memoryResults.value = data.results || [];
    } catch { memoryResults.value = []; }
    searchingMemory.value = false;
};

const handleDeleteMemory = async (id) => {
    try {
        await deleteMemoryItem(id);
        memoryResults.value = memoryResults.value.filter(m => m.id !== id);
    } catch {}
};

// === Memory Create ===
const showAddMemory = ref(false);
const newMemoryContent = ref('');
const newMemoryKind = ref('episodic');
const newMemoryError = ref('');
const creatingMemory = ref(false);
const expandedMemoryId = ref(null);
const editingMemoryId = ref(null);
const editingMemoryContent = ref('');
const editingMemoryKind = ref('episodic');
const savingMemoryEdit = ref(false);

const handleCreateMemory = async () => {
    if (!newMemoryContent.value.trim()) {
        newMemoryError.value = '内容不能为空';
        return;
    }
    newMemoryError.value = '';
    creatingMemory.value = true;
    try {
        const result = await createMemory(newMemoryContent.value.trim(), newMemoryKind.value);
        if (result.status === 'success') {
            memoryResults.value.unshift(result.memory);
            newMemoryContent.value = '';
            newMemoryKind.value = 'episodic';
            showAddMemory.value = false;
        }
    } catch (e) {
        newMemoryError.value = '创建失败，请重试';
    }
    creatingMemory.value = false;
};

const toggleMemoryExpand = (id) => {
    expandedMemoryId.value = expandedMemoryId.value === id ? null : id;
};

const startEditMemory = (m) => {
    editingMemoryId.value = m.id;
    editingMemoryContent.value = m.content;
    editingMemoryKind.value = m.kind;
};
const cancelEditMemory = () => {
    editingMemoryId.value = null;
    editingMemoryContent.value = '';
};
const saveEditMemory = async () => {
    if (!editingMemoryContent.value.trim()) return;
    savingMemoryEdit.value = true;
    try {
        const result = await updateMemory(editingMemoryId.value, {
            content: editingMemoryContent.value.trim(),
            kind: editingMemoryKind.value,
        });
        if (result.status === 'success') {
            const idx = memoryResults.value.findIndex(m => m.id === editingMemoryId.value);
            if (idx >= 0) memoryResults.value[idx] = result.memory;
            editingMemoryId.value = null;
        }
    } catch (e) { /* ignore */ }
    savingMemoryEdit.value = false;
};

const memoryGrouped = computed(() => {
    const groups = {};
    const order = ['episodic', 'semantic', 'procedural'];
    for (const m of memoryResults.value) {
        if (!groups[m.kind]) groups[m.kind] = [];
        groups[m.kind].push(m);
    }
    const result = [];
    for (const k of order) {
        if (groups[k]) result.push({ kind: k, items: groups[k] });
    }
    return result;
});
const memoryKindLabel = (k) => ({ episodic: '情景', semantic: '语义', procedural: '程序' }[k] || k);
const memoryKindColor = (k) => ({
    episodic: 'bg-blue-100 text-blue-600',
    semantic: 'bg-green-100 text-green-600',
    procedural: 'bg-purple-100 text-purple-600',
}[k] || 'bg-gray-100 text-gray-600');

const formatRelativeTime = (dateStr) => {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        if (minutes < 1) return '刚刚';
        if (minutes < 60) return `${minutes}分钟前`;
        if (hours < 24) return `${hours}小时前`;
        if (days < 30) return `${days}天前`;
        return dateStr;
    } catch {
        return dateStr;
    }
};

// === Tools ===
const tools = ref([]);
const loadingTools = ref(false);
const expandedTool = ref('');
const loadTools = async () => {
    loadingTools.value = true;
    try {
        const data = await listTools();
        tools.value = data.tools || [];
    } catch { tools.value = []; }
    loadingTools.value = false;
};

const toggleTool = (name) => {
    expandedTool.value = expandedTool.value === name ? '' : name;
};

// === Tool Execution ===
const toolInputs = reactive({});
const toolLoading = ref('');
const toolResult = reactive({});
const toolError = reactive({});
const toolResultExpanded = reactive({});

const getToolInput = (toolName) => {
    if (!(toolName in toolInputs)) toolInputs[toolName] = '';
    return toolInputs[toolName];
};

const handleExecuteTool = async (tool) => {
    const query = (toolInputs[tool.name] || '').trim();
    if (!query) return;
    toolLoading.value = tool.name;
    toolError[tool.name] = '';
    toolResult[tool.name] = '';
    try {
        const data = await executeTool(tool.name, query);
        toolResult[tool.name] = data.result || JSON.stringify(data, null, 2);
    } catch (err) {
        toolError[tool.name] = err.message || '执行失败';
    } finally {
        toolLoading.value = '';
    }
};

const renderMd = (text) => {
    if (!text) return '';
    return md.render(text);
};

// Tab 切换时加载数据
watch(activeTab, (tab) => {
    if (tab === 'skills') { loadSkills(); loadAvailableTools(); }
    if (tab === 'tools') loadTools();
});

// === 用户偏好 ===
const STORAGE_KEY = 'iris_preferences';
const preferences = ref(JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'));
if (!preferences.value.style) preferences.value.style = 'detailed';
if (!preferences.value.language) preferences.value.language = 'zh';
if (!preferences.value.searchMode) preferences.value.searchMode = 'hybrid';

const styleOptions = [
    { value: 'detailed', label: '详细' },
    { value: 'concise', label: '简洁' },
    { value: 'formal', label: '正式' },
    { value: 'casual', label: '通俗' },
];
const langOptions = [
    { value: 'zh', label: '中文' },
    { value: 'en', label: 'English' },
];

const updatePref = (key, value) => {
    preferences.value[key] = value;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences.value));
};

const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
};

const formatTime = (ts) => {
    const d = new Date(ts);
    const diff = Date.now() - ts;
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    return `${d.getMonth() + 1}/${d.getDate()}`;
};
</script>
