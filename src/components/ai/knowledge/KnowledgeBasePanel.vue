<!-- author: jf -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import { uploadKnowledgeAssets, type RagUploadFileResult, type RagUploadResponse } from '@/api/ragApi'

type LocalUploadItem = RagUploadFileResult & {
  fileSize: number
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
const summaryText = computed(() => {
  if (!uploadSummary.value) return '尚未执行上传'
  return `本次共处理 ${uploadSummary.value.totalFiles} 个文件，成功 ${uploadSummary.value.succeededFiles} 个，失败 ${uploadSummary.value.failedFiles} 个，写入 ${uploadSummary.value.inserted} 条 chunk。`
})

function openFilePicker() {
  fileInputRef.value?.click()
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  syncSelectedFiles(input.files ? Array.from(input.files) : [])
  input.value = ''
}

function onDrop(event: DragEvent) {
  event.preventDefault()
  isDragOver.value = false
  syncSelectedFiles(event.dataTransfer?.files ? Array.from(event.dataTransfer.files) : [])
}

function syncSelectedFiles(files: File[]) {
  selectedFiles.value = dedupeFiles([...selectedFiles.value, ...files])
  uploadItems.value = selectedFiles.value.map((file) => createPendingItem(file, 'pending'))
}

function removeFile(index: number) {
  selectedFiles.value.splice(index, 1)
  uploadItems.value.splice(index, 1)
}

function clearFiles() {
  if (isUploading.value) return
  selectedFiles.value = []
  uploadItems.value = []
  uploadSummary.value = null
  errorMessage.value = ''
}

async function handleUpload() {
  if (!hasFiles.value || isUploading.value) return

  isUploading.value = true
  errorMessage.value = ''
  uploadSummary.value = null
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
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(2)} MB`
  if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${size} B`
}

function statusLabel(status: string): string {
  if (status === 'success') return '成功'
  if (status === 'failed') return '失败'
  if (status === 'uploading') return '进行中'
  return '待上传'
}
</script>

<template>
  <section class="knowledge-panel">
    <div class="panel-shell">
      <header class="panel-header">
        <div>
          <p class="eyebrow">Knowledge Base</p>
          <h1>统一上传与图片 OCR 入库</h1>
          <p class="header-copy">
            单次支持文档与图片混合上传。图片会先做 OCR 转 Markdown，再进入分块和向量入库链路。
          </p>
        </div>
        <div class="header-badges">
          <span class="badge">支持 PDF / TXT / MD / DOCX</span>
          <span class="badge accent">支持 PNG / JPG / JPEG / WEBP</span>
        </div>
      </header>

      <div class="panel-grid">
        <section class="upload-card">
          <div
            class="dropzone"
            :class="{ 'is-drag-over': isDragOver }"
            @dragenter.prevent="isDragOver = true"
            @dragover.prevent="isDragOver = true"
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
            <div class="dropzone-icon" aria-hidden="true">⇪</div>
            <h2>拖拽文件到这里，或手动选择</h2>
            <p>同一批次允许图片与文档混合提交。默认单文件大小限制 10MB。</p>
            <div class="dropzone-actions">
              <button class="primary-btn" type="button" @click="openFilePicker">选择文件</button>
              <button class="ghost-btn" type="button" :disabled="!hasFiles || isUploading" @click="clearFiles">
                清空列表
              </button>
            </div>
          </div>

          <div class="selection-meta">
            <span>已选择 {{ selectedFiles.length }} 个文件</span>
            <span v-if="isUploading">上传进行中</span>
            <span v-else>等待提交</span>
          </div>

          <ul v-if="uploadItems.length > 0" class="file-list">
            <li v-for="(item, index) in uploadItems" :key="`${item.fileName}-${index}`" class="file-item">
              <div class="file-main">
                <div>
                  <p class="file-name">{{ item.fileName }}</p>
                  <p class="file-meta">
                    {{ item.sourceType === 'image' ? '图片 OCR' : '文本解析' }} · {{ formatFileSize(item.fileSize) }}
                  </p>
                </div>
                <span class="status-pill" :class="`status-${item.status}`">{{ statusLabel(item.status) }}</span>
              </div>
              <div class="file-submeta">
                <span>chunk {{ item.chunkCount }}</span>
                <span>入库 {{ item.insertedCount }}</span>
                <span>{{ item.ingestSource }}</span>
              </div>
              <p v-if="item.errorMessage" class="file-error">{{ item.errorMessage }}</p>
              <button
                v-if="!isUploading"
                class="remove-btn"
                type="button"
                aria-label="移除文件"
                @click="removeFile(index)"
              >
                移除
              </button>
            </li>
          </ul>

          <div class="submit-row">
            <button class="primary-btn wide" type="button" :disabled="!hasFiles || isUploading" @click="handleUpload">
              {{ isUploading ? '正在提交...' : '开始上传入库' }}
            </button>
            <button v-if="isUploading" class="ghost-btn" type="button" @click="cancelUpload">取消</button>
          </div>
          <p v-if="errorMessage" class="panel-error">{{ errorMessage }}</p>
        </section>

        <section class="summary-card">
          <div class="summary-block">
            <p class="summary-label">处理摘要</p>
            <p class="summary-text">{{ summaryText }}</p>
          </div>

          <div class="stats-grid">
            <article class="stat-card">
              <span class="stat-label">总文件数</span>
              <strong>{{ uploadSummary?.totalFiles ?? selectedFiles.length }}</strong>
            </article>
            <article class="stat-card">
              <span class="stat-label">成功</span>
              <strong>{{ uploadSummary?.succeededFiles ?? 0 }}</strong>
            </article>
            <article class="stat-card">
              <span class="stat-label">失败</span>
              <strong>{{ uploadSummary?.failedFiles ?? 0 }}</strong>
            </article>
            <article class="stat-card accent-card">
              <span class="stat-label">写入 chunk</span>
              <strong>{{ uploadSummary?.inserted ?? 0 }}</strong>
            </article>
          </div>

          <div class="tips-card">
            <h3>入库策略</h3>
            <ul>
              <li>文档文件直接解析文本，保留原始文件名和 content-type 元数据。</li>
              <li>图片文件先走 Responses API OCR，产出结构优先 Markdown。</li>
              <li>所有内容统一分块、生成 Embedding，并写入 pgvector 存储接口。</li>
            </ul>
          </div>
        </section>
      </div>
    </div>
  </section>
