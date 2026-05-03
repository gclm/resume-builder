<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import type { InterviewMode, InterviewRequestState } from '@/services/interviewService'
import type { ChatMessage } from '@/components/ai/interview/types'

// author: jf
const props = defineProps<{
  mode: InterviewMode
  messages: ChatMessage[]
  isLoading: boolean
  errorMsg: string
  inputText: string
  canSend: boolean
  isListening: boolean
  requestState: InterviewRequestState
  requestStatusText: string
  composerHintText: string
  streamingAssistantMessageId: string | null
  sessionStarted: boolean
  timerText: string
  timerStatusText: string
  currentRound: number
  userTurns: number
  assistantTurns: number
  canToggleVoice: boolean
  canStart: boolean
  canTogglePause: boolean
  canFinish: boolean
  sessionFinished: boolean
  timerRunning: boolean
  speechState: 'idle' | 'connecting' | 'connected' | 'transcribing'
  speechStatusText: string
  showControls?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:inputText', value: string): void
  (e: 'start'): void
  (e: 'togglePause'): void
  (e: 'finish'): void
  (e: 'reset'): void
  (e: 'adjustDuration', delta: number): void
  (e: 'send'): void
  (e: 'toggleVoice'): void
}>()

const chatListRef = ref<HTMLElement | null>(null)
const answerInputRef = ref<HTMLTextAreaElement | null>(null)
const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: false,
})

const assistantName = computed(() => (props.mode === 'candidate' ? 'AI面试官' : 'AI候选人'))
const pauseButtonLabel = computed(() => (props.timerRunning ? '暂停' : '继续'))
const isComposerBusy = computed(() =>
  props.isLoading || ['submitting', 'accepted', 'processing', 'responding'].includes(props.requestState)
)
const isSpeechActive = computed(() => ['connecting', 'connected', 'transcribing'].includes(props.speechState))
const composerPlaceholder = computed(() => {
  if (!props.sessionStarted) {
    return '点击“开始”后，系统会生成第一轮问题或候选人开场回答'
  }
  if (props.sessionFinished) {
    return '当前会话已结束'
  }
  return props.mode === 'candidate'
    ? '输入你的回答，AI 面试官会继续追问'
    : '输入你希望候选人回答的内容或追问方向'
})

function normalizeAssistantContent(content: string): string {
  const text = content?.trim() || ''
  if (!text) return ''

  try {
    const jsonText = (() => {
      if (text.startsWith('{') && text.endsWith('}')) return text
      const first = text.indexOf('{')
      const last = text.lastIndexOf('}')
      if (first >= 0 && last > first) return text.slice(first, last + 1)
      return ''
    })()

    if (!jsonText) return text
    const parsed = JSON.parse(jsonText) as { assistantReply?: unknown }
    if (typeof parsed.assistantReply === 'string' && parsed.assistantReply.trim()) {
      return parsed.assistantReply
    }
  } catch {
    // Keep raw content when it is not valid JSON.
  }

  return text
}

function renderMarkdown(content: string): string {
  return markdown.render(normalizeAssistantContent(content))
}

function handleInputKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter') return
  if ((event as KeyboardEvent & { isComposing?: boolean }).isComposing) return

  if (event.ctrlKey) {
    return
  }

  event.preventDefault()
  if (props.canSend) emit('send')
}

function handleComposerSubmit() {
  if (props.canSend) emit('send')
}

function syncTextareaHeight() {
  const textarea = answerInputRef.value
  if (!textarea) return

  const isCompactViewport = window.matchMedia('(max-width: 768px)').matches
  const isNarrowViewport = window.matchMedia('(max-width: 480px)').matches
  const minHeight = props.sessionFinished ? (isCompactViewport ? 34 : 72) : isNarrowViewport ? 52 : isCompactViewport ? 64 : 116
  const maxHeight = props.sessionFinished ? (isCompactViewport ? 48 : 120) : isCompactViewport ? 120 : 220

  textarea.style.height = '0px'
  textarea.style.height = `${Math.min(Math.max(textarea.scrollHeight, minHeight), maxHeight)}px`
}

