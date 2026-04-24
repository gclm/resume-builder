<!-- author: jf -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import { uploadKnowledgeAssets, type RagUploadFileResult, type RagUploadResponse } from '@/api/ragApi'

type LocalUploadItem = RagUploadFileResult & {
  fileSize: number
}

type UploadPhase = 'idle' | 'ready' | 'uploading' | 'completed' | 'error'

type CompactMetric = {
  label: string
  value: string
}

type GuidanceFact = {
  label: string
  value: string
}

const ACCEPT = '.pdf,.txt,.md,.docx,.png,.jpg,.jpeg,.webp'
const selectedFiles = ref<File[]>([])
const uploadItems = ref<LocalUploadItem[]>([])
const uploadSummary = ref<RagUploadResponse | null>(null)
const errorMessage = ref('')
const isUploading = ref(false)
const isDragOver = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
let abortController: AbortController | null = null

const hasFiles = computed(() => selectedFiles.value.length > 0)
const hasUploadItems = computed(() => uploadItems.value.length > 0)
const totalFiles = computed(() => uploadSummary.value?.totalFiles ?? selectedFiles.value.length)
const succeededFiles = computed(() => uploadSummary.value?.succeededFiles ?? 0)
const failedFiles = computed(() => uploadSummary.value?.failedFiles ?? 0)
const insertedChunks = computed(() => uploadSummary.value?.inserted ?? 0)
const totalSelectedSize = computed(() => selectedFiles.value.reduce((sum, file) => sum + file.size, 0))
const totalSelectedSizeLabel = computed(() => formatFileSize(totalSelectedSize.value))

const uploadPhase = computed<UploadPhase>(() => {
  if (isUploading.value) return 'uploading'
  if (errorMessage.value) return 'error'
  if (uploadSummary.value) return 'completed'
  if (selectedFiles.value.length > 0) return 'ready'
  return 'idle'
})

const phaseLabel = computed(() => {
  switch (uploadPhase.value) {
    case 'ready':
      return '待上传'
    case 'uploading':
      return '处理中'
    case 'completed':
      return '已完成'
    case 'error':
      return '失败'
    default:
      return '未开始'
  }
})

const headerText = computed(() => {
  switch (uploadPhase.value) {
    case 'ready':
      return `已选择 ${totalFiles.value} 个文件，确认后即可开始本批次入库。`
    case 'uploading':
      return `正在处理 ${totalFiles.value} 个文件，结果会直接在当前工作区更新。`
    case 'completed':
      return `本批次处理完成，成功 ${succeededFiles.value} 个，失败 ${failedFiles.value} 个。`
    case 'error':
      return errorMessage.value || '本次上传未完成，请重新选择文件后继续。'
    default:
      return '统一处理文档上传、图片 OCR 和分块入库。'
  }
})

const compactSummary = computed(() => {
  switch (uploadPhase.value) {
    case 'ready':
      return `已选 ${totalFiles.value} 个文件，共 ${totalSelectedSizeLabel.value}`
    case 'uploading':
      return `正在处理 ${totalFiles.value} 个文件`
    case 'completed':
      return `本批次已完成，成功 ${succeededFiles.value}，失败 ${failedFiles.value}`
    case 'error':
      return '上传未完成，请处理错误后重新选择文件'
    default:
      return '文档与图片可混合上传，结果会在下方直接更新'
  }
})

const compactMetrics = computed<CompactMetric[]>(() => [
  { label: '文件', value: String(totalFiles.value) },
  { label: '成功/失败', value: `${succeededFiles.value}/${failedFiles.value}` },
  { label: 'Chunk', value: String(insertedChunks.value) },
])

const resultSectionTitle = computed(() => {
  switch (uploadPhase.value) {
    case 'completed':
      return '处理结果'
    case 'uploading':
      return '当前进度'
    case 'error':
      return '错误与结果'
    default:
      return '当前批次'
  }
})

const emptyStateTitle = computed(() => {
  if (uploadPhase.value === 'error') return '本次上传未完成'
  return '从这里开始整理知识库资料'
})