</template>

<style scoped>
.knowledge-panel {
  flex: 1;
  min-width: 0;
  overflow: auto;
  background:
    radial-gradient(circle at top left, rgba(255, 222, 187, 0.9), transparent 28%),
    linear-gradient(180deg, #f6efe5 0%, #f9f5ee 100%);
}

.panel-shell {
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 24px;
  border-radius: 24px;
  border: 1px solid rgba(217, 119, 69, 0.18);
  background: rgba(255, 251, 246, 0.92);
  box-shadow: 0 18px 40px rgba(70, 49, 33, 0.08);
}

.eyebrow {
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #af6a3f;
  text-transform: uppercase;
}

.panel-header h1 {
  margin: 0;
  color: #2f261f;
  font-size: 32px;
  line-height: 1.1;
}

.header-copy {
  margin: 12px 0 0;
  max-width: 720px;
  color: #66574d;
  font-size: 15px;
  line-height: 1.7;
}

.header-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

.badge {
  padding: 9px 14px;
  border-radius: 999px;
  background: #f3e2d3;
  color: #7f5e48;
  font-size: 12px;
  font-weight: 700;
}

.badge.accent {
  background: #d97745;
  color: #fff;
}

.panel-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(320px, 0.9fr);
  gap: 22px;
}

.upload-card,
.summary-card {
  border-radius: 24px;
  padding: 22px;
  background: rgba(255, 251, 247, 0.96);
  border: 1px solid #e8dbce;
  box-shadow: 0 18px 38px rgba(66, 45, 31, 0.08);
}

.dropzone {
  border: 1.5px dashed #d7bda8;
  border-radius: 22px;
  padding: 36px 24px;
  background:
    linear-gradient(135deg, rgba(255, 243, 229, 0.9), rgba(250, 246, 241, 0.9)),
    repeating-linear-gradient(
      -45deg,
      rgba(217, 119, 69, 0.03),
      rgba(217, 119, 69, 0.03) 12px,
      rgba(255, 255, 255, 0.02) 12px,
      rgba(255, 255, 255, 0.02) 24px
    );
  text-align: center;
  transition: border-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
}

.dropzone.is-drag-over {
  border-color: #d97745;
  transform: translateY(-1px);
  box-shadow: 0 16px 34px rgba(217, 119, 69, 0.14);
}

.file-input {
  display: none;
}

