<script setup lang="ts">
// author: jf
import { computed, onMounted, onUnmounted, reactive, ref, type Component } from 'vue'
import { useResumeStore } from '@/stores/resume'
import BasicInfoEditor from './editors/BasicInfoEditor.vue'
import EducationEditor from './editors/EducationEditor.vue'
import SkillsEditor from './editors/SkillsEditor.vue'
import WorkExperienceEditor from './editors/WorkExperienceEditor.vue'
import ProjectExperienceEditor from './editors/ProjectExperienceEditor.vue'
import AwardsEditor from './editors/AwardsEditor.vue'
import SelfIntroEditor from './editors/SelfIntroEditor.vue'
import AiOptimizePanel from '@/components/ai/AiOptimizePanel.vue'
import { getModuleIconPaths, MODULE_ICON_VIEWBOX } from '@/constants/moduleIcons'

const store = useResumeStore()
const showSaved = ref(false)
const searchValue = ref('')
const showAiPanel = ref(false)
const moduleMenuOpen = ref(false)
const moduleMenuRef = ref<HTMLElement | null>(null)
const jsonImportInputRef = ref<HTMLInputElement | null>(null)
const draggingModuleKey = ref<string | null>(null)
const dragOverModuleKey = ref<string | null>(null)
const nowTick = ref(Date.now())

function handleAiClick() {
  showAiPanel.value = true
}

function toggleModuleMenu() {
  moduleMenuOpen.value = !moduleMenuOpen.value
}

function handleDocumentPointerDown(event: MouseEvent) {
  const target = event.target as Node | null
  if (!target || !moduleMenuRef.value) return
  if (!moduleMenuRef.value.contains(target)) {
    moduleMenuOpen.value = false
  }
}

const expanded = reactive<Record<string, boolean>>({
  basicInfo: true,
  education: false,
  skills: false,
  workExperience: false,
  projectExperience: false,
  awards: false,
  selfIntro: false,
})

const editorMap: Record<string, Component> = {
  basicInfo: BasicInfoEditor,
  education: EducationEditor,
  skills: SkillsEditor,
  workExperience: WorkExperienceEditor,
  projectExperience: ProjectExperienceEditor,
  awards: AwardsEditor,
  selfIntro: SelfIntroEditor,
}

const visibleCount = computed(() => store.modules.filter((m) => m.visible).length)
const searchKeyword = computed(() => searchValue.value.trim())
const filteredModules = computed(() =>
  store.modules.filter((m) => (searchKeyword.value ? m.label.includes(searchKeyword.value) : true))
)

function hasTextContent(value: string | undefined): boolean {
  if (!value) return false
  const text = value
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .trim()
  return text.length > 0
}

function countFilled(values: Array<string | undefined>): number {
  return values.reduce((count, value) => count + (value?.trim() ? 1 : 0), 0)
}

function scoreByFilled(values: Array<string | undefined>): number {
  if (values.length === 0) return 0
  return countFilled(values) / values.length
}

const moduleCompletion = computed<Record<string, number>>(() => {
  const basic = store.basicInfo

  const basicInfoScore = scoreByFilled([
    basic.name,
    basic.phone,
    basic.email,
    basic.jobTitle,
    basic.expectedLocation,
    basic.educationLevel,
  ])

  const firstEducation = store.educationList.find((e) =>
    [e.school, e.major, e.degree, e.startDate].some((value) => value?.trim())
  )
  const educationScore = firstEducation
    ? scoreByFilled([firstEducation.school, firstEducation.major, firstEducation.degree, firstEducation.startDate])
    : 0

  const firstWork = store.workList.find((w) =>
    [w.company, w.position, w.startDate, w.description].some((value) => value?.trim())
  )
  const workScore = firstWork
    ? scoreByFilled([firstWork.company, firstWork.position, firstWork.startDate, firstWork.description])
    : 0

  const firstProject = store.projectList.find((p) =>
    [p.name, p.role, p.startDate, p.mainWork].some((value) => value?.trim())
  )
  const projectScore = firstProject
    ? scoreByFilled([firstProject.name, firstProject.role, firstProject.startDate, firstProject.mainWork])
    : 0

  const firstAward = store.awardList.find((a) => [a.name, a.date].some((value) => value?.trim()))
  const awardsScore = firstAward ? scoreByFilled([firstAward.name, firstAward.date]) : 0

  return {
    basicInfo: basicInfoScore,
    education: educationScore,
    skills: hasTextContent(store.skills) ? 1 : 0,
    workExperience: workScore,
    projectExperience: projectScore,
    awards: awardsScore,
    selfIntro: hasTextContent(store.selfIntro) ? 1 : 0,
  }
})

