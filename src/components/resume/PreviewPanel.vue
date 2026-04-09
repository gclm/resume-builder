<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useResumeStore } from '@/stores/resume'
import TemplatePickerDialog from '@/components/resume/TemplatePickerDialog.vue'
import {
  RESUME_TEMPLATES,
  getResumeTemplateByKey,
  type ResumeTemplateDefinition,
  type ResumeTemplateKey,
} from '@/templates/resume'
import { generateResumeMarkdown, downloadMarkdown } from '@/services/exportMarkdown'

const store = useResumeStore()
const resumeRef = ref<HTMLElement | null>(null)
const exporting = ref(false)
const exportProgress = ref(0)
const exportProgressText = ref('')
type ExportQualityMode = 'compressed' | 'hd'
const exportMenuOpen = ref(false)
const exportMenuRef = ref<HTMLElement | null>(null)
const templatePickerOpen = ref(false)
const jsonImportInputRef = ref<HTMLInputElement | null>(null)

const A4_WIDTH = 794
const A4_RATIO = 297 / 210
const A4_HEIGHT = Math.round(A4_WIDTH * A4_RATIO)
const pageBreaks = ref<number[]>([])

const fallbackTemplate: ResumeTemplateDefinition = getResumeTemplateByKey('default')
const currentTemplate = computed<ResumeTemplateDefinition>(
  () => getResumeTemplateByKey(store.selectedTemplateKey) ?? fallbackTemplate
)
const currentTemplateComponent = computed(() => currentTemplate.value.component)
const a4TemplateLabel = computed(() => `A4 / ${currentTemplate.value.name}`)

function waitNextFrame(): Promise<void> {
  return new Promise((resolve) => requestAnimationFrame(() => resolve()))
}

async function setExportProgress(percent: number, text: string) {
  exportProgress.value = Math.max(0, Math.min(100, Math.round(percent)))
  exportProgressText.value = text
  await nextTick()
  await waitNextFrame()
}

function findEffectiveCanvasHeight(canvas: HTMLCanvasElement): number {
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  if (!ctx) return canvas.height

  const width = canvas.width
  const sampleStepX = Math.max(1, Math.floor(width / 120))

  const rowHasContent = (y: number): boolean => {
    const row = ctx.getImageData(0, y, width, 1).data
    for (let x = 0; x < width; x += sampleStepX) {
      const idx = x * 4
      const alpha = row[idx + 3] ?? 0
      if (alpha === 0) continue
      const r = row[idx] ?? 255
      const g = row[idx + 1] ?? 255
      const b = row[idx + 2] ?? 255
      if (r < 248 || g < 248 || b < 248) return true
    }
    return false
  }

  let roughY = -1
  for (let y = canvas.height - 1; y >= 0; y -= 4) {
    if (rowHasContent(y)) {
      roughY = y
      break
    }
  }

  if (roughY < 0) return 1

  const startY = Math.min(canvas.height - 1, roughY + 3)
  const endY = Math.max(0, roughY - 3)
  for (let y = startY; y >= endY; y -= 1) {
    if (rowHasContent(y)) return Math.min(canvas.height, y + 4)
  }

  return Math.min(canvas.height, roughY + 4)
}

function updatePageBreaks() {
  if (!resumeRef.value) return
  const contentHeight = resumeRef.value.scrollHeight
  const pageHeight = Math.round((resumeRef.value.clientWidth || A4_WIDTH) * A4_RATIO)
  const breaks: number[] = []
  const totalPages = Math.max(1, Math.ceil((contentHeight - 1) / pageHeight))
  for (let i = 1; i < totalPages; i += 1) {
    breaks.push(Math.round(i * pageHeight))
  }
  pageBreaks.value = breaks
}

function openTemplatePicker() {
  templatePickerOpen.value = true
  exportMenuOpen.value = false
}

function chooseTemplate(key: ResumeTemplateKey) {
  store.setTemplate(key)
  templatePickerOpen.value = false
}

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  nextTick(() => updatePageBreaks())
  if (resumeRef.value) {
    resizeObserver = new ResizeObserver(() => updatePageBreaks())
    resizeObserver.observe(resumeRef.value)
  }
  document.addEventListener('mousedown', handleDocumentPointerDown)
})