const emptyStateText = computed(() => {
  if (uploadPhase.value === 'error') {
    return errorMessage.value || '请重新选择文件并再次发起上传。'
  }
  return '选择文件后，会在这里直接看到当前批次和处理结果。'
})

const guidanceFacts: GuidanceFact[] = [
  { label: '支持格式', value: 'PDF / TXT / MD / DOCX / PNG / JPG / JPEG / WEBP' },
  { label: '单文件限制', value: '10 MB' },
  { label: '写入目标', value: 'pgvector' },
  { label: '支持类型', value: '文档 / 图片' },
]

const ingestNotes = [
  '文档：直接解析文本后分块入库',
  '图片：先 OCR，再进入同一分块链路',
]

function openFilePicker() {
  if (isUploading.value) return
  fileInputRef.value?.click()
}

function onFileChange(event: Event) {
  if (isUploading.value) return
  const input = event.target as HTMLInputElement
  syncSelectedFiles(input.files ? Array.from(input.files) : [])
  input.value = ''
}

function onDrop(event: DragEvent) {
  event.preventDefault()
  isDragOver.value = false
  if (isUploading.value) return
  syncSelectedFiles(event.dataTransfer?.files ? Array.from(event.dataTransfer.files) : [])
}

function syncSelectedFiles(files: File[]) {
  if (files.length === 0) return
  const baseFiles = uploadPhase.value === 'ready' ? selectedFiles.value : []
  selectedFiles.value = dedupeFiles([...baseFiles, ...files])
  resetUploadFeedback()
  syncPendingUploadItems()
}

function removeFile(index: number) {
  if (isUploading.value) return
  selectedFiles.value = selectedFiles.value.filter((_, itemIndex) => itemIndex !== index)
  resetUploadFeedback()
  syncPendingUploadItems()
}

function clearFiles() {
  if (isUploading.value) return
  selectedFiles.value = []
  uploadItems.value = []
  resetUploadFeedback()
}

async function handleUpload() {
  if (!hasFiles.value || isUploading.value) return

  isUploading.value = true
  resetUploadFeedback()
  abortController = new AbortController()
  uploadItems.value = selectedFiles.value.map((file) => createPendingItem(file, 'uploading'))

  try {
    const response = await uploadKnowledgeAssets(selectedFiles.value, abortController.signal)
    uploadSummary.value = response
    uploadItems.value = response.files.map((item) => ({
      ...item,
      fileSize: selectedFiles.value.find((file) => file.name === item.fileName)?.size ?? 0,
    }))
  } catch (error) {
    const message = error instanceof Error ? error.message : '知识库上传失败'
    errorMessage.value = message
    uploadItems.value = []
    selectedFiles.value = []
  } finally {
    isUploading.value = false
    abortController = null
  }
}

function cancelUpload() {
  abortController?.abort()
}

function resetUploadFeedback() {
  uploadSummary.value = null
  errorMessage.value = ''
}

function syncPendingUploadItems() {
  uploadItems.value = selectedFiles.value.map((file) => createPendingItem(file, 'pending'))
}

function createPendingItem(file: File, status: string): LocalUploadItem {
  const sourceType = guessSourceType(file.name)
  return {
    fileName: file.name,
    contentType: file.type || 'application/octet-stream',
    sourceType,
    ingestSource: sourceType === 'image' ? 'image_ocr_text' : 'text_document',
    chunkCount: 0,
    insertedCount: 0,
    status,
    errorMessage: null,
    fileSize: file.size,
  }
}

function dedupeFiles(files: File[]): File[] {
  const map = new Map<string, File>()
  for (const file of files) {
    map.set(`${file.name}:${file.size}:${file.lastModified}`, file)
  }
  return Array.from(map.values())
}

function guessSourceType(fileName: string): string {
  const extension = fileName.split('.').pop()?.toLowerCase() ?? ''
  return ['png', 'jpg', 'jpeg', 'webp'].includes(extension) ? 'image' : 'document'
}

function formatFileSize(size: number): string {
  if (size <= 0) return '0 B'
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(2)} MB`
  if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${size} B`
}

