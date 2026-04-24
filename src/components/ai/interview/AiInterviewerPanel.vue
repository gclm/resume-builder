<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import AiConfigDialog from '@/components/ai/AiConfigDialog.vue'
import InterviewSimulationPanel from '@/components/ai/interview/InterviewSimulationPanel.vue'
import ResumePreviewOverlay from '@/components/ai/interview/ResumePreviewOverlay.vue'
import {
  BrowserSpeechTranscriptionSession,
  type SpeechRuntimeState,
  type SpeechSession,
} from '@/services/browserSpeechService'
import { RealtimeTranscriptionSession } from '@/services/realtimeSpeechService'
import { UploadSpeechTranscriptionSession } from '@/services/uploadSpeechService'
import { useAiConfigStore } from '@/stores/aiConfig'
import { useResumeStore } from '@/stores/resume'
import {
  getInterviewSessionDetail,
  listInterviewSessions,
  requestInterviewTurn,
  type FinalEvaluation,
  type InterviewCommand,
  type InterviewHistoryItem,
  type InterviewMode,
  type InterviewRequestState,
  type InterviewSessionSummary,
  type InterviewTurnScore,
  type ResumeSnapshot,
} from '@/services/interviewService'
import type { ChatMessage } from '@/components/ai/interview/types'

// author: jf
const TEXT = {
  statusNotStarted: '\u672a\u5f00\u59cb',
  statusFinished: '\u5df2\u7ed3\u675f',
  statusRunning: '\u8fdb\u884c\u4e2d',
  statusPaused: '\u5df2\u6682\u505c',
  unknownError: '\u672a\u77e5\u9519\u8bef',
  modeCandidate: '\u5019\u9009\u4eba\u6a21\u5f0f\uff08AI \u9762\u8bd5\u5b98\uff09',
  modeInterviewer: '\u9762\u8bd5\u5b98\u6a21\u5f0f\uff08AI \u5019\u9009\u4eba\uff09',
  hideResume: '\u6536\u8d77\u7b80\u5386',
  showResume: '\u67e5\u770b\u7b80\u5386',
  totalScore: '\u603b\u5206',
  pass: '\u901a\u8fc7',
  fail: '\u672a\u901a\u8fc7',
  projectInterview: '\u9879\u76ee\u9762\u8bd5',
  switchedToUploadSpeech: '实时语音不可用，已切换为后端音频转写',
  switchedToBrowserSpeech: '\u5b9e\u65f6\u8bed\u97f3\u4e0d\u53ef\u7528\uff0c\u5df2\u5207\u6362\u4e3a\u6d4f\u89c8\u5668\u514d\u8d39\u8bed\u97f3\u8bc6\u522b',
  speechUnavailable: '实时语音、后端音频转写与浏览器免费语音均不可用',
  historyPlaceholder: '\u5386\u53f2\u4f1a\u8bdd',
  historyRefresh: '\u5237\u65b0\u5386\u53f2',
  historyLoading: '\u52a0\u8f7d\u4e2d...',
  sessionAlreadyFinished: '\u5f53\u524d\u4f1a\u8bdd\u5df2\u7ed3\u675f\uff0c\u4e0d\u53ef\u7ee7\u7eed\u6216\u53d1\u9001\u6d88\u606f\u3002',
  composerDefaultHint: 'Enter \u53d1\u9001\uff0cCtrl+Enter \u6362\u884c\uff0cCtrl+I \u8bed\u97f3\u5f00\u5173',
  composerListeningHint: '\u8bed\u97f3\u8f93\u5165\u4e2d\uff0c\u70b9\u51fb\u9ea6\u514b\u98ce\u7ed3\u675f',
  composerRecordingHint: '录音中，点击麦克风结束后将自动转写',
  composerConnectingHint: '语音连接中，请稍候',
  composerTranscribingHint: '语音转写中，请稍候',
  composerFailedHint: '\u672c\u8f6e\u53d1\u9001\u672a\u5b8c\u6210\uff0c\u8bf7\u6839\u636e\u63d0\u793a\u8c03\u6574\u540e\u91cd\u8bd5',
  composerFinishedHint: '\u5f53\u524d\u4f1a\u8bdd\u5df2\u7ed3\u675f\uff0c\u5982\u9700\u7ee7\u7eed\u8bf7\u5148\u91cd\u7f6e',
  speechRealtimeLabel: '实时语音',
  speechUploadLabel: '后端转写',
  speechBrowserLabel: '浏览器识别',
  speechPreferredLabel: '后端语音优先',
} as const