const completionPercent = computed(() => {
  const enabledModules = store.modules.filter((m) => m.visible)
  if (enabledModules.length === 0) return 0
  const total = enabledModules.reduce((sum, mod) => sum + (moduleCompletion.value[mod.key] ?? 0), 0)
  return Math.round((total / enabledModules.length) * 100)
})

function handleSave() {
  store.saveToStorage()
  showSaved.value = true
  setTimeout(() => {
    showSaved.value = false
  }, 1800)
}

function triggerJsonImport() {
  jsonImportInputRef.value?.click()
}

async function handleImportJson(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const raw = await file.text()
  input.value = ''
  store.importResumeData(raw)
}

const isAutoSavePending = computed(() => store.nextAutoSaveAt !== null)
const autoSaveChipText = computed(() => {
  if (store.isSaving) {
    return '自动保存中...'
  }

  const nextAt = store.nextAutoSaveAt
  if (nextAt) {
    const remainMs = Math.max(nextAt - nowTick.value, 0)
    const remainSec = Math.max(remainMs / 1000, 0.1)
    return `${remainSec.toFixed(1)}秒后自动保存`
  }

  const savedAt = store.lastSavedAt
  if (!savedAt) {
    return `自动保存间隔 ${Math.max(store.autoSaveDelayMs / 1000, 0.1).toFixed(1)}秒`
  }

  const elapsedMs = Math.max(nowTick.value - savedAt, 0)
  const label = store.lastSaveMode === 'manual' ? '手动保存' : '自动保存'
  if (elapsedMs < 2_000) return `刚刚${label}`
  if (elapsedMs < 60_000) return `${Math.floor(elapsedMs / 1000)}秒前${label}`
  return `${Math.floor(elapsedMs / 60_000)}分钟前${label}`
})

const isDefaultOrder = computed(() => store.isDefaultModuleOrder())

function handleResetOrder() {
  store.resetModuleOrder()
}

function toggleExpand(key: string) {
  expanded[key] = !expanded[key]
}

function moduleIconPaths(key: string): string[] {
  return getModuleIconPaths(key)
}

function canMoveUp(key: string): boolean {
  return store.canMoveModule(key, 'up')
}

function canMoveDown(key: string): boolean {
  return store.canMoveModule(key, 'down')
}

function moveUp(key: string) {
  store.moveModule(key, 'up')
}

function moveDown(key: string) {
  store.moveModule(key, 'down')
}

function handleSwitchDragStart(event: DragEvent, key: string) {
  if (key === 'basicInfo') {
    event.preventDefault()
    return
  }
  draggingModuleKey.value = key
  event.dataTransfer?.setData('text/plain', key)
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

function handleSwitchDragOver(event: DragEvent, key: string) {
  if (!draggingModuleKey.value || draggingModuleKey.value === key) return
  event.preventDefault()
  dragOverModuleKey.value = key
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function handleSwitchDrop(targetKey: string) {
  const sourceKey = draggingModuleKey.value
  if (!sourceKey || sourceKey === targetKey) return
  store.reorderModule(sourceKey, targetKey)
  dragOverModuleKey.value = null
}

function handleSwitchDragEnd() {
  draggingModuleKey.value = null
  dragOverModuleKey.value = null
}

let autoSaveTicker: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  autoSaveTicker = setInterval(() => {
    nowTick.value = Date.now()
  }, 200)
  document.addEventListener('mousedown', handleDocumentPointerDown)
})

onUnmounted(() => {
  if (autoSaveTicker) {
    clearInterval(autoSaveTicker)
    autoSaveTicker = null
  }
  document.removeEventListener('mousedown', handleDocumentPointerDown)
})
</script>