function sourceTypeLabel(sourceType: string): string {
  return sourceType === 'image' ? '图片' : '文档'
}

function ingestSourceLabel(ingestSource: string): string {
  if (ingestSource === 'image_ocr_text') return 'OCR 入库'
  if (ingestSource === 'text_document') return '文本入库'
  return ingestSource
}

function statusLabel(status: string): string {
  if (status === 'success') return '成功'
  if (status === 'failed') return '失败'
  if (status === 'uploading') return '处理中'
  return '待上传'
}
</script>

<template>
  <section class="knowledge-panel">
    <div class="panel-shell">
      <header class="page-header">
        <div class="header-copy">
          <p class="eyebrow">Knowledge Base</p>
          <h1>知识库上传与入库</h1>
          <p class="header-text">{{ headerText }}</p>
        </div>
        <div class="header-status">
          <span class="phase-pill" :class="`phase-${uploadPhase}`">{{ phaseLabel }}</span>
          <span v-if="hasFiles || uploadSummary" class="batch-pill">{{ totalFiles }} 个文件</span>
        </div>
      </header>

      <div class="workspace-layout">
        <section class="panel main-card">
          <div class="card-head">
            <div>
              <p class="section-label">Upload Workspace</p>
              <h2>上传与结果</h2>
            </div>
          </div>

          <div
            class="dropzone"
            :class="{ 'is-drag-over': isDragOver, 'is-disabled': isUploading }"
            @dragenter.prevent="isUploading ? undefined : (isDragOver = true)"
            @dragover.prevent="isUploading ? undefined : (isDragOver = true)"
            @dragleave.prevent="isDragOver = false"
            @drop="onDrop"
          >
            <input
              ref="fileInputRef"
              class="file-input"
              type="file"
              multiple
              :accept="ACCEPT"
              @change="onFileChange"
            />
            <div class="dropzone-icon" aria-hidden="true">KB</div>
            <h3>拖拽文件到这里，或手动选择资料</h3>
            <p>文档与图片可混合上传，处理结果会在下方直接更新。</p>
          </div>

          <div class="panel-toolbar">
            <button class="primary-btn" type="button" :disabled="isUploading" @click="openFilePicker">
              选择文件
            </button>
            <button class="ghost-btn" type="button" :disabled="!hasFiles || isUploading" @click="clearFiles">
              清空列表
            </button>
            <button class="ghost-btn" type="button" :disabled="!hasFiles || isUploading" @click="handleUpload">
              开始上传
            </button>
            <button v-if="isUploading" class="ghost-btn danger-btn" type="button" @click="cancelUpload">
              取消上传
            </button>
          </div>

          <div class="compact-bar">
            <p class="compact-summary">{{ compactSummary }}</p>
            <ul class="metric-list">
              <li v-for="metric in compactMetrics" :key="metric.label" class="metric-item">
                <span class="metric-label">{{ metric.label }}</span>
                <strong>{{ metric.value }}</strong>
              </li>
            </ul>
          </div>

          <p v-if="errorMessage" class="panel-error">{{ errorMessage }}</p>

          <div class="result-block">
            <div class="result-head">
              <h3>{{ resultSectionTitle }}</h3>
              <span v-if="hasUploadItems" class="section-count-chip">{{ uploadItems.length }} 项</span>
            </div>

            <div v-if="!hasUploadItems" class="results-empty" :class="{ 'is-error': uploadPhase === 'error' }">
              <div class="empty-mark">KB</div>
              <h3>{{ emptyStateTitle }}</h3>
              <p>{{ emptyStateText }}</p>
            </div>

            <ul v-else class="result-list">
              <li v-for="(item, index) in uploadItems" :key="`${item.fileName}-${index}`" class="result-item">
                <div class="result-main">
                  <div class="result-heading">
                    <div>
                      <p class="file-name">{{ item.fileName }}</p>
                      <p class="file-meta">
                        {{ sourceTypeLabel(item.sourceType) }} · {{ formatFileSize(item.fileSize) }} ·
                        {{ ingestSourceLabel(item.ingestSource) }}
                      </p>
                    </div>
                    <span class="status-pill" :class="`status-${item.status}`">{{ statusLabel(item.status) }}</span>
                  </div>

                  <div class="file-submeta">
                    <span>chunk {{ item.chunkCount }}</span>
                    <span>入库 {{ item.insertedCount }}</span>
                  </div>

                  <p v-if="item.errorMessage" class="file-error">{{ item.errorMessage }}</p>
                </div>

                <button
                  v-if="uploadPhase === 'ready'"
                  class="remove-btn"
                  type="button"
                  aria-label="移除文件"
                  @click="removeFile(index)"
                >
                  移除
                </button>
              </li>
            </ul>
          </div>
        </section>

        <aside class="panel guidance-card">
          <div class="guidance-head">
            <p class="section-label">Guidance</p>
            <h2>处理说明</h2>
            <p>稳定规则集中放在这里，不在主工作区重复出现。</p>
          </div>

          <dl class="guidance-facts">
            <div v-for="fact in guidanceFacts" :key="fact.label" class="fact-row">
              <dt>{{ fact.label }}</dt>
              <dd>{{ fact.value }}</dd>
            </div>
          </dl>

          <div class="guidance-flow">
            <h3>入库路径</h3>
            <ul>
              <li v-for="note in ingestNotes" :key="note">{{ note }}</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  </section>