watch(
  () => [
    JSON.stringify(store.modules),
    JSON.stringify(store.basicInfo),
    JSON.stringify(store.educationList),
    store.skills,
    JSON.stringify(store.workList),
    JSON.stringify(store.projectList),
    JSON.stringify(store.awardList),
    store.selfIntro,
    store.selectedTemplateKey,
  ],
  () => {
    nextTick(() => updatePageBreaks())
  }
)

onUnmounted(() => {
  resizeObserver?.disconnect()
  document.removeEventListener('mousedown', handleDocumentPointerDown)
})

function handleExportTriggerClick() {
  if (exporting.value) return
  exportMenuOpen.value = !exportMenuOpen.value
}

function handleExportTriggerEnter() {
  if (exporting.value) return
  exportMenuOpen.value = true
}

function handleDocumentPointerDown(event: MouseEvent) {
  const target = event.target as Node | null
  if (!target || !exportMenuRef.value) return
  if (!exportMenuRef.value.contains(target)) {
    exportMenuOpen.value = false
  }
}

function handleExportMarkdown() {
  exportMenuOpen.value = false
  const md = generateResumeMarkdown(store)
  const name = store.basicInfo.name?.trim() || '简历'
  downloadMarkdown(`${name}_简历.md`, md)
}

function handleExportJson() {
  exportMenuOpen.value = false
  const name = store.basicInfo.name?.trim() || '简历'
  const blob = new Blob([store.exportResumeData()], {
    type: 'application/json;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${name}_简历.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

async function handleImportJson(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const raw = await file.text()
  input.value = ''
  store.importResumeData(raw)
}

async function exportPDF(mode: ExportQualityMode) {
  if (!resumeRef.value) return
  exporting.value = true
  exportMenuOpen.value = false
  exportProgress.value = 0
  exportProgressText.value = '准备导出...'
  const isHdMode = mode === 'hd'
  const sourceNode = resumeRef.value
  const exportHost = document.createElement('div')
  exportHost.style.position = 'fixed'
  exportHost.style.left = '-10000px'
  exportHost.style.top = '0'
  exportHost.style.width = `${A4_WIDTH}px`
  exportHost.style.pointerEvents = 'none'
  exportHost.style.opacity = '0'
  exportHost.style.zIndex = '-1'

  const exportNode = sourceNode.cloneNode(true) as HTMLElement
  exportNode.classList.add('pdf-exporting')
  exportNode.style.width = `${A4_WIDTH}px`
  exportNode.style.minHeight = '0'
  exportNode.style.height = 'auto'
  exportNode.style.margin = '0'
  exportNode.style.overflow = 'hidden'

  exportHost.appendChild(exportNode)
  document.body.appendChild(exportHost)

  try {
    await setExportProgress(8, '准备导出资源...')
    await document.fonts?.ready
    await setExportProgress(18, '加载导出引擎...')
    const [{ default: html2canvas }, { jsPDF }] = await Promise.all([import('html2canvas'), import('jspdf')])
    await setExportProgress(36, '正在渲染简历画布...')
    const exportScale = isHdMode ? Math.min(4, Math.max(3, window.devicePixelRatio || 1)) : 2
    const canvas = await html2canvas(exportNode, {
      scale: exportScale,
      useCORS: true,
      width: A4_WIDTH,
      windowWidth: A4_WIDTH,
      backgroundColor: '#ffffff',
      scrollX: 0,
      scrollY: 0,
    })
    await setExportProgress(68, '正在分页生成 PDF...')

    const pdf = new jsPDF({
      unit: 'mm',
      format: 'a4',
      orientation: 'portrait',
      compress: !isHdMode,
    })

    const pagePixelHeight = Math.round(canvas.width * A4_RATIO)
    const effectiveHeight = findEffectiveCanvasHeight(canvas)
    const totalPages = Math.max(1, Math.ceil(effectiveHeight / pagePixelHeight))
    let offsetY = 0
    let pageIndex = 0

    while (offsetY < effectiveHeight - 1) {
      const remainingHeight = effectiveHeight - offsetY
      const sliceHeight = Math.min(pagePixelHeight, remainingHeight)
      if (sliceHeight <= 2) break

      const pageCanvas = document.createElement('canvas')
      pageCanvas.width = canvas.width
      pageCanvas.height = sliceHeight
      const ctx = pageCanvas.getContext('2d')
      if (!ctx) break
      ctx.imageSmoothingEnabled = true
      ctx.imageSmoothingQuality = 'high'
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, pageCanvas.width, pageCanvas.height)
      ctx.drawImage(canvas, 0, offsetY, canvas.width, sliceHeight, 0, 0, canvas.width, sliceHeight)

      const imgData = isHdMode ? pageCanvas.toDataURL('image/png') : pageCanvas.toDataURL('image/jpeg', 0.92)
      const imgWidthMm = 210
      const imgHeightMm = (sliceHeight / canvas.width) * imgWidthMm

      if (pageIndex > 0) pdf.addPage('a4', 'portrait')
      pdf.addImage(imgData, isHdMode ? 'PNG' : 'JPEG', 0, 0, imgWidthMm, imgHeightMm, undefined, isHdMode ? 'NONE' : 'FAST')
      const pageProgress = 68 + Math.round((Math.min(pageIndex + 1, totalPages) / totalPages) * 28)
      await setExportProgress(pageProgress, `正在写入第 ${Math.min(pageIndex + 1, totalPages)}/${totalPages} 页...`)

      offsetY += sliceHeight
      pageIndex += 1
    }

    await setExportProgress(98, '正在保存文件...')
    pdf.save(`${store.basicInfo.name || '简历'}_resume.pdf`)
    await setExportProgress(100, '导出完成')
  } catch (err) {
    console.error('PDF export failed:', err)
  } finally {
    exportHost.remove()
    exportProgress.value = 0
    exportProgressText.value = ''
    exporting.value = false
  }
}
</script>

<template>
  <aside class="preview-panel">
    <div class="preview-top">
      <div class="preview-title-row">
        <span class="preview-title">实时预览</span>
        <button class="template-trigger" @click="openTemplatePicker">
          <span class="template-trigger-label">切换模板</span>
          <span class="template-trigger-name">{{ currentTemplate.name }}</span>
          <span class="template-trigger-arrow">▾</span>
        </button>
        <span class="a4-badge">{{ a4TemplateLabel }}</span>
      </div>
      <div
        ref="exportMenuRef"
        class="export-actions export-dropdown"
        @mouseenter="handleExportTriggerEnter"
      >
        <button class="btn-export" :disabled="exporting" @click="handleExportTriggerClick">
          {{ exporting ? '导出中...' : '导出' }}
        </button>
        <div v-if="exportMenuOpen && !exporting" class="export-menu">
          <button class="export-menu-item" @click="exportPDF('hd')">导出高清 PDF</button>
          <button class="export-menu-item" @click="exportPDF('compressed')">导出压缩 PDF</button>
          <button class="export-menu-item" @click="handleExportMarkdown">导出 Markdown</button>
          <button class="export-menu-item" @click="handleExportJson">导出 JSON 进度</button>
          <button class="export-menu-item" @click="exportMenuOpen = false; jsonImportInputRef?.click()">导入 JSON 进度</button>
        </div>
      </div>
    </div>
    <div v-if="exporting" class="export-progress">
      <div class="export-progress-head">
        <span class="export-progress-text">{{ exportProgressText || '导出中...' }}</span>
        <span class="export-progress-percent">{{ exportProgress }}%</span>
      </div>
      <div class="export-progress-track">
        <span class="export-progress-fill" :style="{ width: `${exportProgress}%` }"></span>
      </div>
    </div>
    <input
      ref="jsonImportInputRef"
      type="file"
      accept=".json,application/json"
      style="display: none"
      @change="handleImportJson"
    />

    <TemplatePickerDialog
      v-model="templatePickerOpen"
      :templates="RESUME_TEMPLATES"
      :selected-key="store.selectedTemplateKey"
      @select="chooseTemplate"
    />

    <div class="preview-scroll">
      <div class="paper-wrapper" :style="{ width: `${A4_WIDTH}px` }">
        <div ref="resumeRef" class="paper" :style="{ width: `${A4_WIDTH}px`, minHeight: `${A4_HEIGHT}px` }">
          <component :is="currentTemplateComponent" />
        </div>

        <div v-for="(pos, idx) in pageBreaks" :key="idx" class="page-line" :style="{ top: `${pos}px` }">
          <span>第{{ idx + 2 }}页</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.preview-panel {
  box-sizing: border-box;
  width: 812px;
  max-width: 812px;
  min-width: 0;
  flex: 0 0 812px;
  height: 100%;
  border-left: 1px solid #e4d8cb;
  background: #efe7dc;
  padding: 4px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.preview-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.preview-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.preview-title {
  color: #2d2521;
  font-size: 16px;
  font-weight: 700;
}

.template-trigger {
  height: 30px;
  padding: 0 10px 0 8px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border-radius: 8px;
  border: 1px solid #e0d2c1;
  background: #fff;
  color: #2d2521;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  outline: none;
  box-shadow: 0 1px 0 rgba(45, 37, 33, 0.06);
  transition: background-color 0.12s ease, border-color 0.12s ease, box-shadow 0.12s ease;
}

.template-trigger:hover {
  border-color: #cdbba7;
  background: #faf6f0;
  box-shadow: 0 4px 12px rgba(45, 37, 33, 0.1);
}

.template-trigger-label {
  height: 20px;
  padding: 0 6px;
  border-radius: 6px;
  background: #2d2521;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
}

.template-trigger-name {
  color: #2d2521;
  font-size: 12px;
  font-weight: 700;
  max-width: 180px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.template-trigger-arrow {
  color: #7b6a5b;
  font-size: 11px;
  line-height: 1;
}

.a4-badge {
  height: 24px;
  padding: 0 8px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e9ded0;
  color: #7b6a5b;
  font-size: 11px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}

.btn-export {
  border: none;
  height: 30px;
  padding: 0 10px;
  border-radius: 8px;
  background: #2d2521;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
}

.btn-export:disabled {
  opacity: 0.7;
  cursor: wait;
}

.export-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.export-dropdown {
  position: relative;
}

.export-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 124px;
  padding: 4px;
  border-radius: 8px;
  border: 1px solid #e9ded0;
  background: #fff;
  box-shadow: 0 10px 20px rgba(45, 37, 33, 0.14);
  z-index: 12;
}

.export-menu-item {
  width: 100%;
  border: none;
  border-radius: 6px;
  background: #fff;
  color: #2d2521;
  font-size: 12px;
  font-weight: 600;
  text-align: left;
  padding: 7px 8px;
  cursor: pointer;
  transition: background-color 0.12s ease, color 0.12s ease;
}

.export-menu-item:hover {
  background: #eadccf;
  color: #1f1916;
}

.export-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 10px;
  border: 1px solid #e9ded0;
  border-radius: 8px;
  background: #fff8f2;
}

.export-progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.export-progress-text {
  font-size: 12px;
  color: #7b6a5b;
  font-weight: 600;
}

.export-progress-percent {
  font-size: 12px;
  color: #2d2521;
  font-weight: 700;
}

.export-progress-track {
  position: relative;
  width: 100%;
  height: 6px;
  border-radius: 999px;
  background: #eedfce;
  overflow: hidden;
}

.export-progress-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #d97745 0%, #c96a3b 100%);
  transition: width 0.18s ease;
}

.preview-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0;
}

.paper-wrapper {
  position: relative;
  margin: 0 auto;
  padding-bottom: 8px;
}

.paper {
  box-sizing: border-box;
  background: #fff;
  border: 1px solid #d8dde6;
  border-radius: 4px;
  color: #000;
  box-shadow: 0 12px 24px rgba(45, 37, 33, 0.1);
}

.paper.pdf-exporting {
  box-shadow: none;
  border: none;
  border-radius: 0;
  min-height: 0 !important;
}

.page-line {
  position: absolute;
  left: 16px;
  right: 16px;
  transform: translateY(-6px);
  display: flex;
  align-items: center;
  gap: 8px;
  pointer-events: none;
  z-index: 2;
}

.page-line::before,
.page-line::after {
  content: '';
  flex: 1;
  height: 1px;
  border-top: 1px dashed #d97745;
}

.page-line span {
  color: #d97745;
  font-size: 10px;
  font-weight: 600;
  background: #efe7dc;
  padding: 0 4px;
}
</style>