function scrollToBottom() {
  if (!chatListRef.value) return
  chatListRef.value.scrollTop = chatListRef.value.scrollHeight
}

function isPendingAssistantMessage(item: ChatMessage): boolean {
  return (
    item.role === 'assistant' &&
    props.streamingAssistantMessageId === item.id &&
    ['submitting', 'accepted', 'processing'].includes(props.requestState)
  )
}

function isStreamingAssistantMessage(item: ChatMessage): boolean {
  return item.role === 'assistant' && props.streamingAssistantMessageId === item.id && props.requestState === 'responding'
}

watch(
  () => ({
    inputText: props.inputText,
    requestState: props.requestState,
    messages: props.messages.map((item) => `${item.id}:${item.content}`).join('\u0001'),
  }),
  async () => {
    await nextTick()
    syncTextareaHeight()
    scrollToBottom()
  }
)

onMounted(() => {
  syncTextareaHeight()
})
</script>

<template>
  <section class="simulation-panel">
    <section v-if="showControls !== false" class="card controls-card">
      <div class="controls-top">
        <div>
          <p class="card-title">面试控制台</p>
          <p class="card-helper">你可以调整时长并控制会话状态</p>
        </div>
        <span class="status-pill" :class="{ active: timerRunning }">
          {{ timerStatusText }}
        </span>
      </div>

      <div class="timer-row">
        <span class="timer-label">时长</span>
        <button type="button" class="mini-btn" @click="emit('adjustDuration', -5)">-5m</button>
        <span class="timer-value">{{ timerText }}</span>
        <button type="button" class="mini-btn" @click="emit('adjustDuration', 5)">+5m</button>

        <button
          v-if="canStart"
          type="button"
          class="action-btn primary"
          :disabled="isLoading"
          @click="emit('start')"
        >
          开始
        </button>
        <button
          v-else
          type="button"
          class="action-btn"
          :disabled="!canTogglePause"
          @click="emit('togglePause')"
        >
          {{ pauseButtonLabel }}
        </button>

        <button type="button" class="action-btn danger" :disabled="!canFinish" @click="emit('finish')">
          结束并评分
        </button>
        <button type="button" class="action-btn ghost" :disabled="isLoading" @click="emit('reset')">
          重置
        </button>
      </div>
    </section>

    <section class="card qa-card">
      <div class="qa-header">
        <p class="card-title">模拟面试问答</p>
        <p class="qa-meta">轮次 {{ currentRound }} · 你 {{ userTurns }} 条 · AI {{ assistantTurns }} 条</p>
      </div>

      <p v-if="errorMsg" class="error-text">{{ errorMsg }}</p>

      <div ref="chatListRef" class="chat-list">
        <p v-if="messages.length === 0" class="chat-empty">
          点击“开始”后，系统会基于简历生成第一轮问题或候选人开场回答。
        </p>

        <article
          v-for="item in messages"
          :key="item.id"
          class="chat-item"
          :class="[
            item.role === 'assistant' ? 'assistant' : 'user',
            {
              pending: isPendingAssistantMessage(item),
              streaming: isStreamingAssistantMessage(item),
            },
          ]"
        >
          <p class="chat-role">{{ item.role === 'assistant' ? assistantName : '你' }}</p>
          <template v-if="item.role === 'assistant'">
            <div v-if="isPendingAssistantMessage(item)" class="assistant-status">
              <span class="assistant-status-orb" aria-hidden="true" />
              <span class="assistant-status-text">{{ requestStatusText || item.content }}</span>
            </div>
            <template v-else>
              <div class="chat-markdown markdown-content" v-html="renderMarkdown(item.content)" />
              <span v-if="isStreamingAssistantMessage(item)" class="stream-cursor" aria-hidden="true">▌</span>
            </template>
          </template>
          <p v-else class="chat-content">{{ item.content }}</p>
          <p v-if="item.score" class="score-tip">本轮评分 {{ item.score.score }} · {{ item.score.comment }}</p>
        </article>
      </div>

      <form class="composer" @submit.prevent="handleComposerSubmit">
        <div
          class="composer-shell"
          :class="{
            busy: isComposerBusy,
            listening: isListening,
            disabled: isLoading || sessionFinished,
          }"
        >
          <textarea
            ref="answerInputRef"
            :value="inputText"
            class="answer-input"
            rows="1"
            :placeholder="composerPlaceholder"
            :disabled="isLoading || sessionFinished"
            @input="emit('update:inputText', ($event.target as HTMLTextAreaElement).value)"
            @keydown="handleInputKeydown"
          />
          <div class="composer-footer">
            <div class="composer-meta">
              <p class="composer-hint">{{ composerHintText }}</p>
              <span
                class="speech-pill"
                :class="{
                  active: isSpeechActive,
                  listening: speechState === 'connected',
                  transcribing: speechState === 'transcribing',
                }"
              >
                {{ speechStatusText }}
              </span>
            </div>
            <div class="composer-actions">
              <button
                type="button"
                class="icon-btn voice-btn"
                :class="{ active: isListening || speechState === 'transcribing' }"
                :disabled="!canToggleVoice"
                :aria-label="isListening ? '停止语音输入' : '开始语音输入'"
                @click="emit('toggleVoice')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M12 3a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3Zm-6 8a1 1 0 1 1 2 0 4 4 0 0 0 8 0 1 1 0 1 1 2 0 5.99 5.99 0 0 1-5 5.91V20h2a1 1 0 1 1 0 2H9a1 1 0 1 1 0-2h2v-3.09A5.99 5.99 0 0 1 6 11Z"
                  />
                </svg>
              </button>
              <button type="submit" class="icon-btn send-btn" :disabled="!canSend" aria-label="发送回答">
                <span v-if="isComposerBusy" class="send-spinner" aria-hidden="true" />
                <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4.5 12 19 4.5l-3 15-4.5-5-5 4 1.5-6.5Z" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </form>
    </section>
  </section>