</template>

<style scoped>
.knowledge-panel {
  --kb-bg: #f3ede6;
  --kb-bg-soft: #f8f4ee;
  --kb-surface: rgba(255, 252, 248, 0.95);
  --kb-border: rgba(122, 91, 68, 0.12);
  --kb-border-strong: rgba(122, 91, 68, 0.18);
  --kb-text: #2d241e;
  --kb-text-soft: #6f5a4c;
  --kb-text-muted: #8f7868;
  --kb-accent: #c9794e;
  --kb-accent-soft: rgba(201, 121, 78, 0.12);
  --kb-success-soft: rgba(68, 145, 110, 0.14);
  --kb-success-text: #2f7b58;
  --kb-error-soft: rgba(186, 88, 67, 0.14);
  --kb-error-text: #a84839;
  --kb-pending-soft: rgba(116, 101, 90, 0.12);
  --kb-pending-text: #6d5a4e;
  --kb-shadow: 0 18px 36px rgba(80, 57, 41, 0.08);
  flex: 1;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  overflow: auto;
  background:
    radial-gradient(circle at top left, rgba(239, 214, 189, 0.45), transparent 24%),
    linear-gradient(180deg, var(--kb-bg) 0%, var(--kb-bg-soft) 100%);
}

.panel-shell {
  min-height: 100%;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel {
  border-radius: 24px;
  border: 1px solid var(--kb-border);
  background: var(--kb-surface);
  box-shadow: var(--kb-shadow);
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 22px;
  border-radius: 24px;
  border: 1px solid var(--kb-border-strong);
  background:
    radial-gradient(circle at top left, rgba(243, 220, 199, 0.38), transparent 28%),
    linear-gradient(135deg, rgba(249, 244, 238, 0.98), rgba(241, 233, 223, 0.94));
}

.header-copy {
  min-width: 0;
  max-width: 720px;
}

.eyebrow,
.section-label {
  margin: 0 0 8px;
  color: #9e6d4d;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.page-header h1,
.card-head h2,
.guidance-head h2 {
  margin: 0;
  color: var(--kb-text);
}

.page-header h1 {
  font-size: 30px;
  line-height: 1.12;
}

.header-text,
.guidance-head p,
.results-empty p,
.file-meta,
.file-error,
.guidance-flow li {
  color: var(--kb-text-soft);
  font-size: 13px;
  line-height: 1.65;
}

.header-text {
  margin: 10px 0 0;
}

.header-status {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.phase-pill,
.batch-pill,
.status-pill,
.section-count-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.phase-pill,
.batch-pill {
  background: rgba(255, 255, 255, 0.82);
  color: var(--kb-text-soft);
  border: 1px solid rgba(122, 91, 68, 0.08);
}

.phase-ready,
.phase-idle {
  background: var(--kb-pending-soft);
  color: var(--kb-pending-text);
  border-color: transparent;
}

.phase-uploading {
  background: var(--kb-accent-soft);
  color: #ab643b;
  border-color: transparent;
}

.phase-completed {
  background: var(--kb-success-soft);
  color: var(--kb-success-text);
  border-color: transparent;
}

.phase-error {
  background: var(--kb-error-soft);
  color: var(--kb-error-text);
  border-color: transparent;
}

.workspace-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(300px, 0.78fr);
  gap: 16px;
  align-items: start;
}

.main-card,
.guidance-card {
  padding: 20px;
}

.main-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-head,
.guidance-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-head h2,
.guidance-head h2 {
  font-size: 22px;
  line-height: 1.2;
}

.dropzone {
  min-height: 188px;
  border: 1.5px dashed rgba(170, 132, 104, 0.42);
  border-radius: 22px;
  padding: 24px 18px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  text-align: center;
  background:
    linear-gradient(135deg, rgba(255, 246, 236, 0.94), rgba(251, 247, 242, 0.94)),
    repeating-linear-gradient(
      -45deg,
      rgba(201, 121, 78, 0.025),
      rgba(201, 121, 78, 0.025) 12px,
      rgba(255, 255, 255, 0.02) 12px,
      rgba(255, 255, 255, 0.02) 24px
    );
  transition: border-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease;
}

.dropzone.is-drag-over {
  border-color: var(--kb-accent);
  transform: translateY(-1px);
  box-shadow: 0 14px 26px rgba(201, 121, 78, 0.12);
}

.dropzone.is-disabled {
  opacity: 0.7;
}

.file-input {
  display: none;
}

.dropzone-icon,
.empty-mark {
  width: 54px;
  height: 54px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #e7ddd2, #f5efe9);
  color: var(--kb-text);
  font-size: 17px;
  font-weight: 800;
  letter-spacing: 0.08em;
  box-shadow: 0 10px 18px rgba(80, 57, 41, 0.08);
}

.dropzone h3,
.result-head h3,
.results-empty h3,
.guidance-flow h3 {
  margin: 0;
  color: var(--kb-text);
}

.dropzone h3 {
  font-size: 18px;
}

.dropzone p {
  margin: 0;
  max-width: 520px;
  color: var(--kb-text-soft);
  font-size: 13px;
  line-height: 1.6;
}

.panel-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.primary-btn,
.ghost-btn,
.remove-btn {
  border: none;
  cursor: pointer;
  transition: transform 0.18s ease, background-color 0.18s ease, color 0.18s ease, opacity 0.18s ease;
}

.primary-btn,
.ghost-btn {
  min-height: 42px;
  padding: 0 16px;
  border-radius: 14px;
  font-size: 14px;
  font-weight: 700;
}

.primary-btn {
  background: var(--kb-accent);
  color: #fff;
}

.ghost-btn {
  background: #efe7dd;
  color: var(--kb-text-soft);
}

.danger-btn {
  background: rgba(186, 88, 67, 0.1);
  color: var(--kb-error-text);
}

.primary-btn:hover:not(:disabled),
.ghost-btn:hover:not(:disabled),
.remove-btn:hover {
  transform: translateY(-1px);
}

.primary-btn:disabled,
.ghost-btn:disabled {
  opacity: 0.58;
  cursor: not-allowed;
  transform: none;
}

.compact-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid var(--kb-border);
  background: rgba(255, 255, 255, 0.84);
}

.compact-summary {
  margin: 0;
  color: var(--kb-text);
  font-size: 14px;
  font-weight: 700;
  line-height: 1.5;
}

.metric-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  min-width: min(100%, 340px);
}