const resumeStore = useResumeStore()
const aiConfigStore = useAiConfigStore()

type SpeechEngine = 'realtime' | 'upload' | 'browser'
type SpeechUiState = Exclude<SpeechRuntimeState, 'closed'> | 'idle'

const mode = ref<InterviewMode>('candidate')
const durationMinutes = ref(60)
const elapsedSeconds = ref(0)
const sessionStarted = ref(false)
const timerRunning = ref(false)
const isLoading = ref(false)
const isListening = ref(false)
const showResumePreview = ref(false)
const showAiConfig = ref(false)
const errorMsg = ref('')
const inputText = ref('')
const finalEvaluation = ref<FinalEvaluation | null>(null)
const messages = ref<ChatMessage[]>([])
const memorySummary = ref('')
const requestState = ref<InterviewRequestState>('idle')
const requestStatusText = ref('')
const streamingAssistantMessageId = ref<string | null>(null)
const currentSessionId = ref('')
const sessionHistory = ref<InterviewSessionSummary[]>([])
const selectedSessionId = ref('')
const loadingSessionHistory = ref(false)
const sessionFinished = ref(false)
const speechUiState = ref<SpeechUiState>('idle')

const totalSeconds = computed(() => Math.max(durationMinutes.value, 1) * 60)
const remainingSeconds = computed(() => Math.max(totalSeconds.value - elapsedSeconds.value, 0))
const timerText = computed(() => {
  const minutes = Math.floor(remainingSeconds.value / 60)
  const seconds = remainingSeconds.value % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})
const timerStatusText = computed(() => {
  if (!sessionStarted.value) return TEXT.statusNotStarted
  if (sessionFinished.value) return TEXT.statusFinished
  if (remainingSeconds.value === 0) return TEXT.statusFinished
  return timerRunning.value ? TEXT.statusRunning : TEXT.statusPaused
})
const assistantTurns = computed(() => messages.value.filter((item) => item.role === 'assistant').length)
const userTurns = computed(() => messages.value.filter((item) => item.role === 'user').length)
const currentRound = computed(() => Math.max(assistantTurns.value, userTurns.value))
const canSend = computed(() => sessionStarted.value && !sessionFinished.value && inputText.value.trim() !== '' && !isLoading.value)
const canStart = computed(() => !sessionStarted.value && !isLoading.value)
const canTogglePause = computed(() => sessionStarted.value && !sessionFinished.value && remainingSeconds.value > 0 && !isLoading.value)
const canFinish = computed(() => sessionStarted.value && !isLoading.value && !sessionFinished.value && messages.value.length > 0)
const canToggleVoice = computed(
  () => sessionStarted.value && !sessionFinished.value && !isLoading.value && speechUiState.value !== 'transcribing'
)
const configBadgeText = computed(() => '\u8bed\u97f3\u914d\u7f6e')
const configTooltipText = computed(() => '\u8bed\u97f3\u914d\u7f6e')
const historyRefreshText = computed(() => (loadingSessionHistory.value ? TEXT.historyLoading : TEXT.historyRefresh))
const speechStatusText = computed(() => {
  const engineLabel = resolveSpeechEngineLabel(activeSpeechEngine.value)
  if (!sessionStarted.value) {
    return `语音 · ${aiConfigStore.shouldRequestBackendSpeech ? TEXT.speechPreferredLabel : TEXT.speechBrowserLabel}`
  }
  if (speechUiState.value === 'connecting') {
    return `语音 · ${engineLabel}连接中`
  }
  if (speechUiState.value === 'connected') {
    if (activeSpeechEngine.value === 'upload') {
      return `语音 · ${engineLabel}录音中`
    }
    if (activeSpeechEngine.value === 'browser') {
      return '语音 · 浏览器输入中'
    }
    return `语音 · ${engineLabel}识别中`
  }
  if (speechUiState.value === 'transcribing') {
    return `语音 · ${engineLabel}转写中`
  }
  return `语音 · ${engineLabel}`
})
const composerHintText = computed(() => {
  if (speechUiState.value === 'connecting') return TEXT.composerConnectingHint
  if (speechUiState.value === 'transcribing') return `${resolveSpeechEngineLabel(activeSpeechEngine.value)}处理中，请稍候`
  if (isListening.value) {
    return activeSpeechEngine.value === 'upload' ? TEXT.composerRecordingHint : TEXT.composerListeningHint
  }
  if (['submitting', 'accepted', 'processing', 'responding'].includes(requestState.value)) {
    return requestStatusText.value || TEXT.composerDefaultHint
  }
  if (requestState.value === 'failed') return TEXT.composerFailedHint
  if (sessionFinished.value) return TEXT.composerFinishedHint
  return TEXT.composerDefaultHint
})