.dropzone-icon {
  width: 58px;
  height: 58px;
  margin: 0 auto 16px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  background: #2f261f;
  color: #fff;
  font-size: 26px;
  box-shadow: 0 12px 24px rgba(47, 38, 31, 0.18);
}

.dropzone h2 {
  margin: 0;
  color: #2f261f;
  font-size: 22px;
}

.dropzone p {
  margin: 12px auto 0;
  max-width: 520px;
  color: #6d5d52;
  font-size: 14px;
  line-height: 1.7;
}

.dropzone-actions,
.submit-row {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: center;
  margin-top: 20px;
}

.primary-btn,
.ghost-btn,
.remove-btn {
  border: none;
  cursor: pointer;
  transition: transform 0.18s ease, background-color 0.18s ease, color 0.18s ease;
}

.primary-btn {
  padding: 12px 18px;
  border-radius: 14px;
  background: #d97745;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
}

.primary-btn:hover:not(:disabled),
.ghost-btn:hover:not(:disabled),
.remove-btn:hover {
  transform: translateY(-1px);
}

.primary-btn:disabled,
.ghost-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  transform: none;
}

.primary-btn.wide {
  min-width: 220px;
}

.ghost-btn {
  padding: 12px 16px;
  border-radius: 14px;
  background: #efe6db;
  color: #6c594c;
  font-size: 14px;
  font-weight: 700;
}

.selection-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin: 18px 4px 0;
  color: #816d5e;
  font-size: 13px;
  font-weight: 600;
}

.file-list {
  list-style: none;
  margin: 18px 0 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.file-item {
  padding: 16px;
  border-radius: 18px;
  background: #fcfaf7;
  border: 1px solid #ebdfd4;
}

.file-main,
.file-submeta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.file-name {
  margin: 0;
  color: #302620;
  font-size: 15px;
  font-weight: 700;
}

.file-meta,
.file-error,
.summary-text,
.tips-card li {
  margin: 6px 0 0;
  color: #6a5b50;
  font-size: 13px;
  line-height: 1.6;
}

.file-submeta {
  margin-top: 10px;
  color: #8a7667;
  font-size: 12px;
  font-weight: 600;
}

.status-pill {
  padding: 7px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.status-success {
  background: rgba(64, 144, 109, 0.14);
  color: #2b7d58;
}

.status-failed {
  background: rgba(196, 88, 69, 0.13);
  color: #b44736;
}

.status-uploading {
  background: rgba(217, 119, 69, 0.14);
  color: #c3683a;
}

.status-pending {
  background: rgba(122, 108, 97, 0.12);
  color: #6c594c;
}

.remove-btn {
  margin-top: 12px;
  padding: 0;
  background: transparent;
  color: #b85f38;
  font-size: 12px;
  font-weight: 700;
}

.panel-error {
  margin: 14px 0 0;
  color: #b44736;
  font-size: 13px;
  font-weight: 600;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.summary-block,
.tips-card {
  padding: 18px;
  border-radius: 18px;
  background: #f9f4ee;
  border: 1px solid #ecdfd0;
}

.summary-label,
.stat-label {
  display: block;
  margin-bottom: 8px;
  color: #8a7461;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.stat-card {
  padding: 18px;
  border-radius: 18px;
  background: #fff;
  border: 1px solid #ebdfd2;
}

.stat-card strong {
  color: #2f261f;
  font-size: 28px;
}

.accent-card {
  background: linear-gradient(135deg, #2f261f, #5d4330);
  border-color: transparent;
}

.accent-card .stat-label,
.accent-card strong {
  color: #fff;
}

.tips-card h3 {
  margin: 0 0 12px;
  color: #2f261f;
  font-size: 18px;
}

.tips-card ul {
  padding-left: 18px;
  margin: 0;
}

@media (max-width: 1180px) {
  .panel-grid {
    grid-template-columns: 1fr;
  }

  .header-badges {
    justify-content: flex-start;
  }
}

@media (max-width: 720px) {
  .panel-shell {
    padding: 16px;
  }

  .panel-header,
  .upload-card,
  .summary-card {
    padding: 18px;
    border-radius: 20px;
  }

  .panel-header {
    flex-direction: column;
  }

  .panel-header h1 {
    font-size: 28px;
  }

  .dropzone-actions,
  .submit-row,
  .selection-meta,
  .file-main,
  .file-submeta {
    flex-direction: column;
    align-items: flex-start;
  }

  .primary-btn.wide {
    width: 100%;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