.metric-item {
  padding: 10px 12px;
  border-radius: 16px;
  background: rgba(248, 242, 236, 0.88);
  text-align: center;
}

.metric-label {
  display: block;
  color: var(--kb-text-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.metric-item strong {
  display: block;
  margin-top: 6px;
  color: var(--kb-text);
  font-size: 22px;
  line-height: 1;
}

.panel-error {
  margin: 0;
  color: var(--kb-error-text);
  font-size: 13px;
  font-weight: 700;
}

.result-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.result-head h3 {
  font-size: 18px;
  line-height: 1.2;
}

.section-count-chip {
  color: var(--kb-text-soft);
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--kb-border);
}

.results-empty {
  border-radius: 20px;
  border: 1px solid var(--kb-border);
  background:
    linear-gradient(135deg, rgba(249, 243, 236, 0.85), rgba(255, 255, 255, 0.8)),
    repeating-linear-gradient(
      -45deg,
      rgba(201, 121, 78, 0.02),
      rgba(201, 121, 78, 0.02) 12px,
      rgba(255, 255, 255, 0.02) 12px,
      rgba(255, 255, 255, 0.02) 24px
    );
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  text-align: center;
  padding: 20px;
}

.results-empty.is-error {
  border-color: rgba(186, 88, 67, 0.18);
  background: linear-gradient(135deg, rgba(252, 242, 239, 0.88), rgba(255, 255, 255, 0.8));
}

.result-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.result-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid var(--kb-border);
  background: rgba(255, 255, 255, 0.84);
}