const resumeSnapshot = computed<ResumeSnapshot>(() => ({
  basicInfo: resumeStore.basicInfo,
  skillsText: resumeStore.skills,
  workList: resumeStore.workList,
  projectList: resumeStore.projectList,
  educationList: resumeStore.educationList,
  selfIntro: resumeStore.selfIntro,
}))

let ticker: ReturnType<typeof setInterval> | null = null
let speechSession: SpeechSession | null = null
const activeSpeechEngine = ref<SpeechEngine | null>(null)
let switchingSpeechEngine = false
let speechInputPrefix = ''
let speechTranscript = ''

function newMessageId(): string {
  return `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function resolveAssistantLabel(currentMode: InterviewMode): string {
  return currentMode === 'candidate' ? 'AI面试官' : 'AI候选人'
}

function resolveSpeechEngineLabel(engine: SpeechEngine | null): string {
  if (engine === 'realtime') return TEXT.speechRealtimeLabel
  if (engine === 'upload') return TEXT.speechUploadLabel
  if (engine === 'browser') return TEXT.speechBrowserLabel
  return aiConfigStore.shouldRequestBackendSpeech ? TEXT.speechPreferredLabel : TEXT.speechBrowserLabel
}

function normalizeStatusMessage(message: string, fallback: string): string {
  const cleaned = String(message || '').trim()
  return cleaned || fallback
}

function buildRequestStatusText(command: InterviewCommand, state: InterviewRequestState): string {
  const assistantLabel = resolveAssistantLabel(mode.value)

  if (command === 'start') {
    if (state === 'submitting') return '正在启动面试...'
    if (state === 'accepted') return '面试已启动，正在同步当前简历上下文'
    if (state === 'processing') {
      return mode.value === 'candidate' ? 'AI面试官正在生成第一轮问题...' : 'AI候选人正在生成开场回答...'
    }
    if (state === 'responding') return `${assistantLabel}正在回复...`
    if (state === 'failed') return '面试启动失败，请重试'
    return ''
  }

  if (command === 'finish') {
    if (state === 'submitting') return '正在结束面试...'
    if (state === 'accepted') return '已收到结束指令'
    if (state === 'processing') return '正在生成评分结果与总结...'
    if (state === 'responding') return `${assistantLabel}正在输出评分结果...`
    if (state === 'failed') return '结束并评分失败，请重试'
    return ''
  }

  if (state === 'submitting') return '消息已发送'
  if (state === 'accepted') return '已收到你的回答'
  if (state === 'processing') {
    return mode.value === 'candidate' ? 'AI面试官正在组织下一轮提问...' : 'AI候选人正在组织回答...'
  }
  if (state === 'responding') return `${assistantLabel}正在回复...`
  if (state === 'failed') return '本轮回复失败，请调整后重试'
  return ''
}

function setRequestState(nextState: InterviewRequestState, command: InterviewCommand, message?: string) {
  requestState.value = nextState

  if (nextState === 'idle' || nextState === 'completed') {
    requestStatusText.value = ''
    return
  }

  requestStatusText.value = normalizeStatusMessage(message || '', buildRequestStatusText(command, nextState))
}

function appendMessage(role: 'assistant' | 'user', content: string, score: InterviewTurnScore | null = null) {
  messages.value.push({
    id: newMessageId(),
    role,
    content: content.trim(),
    score,
  })
}

function createAssistantDraftMessage(content: string): string {
  const id = newMessageId()
  messages.value.push({
    id,
    role: 'assistant',
    content: content.trim(),
    score: null,
  })
  return id
}

function updateAssistantMessageById(id: string, content: string, score: InterviewTurnScore | null = null) {
  const target = messages.value.find((item) => item.id === id)
  if (!target) return
  target.content = content
  target.score = score
}

function removeMessageById(id: string) {
  const index = messages.value.findIndex((item) => item.id === id)
  if (index >= 0) messages.value.splice(index, 1)
}

function formatErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return String(error ?? TEXT.unknownError)
}

function mergeSpeechToInput() {
  const transcript = speechTranscript.trim()
  if (!transcript) {
    inputText.value = speechInputPrefix
    return
  }
  inputText.value = speechInputPrefix ? `${speechInputPrefix}\n${transcript}` : transcript
}

function buildSpeechCallbacks(engine: SpeechEngine) {
  return {
    onPartialText(text: string) {
      speechTranscript = text
      mergeSpeechToInput()
    },
    onFinalText(_segment: string, mergedText: string) {
      speechTranscript = mergedText
      mergeSpeechToInput()
    },
    onError(message: string) {
      if (engine === 'realtime') {
        void handleRealtimeSpeechError(message)
        return
      }
      errorMsg.value = message
      stopSpeechSafely(false)
    },
    onStateChange(state: SpeechRuntimeState) {
      speechUiState.value = state === 'closed' ? 'idle' : state
      isListening.value = state === 'connected' || state === 'connecting'
    },
  }
}

async function createSpeechSession(engine: SpeechEngine): Promise<SpeechSession> {
  if (engine === 'realtime') {
    return new RealtimeTranscriptionSession({
      language: 'zh',
      callbacks: buildSpeechCallbacks('realtime'),
    })
  }

  if (engine === 'upload') {
    return new UploadSpeechTranscriptionSession({
      language: 'zh',
      callbacks: buildSpeechCallbacks('upload'),
    })
  }

  return new BrowserSpeechTranscriptionSession({
    language: 'zh-CN',
    callbacks: buildSpeechCallbacks('browser'),
  })
}

async function activateSpeechEngine(engine: SpeechEngine) {
  const session = await createSpeechSession(engine)
  speechSession = session
  activeSpeechEngine.value = engine
  speechUiState.value = 'connecting'
  try {
    await session.start()
  } catch (error) {
    speechSession = null
    activeSpeechEngine.value = null
    speechUiState.value = 'idle'
    throw error
  }
}

async function stopSpeech(clearSpeechText: boolean) {
  const session = speechSession
  speechSession = null

  if (session) {
    await session.stop({ silent: clearSpeechText })
  }

  isListening.value = false
  speechUiState.value = 'idle'
  if (clearSpeechText) {
    speechTranscript = ''
    inputText.value = speechInputPrefix
  }
  speechInputPrefix = ''
  activeSpeechEngine.value = null
}

function stopSpeechSafely(clearSpeechText: boolean) {
  void stopSpeech(clearSpeechText).catch(() => {
    isListening.value = false
    speechUiState.value = 'idle'
    activeSpeechEngine.value = null
  })
}

async function trySwitchToBrowserSpeech(reason: string, markBackendUnavailable = false): Promise<boolean> {
  if (switchingSpeechEngine) {
    return false
  }

  switchingSpeechEngine = true
  try {
    if (markBackendUnavailable) {
      aiConfigStore.markBackendSpeechUnavailable()
    }
    await stopSpeech(false)
    await activateSpeechEngine('browser')
    errorMsg.value = `${TEXT.switchedToBrowserSpeech}\n${reason}`
    return true
  } catch (fallbackError) {
    const fallbackMessage = formatErrorMessage(fallbackError)
    errorMsg.value = `${TEXT.speechUnavailable}\n${reason}\n${fallbackMessage}`
    return false
  } finally {
    switchingSpeechEngine = false
  }
}

async function trySwitchFromRealtimeToUpload(reason: string): Promise<boolean> {
  if (switchingSpeechEngine) {
    return false
  }

  switchingSpeechEngine = true
  try {
    await stopSpeech(false)
    speechInputPrefix = inputText.value.trim()
    speechTranscript = ''
    inputText.value = speechInputPrefix

    try {
      await activateSpeechEngine('upload')
      errorMsg.value = `${TEXT.switchedToUploadSpeech}\n${reason}`
      return true
    } catch (uploadError) {
      const uploadMessage = formatErrorMessage(uploadError)
      aiConfigStore.markBackendSpeechUnavailable()
      try {
        await activateSpeechEngine('browser')
        errorMsg.value = `${TEXT.switchedToBrowserSpeech}\n${reason}\n${uploadMessage}`
        return true
      } catch (browserError) {
        const browserMessage = formatErrorMessage(browserError)
        errorMsg.value = `${TEXT.speechUnavailable}\n${reason}\n${uploadMessage}\n${browserMessage}`
        return false
      }
    }
  } finally {
    switchingSpeechEngine = false
  }
}

async function handleRealtimeSpeechError(message: string) {
  if (activeSpeechEngine.value === 'realtime') {
    const switched = await trySwitchFromRealtimeToUpload(message)
    if (switched) {
      return
    }
  }

  errorMsg.value = message
  stopSpeechSafely(false)
}

async function startSpeech() {
  if (!sessionStarted.value || isLoading.value || speechSession) return

  errorMsg.value = ''
  speechInputPrefix = inputText.value.trim()
  speechTranscript = ''
  speechUiState.value = 'idle'
  mergeSpeechToInput()

  if (!aiConfigStore.shouldRequestBackendSpeech) {
    try {
      await activateSpeechEngine('browser')
      return
    } catch (error) {
      const message = formatErrorMessage(error)
      errorMsg.value = message
      return
    }
  }

  try {
    await activateSpeechEngine('realtime')
  } catch (error) {
    const realtimeMessage = formatErrorMessage(error)

    try {
      await activateSpeechEngine('upload')
      errorMsg.value = `${TEXT.switchedToUploadSpeech}\n${realtimeMessage}`
      return
    } catch (uploadError) {
      const uploadMessage = formatErrorMessage(uploadError)
      const switched = await trySwitchToBrowserSpeech(`${realtimeMessage}\n${uploadMessage}`, true)
      if (switched) {
        return
      }

      isListening.value = false
      speechUiState.value = 'idle'
      speechTranscript = ''
      inputText.value = speechInputPrefix
      speechInputPrefix = ''
      activeSpeechEngine.value = null
      errorMsg.value = `${TEXT.speechUnavailable}\n${realtimeMessage}\n${uploadMessage}`
    }
  }
}

function resetSession() {
  stopSpeechSafely(true)
  messages.value = []
  finalEvaluation.value = null
  memorySummary.value = ''
  errorMsg.value = ''
  requestState.value = 'idle'
  requestStatusText.value = ''
  elapsedSeconds.value = 0
  sessionStarted.value = false
  timerRunning.value = false
  streamingAssistantMessageId.value = null
  inputText.value = ''
  currentSessionId.value = ''
  selectedSessionId.value = ''
  isListening.value = false
  sessionFinished.value = false
  speechUiState.value = 'idle'
  activeSpeechEngine.value = null
}

function buildHistory(excludeLastMessageId?: string): InterviewHistoryItem[] {
  const source = excludeLastMessageId
    ? messages.value.filter((item) => item.id !== excludeLastMessageId)
    : messages.value
  return source.map((item) => ({
    role: item.role,
    content: item.content,
    score: item.score,
  }))
}


function buildSessionOptionLabel(item: InterviewSessionSummary): string {
  const modeLabel = item.mode === 'candidate' ? '候选人模式' : '面试官模式'
  const statusLabel = item.status === 'finished' ? '已结束' : '进行中'
  const scoreLabel = item.totalScore == null ? '' : ` · ${item.totalScore}分`
  const timeLabel = item.updatedAt.replace('T', ' ').slice(0, 16)
  return `${timeLabel} · ${modeLabel} · ${statusLabel}${scoreLabel}`
}

function applySessionDetail(detail: Awaited<ReturnType<typeof getInterviewSessionDetail>>) {
  mode.value = detail.mode
  durationMinutes.value = Math.max(15, Math.min(120, detail.durationMinutes || 60))
  elapsedSeconds.value = Math.max(0, Math.min(detail.elapsedSeconds || 0, durationMinutes.value * 60))
  messages.value = detail.messages.map((item) => ({
    id: newMessageId(),
    role: item.role,
    content: item.content,
    score: item.score,
  }))
  memorySummary.value = detail.memorySummary || ''
  finalEvaluation.value = detail.finalEvaluation
  requestState.value = 'idle'
  requestStatusText.value = ''
  currentSessionId.value = detail.sessionId
  selectedSessionId.value = detail.sessionId
  sessionStarted.value = detail.messages.length > 0
  timerRunning.value = false
  streamingAssistantMessageId.value = null
  inputText.value = ''
  errorMsg.value = ''
  sessionFinished.value = detail.status === 'finished' || Boolean(detail.finalEvaluation)
}

async function refreshSessionHistory(preferredSessionId?: string) {
  loadingSessionHistory.value = true
  try {
    const sessions = await listInterviewSessions(30)
    sessionHistory.value = sessions

    const targetSessionId =
      preferredSessionId ||
      currentSessionId.value ||
      selectedSessionId.value ||
      sessions[0]?.sessionId ||
      ''

    selectedSessionId.value = sessions.some((item) => item.sessionId === targetSessionId) ? targetSessionId : sessions[0]?.sessionId || ''
  } catch (error) {
    errorMsg.value = formatErrorMessage(error)
  } finally {
    loadingSessionHistory.value = false
  }
}

async function restoreSessionById(sessionId: string, refreshHistory = false) {
  const targetSessionId = sessionId.trim()
  if (!targetSessionId) return

  if (isListening.value) {
    await stopSpeech(false)
  }

  const detail = await getInterviewSessionDetail(targetSessionId)
  applySessionDetail(detail)
  if (refreshHistory) {
    await refreshSessionHistory(targetSessionId)
  }
}

async function initializeSessionHistory() {
  await refreshSessionHistory()
  const firstSessionId = selectedSessionId.value
  if (!firstSessionId) return

  try {
    await restoreSessionById(firstSessionId)
  } catch (error) {
    errorMsg.value = formatErrorMessage(error)
  }
}

async function handleSessionSelectionChange() {
  const targetSessionId = selectedSessionId.value.trim()
  if (!targetSessionId || targetSessionId === currentSessionId.value) return

  try {
    await restoreSessionById(targetSessionId)
  } catch (error) {
    errorMsg.value = formatErrorMessage(error)
  }
}

function handleRefreshSessionHistory() {
  void refreshSessionHistory(selectedSessionId.value || currentSessionId.value)
}
async function runInterview(command: InterviewCommand, userInput?: string) {
  if (isLoading.value) return
  if (command === 'continue' && sessionFinished.value) {
    errorMsg.value = TEXT.sessionAlreadyFinished
    return
  }

  isLoading.value = true
  errorMsg.value = ''
  setRequestState('submitting', command)
  const draftMessageId = createAssistantDraftMessage(requestStatusText.value || buildRequestStatusText(command, 'submitting'))
  streamingAssistantMessageId.value = draftMessageId
  let hasStreamedAssistantReply = false

  try {
    const response = await requestInterviewTurn(
      {
        mode: mode.value,
        command,
        sessionId: currentSessionId.value || undefined,
        userInput,
        history: buildHistory(draftMessageId),
        resumeSnapshot: resumeSnapshot.value,
        durationMinutes: durationMinutes.value,
        elapsedSeconds: elapsedSeconds.value,
        memorySummary: memorySummary.value,
      },
      undefined,
      {
        onAccepted(message) {
          setRequestState('accepted', command, message)
          updateAssistantMessageById(draftMessageId, requestStatusText.value, null)
        },
        onProcessing(message) {
          setRequestState('processing', command, message)
          updateAssistantMessageById(draftMessageId, requestStatusText.value, null)
        },
        onAssistantReplyChunk(text) {
          hasStreamedAssistantReply = true
          setRequestState('responding', command)
          updateAssistantMessageById(draftMessageId, text)
        },
      }
    )

    updateAssistantMessageById(draftMessageId, response.assistantReply, response.turnScore)
    setRequestState('completed', command)
    if (response.sessionId) {
      currentSessionId.value = response.sessionId
      selectedSessionId.value = response.sessionId
    }
    if (response.memorySummary) memorySummary.value = response.memorySummary
    if (response.finalEvaluation) finalEvaluation.value = response.finalEvaluation
    if (response.nextAction === 'finish' || command === 'finish') {
      timerRunning.value = false
      sessionFinished.value = true
    }
    void refreshSessionHistory(currentSessionId.value)
  } catch (error: unknown) {
    if (!hasStreamedAssistantReply) {
      removeMessageById(draftMessageId)
    }
    setRequestState('failed', command)
    errorMsg.value = formatErrorMessage(error)
  } finally {
    if (streamingAssistantMessageId.value === draftMessageId) {
      streamingAssistantMessageId.value = null
    }
    isLoading.value = false
  }
}

function handleModeSwitch(nextMode: InterviewMode) {
  if (mode.value === nextMode) return
  mode.value = nextMode
  resetSession()
}

function adjustDuration(delta: number) {
  const next = Math.max(15, Math.min(120, durationMinutes.value + delta))
  if (next === durationMinutes.value) return
  durationMinutes.value = next
  if (!sessionStarted.value) {
    elapsedSeconds.value = 0
  } else {
    elapsedSeconds.value = Math.max(0, Math.min(elapsedSeconds.value, totalSeconds.value - 1))
  }
}

function handleStart() {
  if (!canStart.value) return
  currentSessionId.value = ''
  selectedSessionId.value = ''
  sessionStarted.value = true
  timerRunning.value = true
  sessionFinished.value = false
  void runInterview('start')
}

function handleTogglePause() {
  if (!sessionStarted.value || sessionFinished.value || remainingSeconds.value === 0 || isLoading.value) return
  timerRunning.value = !timerRunning.value
}

function handleFinish() {
  if (!canFinish.value) return
  timerRunning.value = false
  void runInterview('finish')
}

function handleReset() {
  resetSession()
}

async function handleSend() {
  const text = inputText.value.trim()
  if (sessionFinished.value) {
    errorMsg.value = TEXT.sessionAlreadyFinished
    return
  }
  if (!canSend.value || !text) return

  if (isListening.value) {
    await stopSpeech(false)
  }

  const finalText = inputText.value.trim()
  if (!finalText) return

  appendMessage('user', finalText)
  inputText.value = ''
  speechInputPrefix = ''
  speechTranscript = ''
  void runInterview('continue', finalText)
}

async function handleToggleVoice() {
  if (!canToggleVoice.value) return

  if (isListening.value) {
    await stopSpeech(false)
    return
  }

  await startSpeech()
}

function handleGlobalKeydown(event: KeyboardEvent) {
  if (!event.ctrlKey || event.altKey || event.shiftKey || event.metaKey) return
  if (event.key.toLowerCase() !== 'i') return
  event.preventDefault()
  void handleToggleVoice()
}

function handleOpenAiConfig() {
  showAiConfig.value = true
}

watch(remainingSeconds, (value) => {
  if (!sessionStarted.value) return
  if (value !== 0) return
  timerRunning.value = false
  if (!finalEvaluation.value && !isLoading.value) {
    void runInterview('finish')
  }
})

onMounted(() => {
  void initializeSessionHistory()
  window.addEventListener('keydown', handleGlobalKeydown)
  ticker = setInterval(() => {
    if (!sessionStarted.value || !timerRunning.value) return
    if (remainingSeconds.value <= 0) return
    elapsedSeconds.value += 1
  }, 1000)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
  if (ticker) {
    clearInterval(ticker)
    ticker = null
  }
  stopSpeechSafely(true)
})
</script>

<template>
  <section class="ai-interviewer-panel">
    <header class="topbar">
      <div class="role-switch">
        <button type="button" class="mode-btn" :class="{ active: mode === 'candidate' }" @click="handleModeSwitch('candidate')">
          {{ TEXT.modeCandidate }}
        </button>
        <button
          type="button"
          class="mode-btn"
          :class="{ active: mode === 'interviewer' }"
          @click="handleModeSwitch('interviewer')"
        >
          {{ TEXT.modeInterviewer }}
        </button>
      </div>

      <div class="top-actions">
        <button
          class="config-btn"
          type="button"
          :title="configTooltipText"
          :data-model-tooltip="configTooltipText"
          @click="handleOpenAiConfig"
        >
          <svg class="icon-xs" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          <span class="config-btn-text">{{ configBadgeText }}</span>
        </button>
        <select
          v-model="selectedSessionId"
          class="history-select"
          :disabled="loadingSessionHistory"
          @change="handleSessionSelectionChange"
        >
          <option value="">{{ TEXT.historyPlaceholder }}</option>
          <option v-for="item in sessionHistory" :key="item.sessionId" :value="item.sessionId">
            {{ buildSessionOptionLabel(item) }}
          </option>
        </select>
        <button class="top-btn" type="button" :disabled="loadingSessionHistory" @click="handleRefreshSessionHistory">
          {{ historyRefreshText }}
        </button>
        <button class="top-btn" type="button" @click="showResumePreview = !showResumePreview">
          {{ showResumePreview ? TEXT.hideResume : TEXT.showResume }}
        </button>
      </div>
    </header>

    <div v-if="finalEvaluation" class="final-banner" :class="{ pass: finalEvaluation.passed, fail: !finalEvaluation.passed }">
      {{ TEXT.totalScore }} {{ finalEvaluation.totalScore }}分｜{{ finalEvaluation.passed ? TEXT.pass : TEXT.fail }}｜{{ TEXT.projectInterview }}
    </div>

    <div class="workspace">
      <InterviewSimulationPanel
        :mode="mode"
        :messages="messages"
        :is-loading="isLoading"
        :error-msg="errorMsg"
        :input-text="inputText"
        :can-send="canSend"
        :is-listening="isListening"
        :request-state="requestState"
        :request-status-text="requestStatusText"
        :composer-hint-text="composerHintText"
        :streaming-assistant-message-id="streamingAssistantMessageId"
        :session-started="sessionStarted"
        :timer-text="timerText"
        :timer-status-text="timerStatusText"
        :current-round="currentRound"
        :user-turns="userTurns"
        :assistant-turns="assistantTurns"
        :can-toggle-voice="canToggleVoice"
        :can-start="canStart"
        :can-toggle-pause="canTogglePause"
        :can-finish="canFinish"
        :session-finished="sessionFinished"
        :timer-running="timerRunning"
        :speech-state="speechUiState"
        :speech-status-text="speechStatusText"
        @update:input-text="inputText = $event"
        @start="handleStart"
        @toggle-pause="handleTogglePause"
        @finish="handleFinish"
        @reset="handleReset"
        @adjust-duration="adjustDuration"
        @send="handleSend"
        @toggle-voice="handleToggleVoice"
      />

      <ResumePreviewOverlay v-if="showResumePreview" @close="showResumePreview = false" />
    </div>

    <AiConfigDialog v-if="showAiConfig" @close="showAiConfig = false" />
  </section>
</template>

<style scoped>
.ai-interviewer-panel {
  position: relative;
  flex: 1;
  min-width: 0;
  height: 100%;
  overflow: hidden;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: linear-gradient(145deg, #f7f2ec 0%, #f1e5d8 100%);
}

.topbar {
  border: 1px solid #e4d8cb;
  border-radius: 12px;
  background: #fff;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.role-switch {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mode-btn {
  border-radius: 8px;
  border: 1px solid #dfd2c2;
  background: #f7f3ee;
  color: #625649;
  font-size: 12px;
  font-weight: 700;
  padding: 7px 12px;
  cursor: pointer;
}

.mode-btn.active {
  border-color: #1f1c17;
  background: #1f1c17;
  color: #fff;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.top-btn {
  border: 1px solid #dfd2c2;
  border-radius: 8px;
  background: #f7f3ee;
  color: #5f5448;
  font-size: 12px;
  font-weight: 700;
  padding: 7px 10px;
  cursor: pointer;
}

.history-select {
  min-width: 220px;
  max-width: 360px;
  height: 30px;
  border: 1px solid #dfd2c2;
  border-radius: 8px;
  background: #fff;
  color: #5f5448;
  font-size: 12px;
  padding: 0 8px;
}

.history-select:disabled {
  opacity: 0.65;
}

.config-btn {
  position: relative;
  height: 30px;
  padding: 0 10px;
  border-radius: 7px;
  border: 1px solid #ddd2c6;
  background: #fff;
  color: #5c4f44;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
  max-width: 180px;
  overflow: visible;
}

.config-btn:hover {
  border-color: #d97745;
  color: #d97745;
}

.config-btn-text {
  flex: 1;
  min-width: 0;
  display: inline-block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.icon-xs {
  width: 14px;
  height: 14px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
  flex-shrink: 0;
}

.final-banner {
  border-radius: 9px;
  border: 1px solid #d8d0c4;
  background: #f7f3ed;
  color: #5f5448;
  font-size: 12px;
  font-weight: 600;
  padding: 8px 10px;
}

.final-banner.pass {
  border-color: #c8e6cf;
  background: #eef8f1;
  color: #2b7a45;
}

.final-banner.fail {
  border-color: #f0d2c8;
  background: #fff1ec;
  color: #b74a30;
}

.workspace {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
}

.workspace > :first-child {
  flex: 1;
  min-height: 0;
}

@media (max-width: 860px) {
  .topbar {
    flex-direction: column;
    align-items: stretch;
  }

  .role-switch,
  .top-actions {
    width: 100%;
  }

  .mode-btn,
  .top-btn,
  .config-btn,
  .history-select {
    flex: 1;
    text-align: center;
  }
}
</style>