</template>

<style scoped>
.simulation-panel {
  flex: 1;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.card {
  border-radius: 12px;
  border: 1px solid #e4d8cb;
  background: #fff;
  padding: 12px;
}

.controls-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.controls-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.card-title {
  color: #2d2521;
  font-size: 14px;
  font-weight: 700;
}

.card-helper {
  margin-top: 4px;
  color: #8a7461;
  font-size: 12px;
}

.status-pill {
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 700;
  background: #f0ece6;
  color: #7f7162;
}

.status-pill.active {
  background: #eaf7ed;
  color: #2b7a45;
}

.timer-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.timer-label {
  color: #7c7062;
  font-size: 12px;
  font-weight: 600;
}

.timer-value {
  min-width: 56px;
  text-align: center;
  border: 1px solid #dfd2c2;
  border-radius: 8px;
  background: #fff;
  color: #2d2521;
  font-size: 12px;
  font-weight: 700;
  padding: 7px 8px;
}

.mini-btn {
  border: 1px solid #dfd2c2;
  border-radius: 8px;
  background: #f7f3ee;
  color: #5f5448;
  font-size: 12px;
  font-weight: 700;
  padding: 7px 10px;
  cursor: pointer;
}

.action-btn {
  border: 1px solid #dfd2c2;
  border-radius: 8px;
  background: #fff;
  color: #5f5448;
  font-size: 12px;
  font-weight: 700;
  padding: 7px 10px;
  cursor: pointer;
}

.action-btn.primary {
  border-color: #2d2521;
  background: #2d2521;
  color: #fff;
}

.action-btn.danger {
  border-color: #d97745;
  background: #d97745;
  color: #fff;
}

.action-btn.ghost {
  background: #f7f3ee;
}

.action-btn:disabled,
.mini-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.qa-card {
  flex: 1 1 0;
  height: auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
}

.qa-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.qa-meta {
  color: #8a7461;
  font-size: 12px;
  font-weight: 600;
}

.error-text {
  border: 1px solid #f0c7c7;
  border-radius: 8px;
  background: #fff1f1;
  color: #bf2f2f;
  font-size: 12px;
  font-weight: 600;
  padding: 8px 10px;
}

.chat-list {
  flex: 1;
  min-height: 0;
  border: 1px solid #eadfd1;
  border-radius: 14px;
  background: linear-gradient(180deg, #fdfbf8 0%, #fbf7f1 100%);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
}

.chat-empty {
  color: #8a7461;
  font-size: 12px;
  text-align: center;
  margin: auto 0;
}

.chat-item {
  border-radius: 14px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.chat-item.assistant {
  background: #f7f1ea;
  border: 1px solid #e8ddd0;
}

.chat-item.assistant.pending {
  border-color: #dfc9b7;
  box-shadow: 0 10px 24px rgba(77, 57, 31, 0.06);
}

.chat-item.user {
  background: #fff;
  border: 1px solid #e8ddd0;
}

.chat-role {
  color: #8a7461;
  font-size: 12px;
  font-weight: 700;
}

.chat-content {
  color: #2d2521;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
}

.chat-markdown {
  color: #2d2521;
  font-size: 13px;
  word-break: break-word;
  line-height: 1.65;
}

.assistant-status {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: #6f5c49;
  font-size: 13px;
  font-weight: 600;
}

.assistant-status-orb {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(180deg, #1f1c17 0%, #d97745 100%);
  box-shadow: 0 0 0 8px rgba(217, 119, 69, 0.12);
  animation: pulse 1.3s ease-in-out infinite;
}

.assistant-status-text {
  min-width: 0;
  word-break: break-word;
}

.markdown-content :deep(p) {
  margin: 0 0 8px;
}

.markdown-content :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 0 0 8px;
  padding-left: 18px;
}

.markdown-content :deep(li) {
  margin-bottom: 4px;
}

.markdown-content :deep(pre) {
  margin: 8px 0;
  padding: 10px;
  border-radius: 8px;
  background: #1f1c17;
  color: #f8f4ef;
  overflow: auto;
}

.markdown-content :deep(code) {
  font-family: Consolas, 'Courier New', monospace;
  font-size: 12px;
}

.markdown-content :deep(p code),
.markdown-content :deep(li code) {
  background: #efe7de;
  color: #5b4937;
  padding: 2px 6px;
  border-radius: 6px;
}

.markdown-content :deep(blockquote) {
  margin: 8px 0;
  padding: 6px 10px;
  border-left: 3px solid #d6b79e;
  background: #f8f2ea;
  color: #705b47;
}

.markdown-content :deep(a) {
  color: #315f9a;
}

.score-tip {
  color: #315f9a;
  font-size: 12px;
  font-weight: 600;
  background: #eaf2ff;
  border-radius: 8px;
  padding: 6px 8px;
}

.stream-cursor {
  display: inline-block;
  color: #d97745;
  font-weight: 700;
  animation: blink 0.9s steps(1, end) infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

@keyframes pulse {
  50% {
    transform: scale(1.15);
    opacity: 0.85;
  }
}

.composer {
  flex-shrink: 0;
}

.composer-shell {
  border: 1px solid #dfd2c2;
  border-radius: 20px;
  background: linear-gradient(180deg, #ffffff 0%, #fbf7f2 100%);
  padding: 14px 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 18px 36px rgba(45, 37, 33, 0.08);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.composer-shell:focus-within {
  border-color: #d97745;
  box-shadow: 0 0 0 4px rgba(217, 119, 69, 0.12), 0 20px 40px rgba(45, 37, 33, 0.1);
}

.composer-shell.busy {
  border-color: #d8c1b0;
}

.composer-shell.listening {
  border-color: #d97745;
}

.composer-shell.disabled {
  opacity: 0.82;
}

.answer-input {
  width: 100%;
  border: none;
  background: transparent;
  color: #2d2521;
  font-size: 14px;
  line-height: 1.7;
  min-height: 116px;
  max-height: 220px;
  resize: none;
  padding: 0;
}

.answer-input::placeholder {
  color: #9a8674;
}

.answer-input:focus {
  outline: none;
}

.composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.composer-meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.composer-hint {
  color: #7b6f62;
  font-size: 12px;
  font-weight: 600;
}

.speech-pill {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  max-width: 100%;
  border-radius: 999px;
  border: 1px solid #e1d5c8;
  background: #f6f1ea;
  color: #7c6d60;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  padding: 6px 10px;
}

.speech-pill.active {
  border-color: #d8c3b0;
  background: #fff7ee;
  color: #8d5e38;
}

.speech-pill.listening {
  border-color: #d97745;
  background: rgba(217, 119, 69, 0.12);
  color: #be5f28;
}

.speech-pill.transcribing {
  border-color: #cba781;
  background: #fff2e3;
  color: #9c5b29;
}

.composer-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.icon-btn {
  width: 42px;
  height: 42px;
  border-radius: 999px;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease, border-color 0.18s ease;
}

.icon-btn svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

.voice-btn {
  border-color: #ddd2c6;
  background: #fff;
  color: #64594d;
  cursor: pointer;
}

.voice-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(45, 37, 33, 0.08);
}

.voice-btn.active {
  border-color: #d97745;
  background: rgba(217, 119, 69, 0.12);
  color: #c65f23;
}

.send-btn {
  border: none;
  background: #1f1c17;
  color: #fff;
  cursor: pointer;
  box-shadow: 0 14px 26px rgba(31, 28, 23, 0.2);
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px) scale(1.01);
}

.send-btn:disabled,
.voice-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

.send-spinner {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 2px solid rgba(255, 255, 255, 0.26);
  border-top-color: #fff;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .simulation-panel {
    gap: 8px;
    height: 100%;
    min-height: 0;
  }

  .card {
    padding: 10px;
  }

  .controls-top,
  .qa-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .timer-row {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    width: 100%;
    align-items: stretch;
  }

  .timer-label,
  .mini-btn,
  .timer-value,
  .action-btn {
    min-width: 0;
    min-height: 34px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 6px 6px;
    font-size: 11.5px;
    line-height: 1.15;
    white-space: normal;
  }

  .timer-value {
    width: 100%;
  }

  .action-btn {
    grid-column: span 2;
    order: 3;
    width: 100%;
  }

  .action-btn.ghost {
    order: 4;
  }

  .action-btn.danger {
    grid-column: 1 / -1;
    order: 5;
  }

  .composer-shell {
    padding: 10px;
    border-radius: 16px;
    gap: 8px;
  }

  .answer-input {
    min-height: 64px;
    max-height: 120px;
    font-size: 13px;
    line-height: 1.55;
  }

  .composer-footer {
    flex-direction: row;
    align-items: flex-end;
    gap: 8px;
  }

  .composer-meta {
    flex: 1;
    width: 100%;
    gap: 6px;
  }

  .composer-hint {
    font-size: 11px;
    line-height: 1.35;
  }

  .speech-pill {
    padding: 5px 8px;
  }

  .composer-actions {
    flex-shrink: 0;
    justify-content: flex-end;
    gap: 8px;
  }

  .qa-card {
    flex: 1 1 0;
    height: auto;
    min-height: 0;
  }

  .chat-list {
    min-height: 0;
  }

  .composer-shell.disabled {
    gap: 8px;
    padding: 10px;
  }

  .composer-shell.disabled .answer-input {
    min-height: 34px;
    max-height: 48px;
  }
}

@media (max-width: 480px) {
  .chat-list {
    padding: 10px;
  }

  .chat-item {
    padding: 10px;
  }

  .composer-actions {
    justify-content: flex-end;
  }

  .icon-btn {
    width: 42px;
    height: 42px;
  }

  .send-btn {
    flex: 0 0 52px;
    border-radius: 999px;
  }

  .answer-input {
    min-height: 52px;
    max-height: 96px;
  }
}
</style>