.result-main {
  flex: 1;
  min-width: 0;
}

.result-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.file-name {
  margin: 0;
  color: var(--kb-text);
  font-size: 15px;
  font-weight: 800;
  line-height: 1.45;
}

.file-meta {
  margin: 4px 0 0;
}

.file-submeta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

.file-submeta span {
  color: var(--kb-text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.status-pill {
  padding-inline: 10px;
}

.status-success {
  background: var(--kb-success-soft);
  color: var(--kb-success-text);
}

.status-failed {
  background: var(--kb-error-soft);
  color: var(--kb-error-text);
}

.status-uploading {
  background: var(--kb-accent-soft);
  color: #ab643b;
}

.status-pending {
  background: var(--kb-pending-soft);
  color: var(--kb-pending-text);
}

.file-error {
  margin: 10px 0 0;
  color: var(--kb-error-text);
}

.remove-btn {
  padding: 0;
  background: transparent;
  color: #b1633d;
  font-size: 12px;
  font-weight: 700;
}

.guidance-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.guidance-facts {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.fact-row {
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(248, 242, 236, 0.86);
}

.fact-row dt {
  margin: 0;
  color: var(--kb-text-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.fact-row dd {
  margin: 6px 0 0;
  color: var(--kb-text);
  font-size: 14px;
  font-weight: 700;
  line-height: 1.5;
}

.guidance-flow {
  padding: 14px 16px;
  border-radius: 18px;
  background:
    radial-gradient(circle at top left, rgba(240, 218, 196, 0.28), transparent 30%),
    linear-gradient(135deg, rgba(250, 245, 239, 0.98), rgba(244, 237, 228, 0.92));
}

.guidance-flow ul {
  margin: 10px 0 0;
  padding-left: 18px;
}

@media (max-width: 1120px) {
  .workspace-layout {
    grid-template-columns: minmax(0, 1.35fr) minmax(260px, 0.8fr);
  }

  .compact-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .metric-list {
    width: 100%;
    min-width: 0;
  }
}

@media (max-width: 960px) {
  .panel-shell {
    padding: 16px;
  }

  .workspace-layout {
    grid-template-columns: 1fr;
  }

  .page-header,
  .main-card,
  .guidance-card {
    padding: 18px;
  }
}

@media (max-width: 720px) {
  .panel-shell {
    padding: 14px;
  }

  .page-header,
  .main-card,
  .guidance-card,
  .results-empty,
  .result-item,
  .compact-bar {
    border-radius: 20px;
  }

  .page-header,
  .result-heading,
  .result-item,
  .panel-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .page-header h1 {
    font-size: 28px;
  }

  .header-status,
  .panel-toolbar {
    width: 100%;
  }

  .primary-btn,
  .ghost-btn {
    width: 100%;
  }

  .metric-list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .dropzone {
    min-height: 172px;
    padding: 20px 16px;
  }
}
</style>