<template>
  <main class="editor-panel">
    <div class="editor-toolbar">
      <input v-model="searchValue" class="search-input" placeholder="搜索模块：基本信息 / 教育经历 / 专业技能" />
      <span
        class="chip"
        :class="{ 'chip-pending': isAutoSavePending, 'chip-saving': store.isSaving }"
        :title="autoSaveChipText"
        :aria-label="autoSaveChipText"
        role="status"
        aria-live="polite"
      >
        <span v-if="store.isSaving" class="chip-loading" aria-hidden="true"></span>
        <svg v-else class="chip-status-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 7v5l3 2" />
          <circle cx="12" cy="12" r="8" />
        </svg>
      </span>
    </div>

    <div ref="moduleMenuRef" class="floating-tools">
      <div class="floating-tools-stack">
        <div class="module-switch-anchor">
          <button
            class="floating-tool-btn module-tool-btn"
            type="button"
            :aria-expanded="moduleMenuOpen"
            aria-haspopup="menu"
            aria-label="模块开关"
            title="模块开关"
            @click="toggleModuleMenu"
          >
            <svg class="btn-module-switch-icon" viewBox="0 0 24 24" aria-hidden="true">
              <path
                fill-rule="evenodd"
                clip-rule="evenodd"
                d="M10.65 2.45c-.18.06-.31.21-.35.4l-.42 2.28a7.2 7.2 0 0 0-1.32.76l-2.2-.76a.58.58 0 0 0-.58.14L4.22 6.83a.58.58 0 0 0-.14.58l.76 2.2c-.3.42-.55.86-.76 1.32l-2.28.42a.55.55 0 0 0-.45.54v2.22c0 .26.19.49.45.54l2.28.42c.2.46.46.9.76 1.32l-.76 2.2c-.07.2-.02.43.14.58l1.56 1.56c.15.16.38.21.58.14l2.2-.76c.42.3.86.55 1.32.76l.42 2.28c.04.26.28.45.54.45h2.22c.26 0 .5-.19.54-.45l.42-2.28a7.2 7.2 0 0 0 1.32-.76l2.2.76c.2.07.43.02.58-.14l1.56-1.56a.58.58 0 0 0 .14-.58l-.76-2.2c.3-.42.55-.86.76-1.32l2.28-.42a.55.55 0 0 0 .45-.54v-2.22a.55.55 0 0 0-.45-.54l-2.28-.42a7.2 7.2 0 0 0-.76-1.32l.76-2.2a.58.58 0 0 0-.14-.58l-1.56-1.56a.58.58 0 0 0-.58-.14l-2.2.76a7.2 7.2 0 0 0-1.32-.76l-.42-2.28a.55.55 0 0 0-.54-.45h-2.22c-.07 0-.13.01-.19.03ZM12 15.35a3.35 3.35 0 1 0 0-6.7 3.35 3.35 0 0 0 0 6.7Z"
              />
            </svg>
            <span class="floating-badge">{{ visibleCount }}</span>
          </button>
          <div v-if="moduleMenuOpen" class="module-switch-popover">
            <div class="module-switch-popover-header">
              <p class="module-switch-popover-title">选择展示模块</p>
              <button
                class="btn-reset-order-icon"
                type="button"
                :disabled="isDefaultOrder"
                aria-label="恢复默认顺序"
                title="恢复默认顺序"
                @click="handleResetOrder"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M20 11a8 8 0 1 1-2.34-5.66" />
                  <path d="M20 4v7h-7" />
                </svg>
              </button>
            </div>
            <ul class="module-switch-list">
              <li
                v-for="mod in store.modules"
                :key="`switch-${mod.key}`"
                class="module-switch-item"
                :class="{
                  active: mod.visible,
                  muted: !mod.visible,
                  draggable: mod.key !== 'basicInfo',
                  dragging: draggingModuleKey === mod.key,
                  'drag-over': dragOverModuleKey === mod.key,
                }"
                :draggable="mod.key !== 'basicInfo'"
                @dragstart="handleSwitchDragStart($event, mod.key)"
                @dragover="handleSwitchDragOver($event, mod.key)"
                @drop.prevent="handleSwitchDrop(mod.key)"
                @dragend="handleSwitchDragEnd"
              >
                <div class="module-switch-info">
                  <span v-if="mod.key !== 'basicInfo'" class="drag-handle" aria-hidden="true" title="拖拽排序">⋮⋮</span>
                  <span class="module-switch-icon" aria-hidden="true">
                    <svg class="module-switch-icon-svg" :viewBox="MODULE_ICON_VIEWBOX">
                      <path v-for="(d, idx) in moduleIconPaths(mod.key)" :key="`switch-${mod.key}-${idx}`" :d="d" />
                    </svg>
                  </span>
                  <span class="module-switch-label">{{ mod.label }}</span>
                </div>

                <div class="module-switch-actions">
                  <div v-if="mod.key !== 'basicInfo' && mod.visible" class="order-actions order-actions-switch">
                    <button class="order-btn" :disabled="!canMoveUp(mod.key)" @click.stop="moveUp(mod.key)">↑</button>
                    <button class="order-btn" :disabled="!canMoveDown(mod.key)" @click.stop="moveDown(mod.key)">↓</button>
                  </div>
                  <label class="toggle-switch">
                    <input
                      type="checkbox"
                      :checked="mod.visible"
                      :aria-label="`${mod.label}开关`"
                      @change="store.toggleModule(mod.key)"
                    />
                    <span class="toggle-slider"></span>
                  </label>
                </div>
              </li>
            </ul>
          </div>
        </div>
        <button
          class="floating-tool-btn ai-tool-btn"
          type="button"
          aria-label="AI优化建议"
          title="AI优化建议"
          @click="handleAiClick"
        >
          <span class="ai-tool-text">AI</span>
        </button>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-card">
        <p class="stat-label">简历完整度</p>
        <p class="stat-value">{{ completionPercent }}%</p>
      </div>
      <div class="stat-card">
        <p class="stat-label">模块已启用</p>
        <p class="stat-value">{{ visibleCount }} / {{ store.modules.length }}</p>
      </div>
    </div>

    <section class="info-editor">
      <div class="info-editor-header">
        <div class="editor-title-row">
          <h2 class="editor-title">信息编辑区</h2>
          <span class="storage-tip-wrap">
            <button
              class="storage-tip-trigger"
              type="button"
              aria-label="查看简历本地存储提示"
              aria-describedby="resume-storage-tooltip"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 11v5" />
                <path d="M12 8h.01" />
              </svg>
            </button>
            <span id="resume-storage-tooltip" class="storage-tooltip" role="tooltip">
              简历编辑不存储任何个人数据，存储到您本人浏览器缓存里，如果您删除浏览器缓存可能造成数据丢失，建议您编辑完先导出 json 后续可直接导入恢复。
            </span>
          </span>
        </div>
        <div class="editor-header-actions">
          <button class="btn-import" type="button" @click="triggerJsonImport">导入 JSON</button>
          <button class="btn-save" @click="handleSave">保存草稿</button>
        </div>
      </div>
      <p class="editor-subtitle">模块顺序与模块开关一致，点击右侧可展开/收起</p>
      <input
        ref="jsonImportInputRef"
        type="file"
        accept=".json,application/json"
        style="display: none"
        @change="handleImportJson"
      />
      <transition name="fade">
        <p v-if="showSaved" class="save-hint">已保存</p>
      </transition>

      <div class="module-sections">
        <article
          v-for="mod in filteredModules"
          :key="mod.key"
          class="module-block"
          :class="{ disabled: !mod.visible }"
        >
	          <header class="module-head" @click="toggleExpand(mod.key)">
	            <div class="module-head-left">
	              <span class="module-head-icon" aria-hidden="true">
	                <svg class="module-head-icon-svg" :viewBox="MODULE_ICON_VIEWBOX">
	                  <path v-for="(d, idx) in moduleIconPaths(mod.key)" :key="`${mod.key}-${idx}`" :d="d" />
	                </svg>
	              </span>
	              <span class="module-head-title">{{ mod.label }}</span>
	            </div>
            <div class="module-head-right">
              <span v-if="!mod.visible" class="disabled-tag">已关闭</span>
              <span class="expand-text">{{ expanded[mod.key] && mod.visible ? '收起' : '展开' }} ▸</span>
            </div>
          </header>

          <div v-if="expanded[mod.key] && mod.visible" class="module-body">
            <component :is="editorMap[mod.key]" />
          </div>
        </article>

        <div v-if="filteredModules.length === 0" class="empty-result">没有匹配的模块</div>
      </div>
    </section>

    <AiOptimizePanel
      :open="showAiPanel"
      @close="showAiPanel = false"
    />
  </main>
</template>

<style scoped src="./EditorPanel.css"></style>
<style scoped src="./EditorPanel.responsive.css"></style>
