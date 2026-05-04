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
  switchedToBrowserSpeech: '后端实时语音不可用，已切换为浏览器免费语音识别',
  speechUnavailable: '后端实时语音与浏览器免费语音均不可用',
  speechAutoDisabledNotice: '后端实时语音已因连续失败自动停用，可在语音配置中重新启用。',
  historyPlaceholder: '\u5386\u53f2\u4f1a\u8bdd',
  historyRefresh: '\u5237\u65b0\u5386\u53f2',
  historyLoading: '\u52a0\u8f7d\u4e2d...',
  sessionAlreadyFinished: '\u5f53\u524d\u4f1a\u8bdd\u5df2\u7ed3\u675f\uff0c\u4e0d\u53ef\u7ee7\u7eed\u6216\u53d1\u9001\u6d88\u606f\u3002',
  composerDefaultHint: 'Enter \u53d1\u9001\uff0cCtrl+Enter \u6362\u884c\uff0cCtrl+I \u8bed\u97f3\u5f00\u5173',
  composerListeningHint: '\u8bed\u97f3\u8f93\u5165\u4e2d\uff0c\u70b9\u51fb\u9ea6\u514b\u98ce\u7ed3\u675f',
  composerConnectingHint: '语音连接中，请稍候',
  composerTranscribingHint: '语音转写中，请稍候',
  composerFailedHint: '\u672c\u8f6e\u53d1\u9001\u672a\u5b8c\u6210\uff0c\u8bf7\u6839\u636e\u63d0\u793a\u8c03\u6574\u540e\u91cd\u8bd5',
  composerFinishedHint: '\u5f53\u524d\u4f1a\u8bdd\u5df2\u7ed3\u675f\uff0c\u5982\u9700\u7ee7\u7eed\u8bf7\u5148\u91cd\u7f6e',
  speechRealtimeLabel: '实时语音',
  speechBrowserLabel: '浏览器识别',
  speechPreferredLabel: '后端语音优先',
} as const

const resumeStore = useResumeStore()
const aiConfigStore = useAiConfigStore()

type SpeechEngine = 'realtime' | 'browser'
type SpeechUiState = Exclude<SpeechRuntimeState, 'closed'> | 'idle'
type FloatingPanel = 'mode' | 'controls'

const BACKEND_SPEECH_AUTO_DISABLE_THRESHOLD = 2

const mode = ref<InterviewMode>('candidate')
const durationMinutes = ref(60)
const elapsedSeconds = ref(0)
const sessionStarted = ref(false)
const timerRunning = ref(false)
const isLoading = ref(false)
const isListening = ref(false)
const showResumePreview = ref(false)
const showAiConfig = ref(false)
const activeFloatingPanel = ref<FloatingPanel | null>(null)
const floatingActionsRef = ref<HTMLElement | null>(null)
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
const interviewStatusText = computed(() => {
  if (!sessionStarted.value) return TEXT.statusNotStarted
  if (sessionFinished.value || remainingSeconds.value === 0) return TEXT.statusFinished
  return TEXT.statusRunning
})
const pauseButtonLabel = computed(() => (timerRunning.value ? '暂停' : '继续'))
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
    return TEXT.composerListeningHint
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
let backendSpeechFailureCount = 0

function newMessageId(): string {
  return `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function resetBackendSpeechFailureState() {
  backendSpeechFailureCount = 0
}

function trackBackendSpeechFailure(): boolean {
  if (!aiConfigStore.useBackendSpeech) {
    return false
  }

  backendSpeechFailureCount += 1
  if (backendSpeechFailureCount < BACKEND_SPEECH_AUTO_DISABLE_THRESHOLD) {
    return false
  }

  aiConfigStore.markBackendSpeechUnavailable()
  return true
}

function resolveAssistantLabel(currentMode: InterviewMode): string {
  return currentMode === 'candidate' ? 'AI面试官' : 'AI候选人'
}

function resolveSpeechEngineLabel(engine: SpeechEngine | null): string {
  if (engine === 'realtime') return TEXT.speechRealtimeLabel
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
    if (engine === 'realtime') {
      resetBackendSpeechFailureState()
      aiConfigStore.clearBackendSpeechUnavailable()
    }
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

async function trySwitchToBrowserSpeech(reason: string, trackBackendFailure = false): Promise<boolean> {
  if (switchingSpeechEngine) {
    return false
  }

  switchingSpeechEngine = true
  const backendSpeechAutoDisabled = trackBackendFailure ? trackBackendSpeechFailure() : false
  const autoDisabledNotice = backendSpeechAutoDisabled ? `\n${TEXT.speechAutoDisabledNotice}` : ''
  try {
    const preservedInput = inputText.value.trim()
    await stopSpeech(false)
    speechInputPrefix = preservedInput
    speechTranscript = ''
    inputText.value = preservedInput
    await activateSpeechEngine('browser')
    errorMsg.value = `${TEXT.switchedToBrowserSpeech}\n${reason}${autoDisabledNotice}`
    return true
  } catch (fallbackError) {
    const fallbackMessage = formatErrorMessage(fallbackError)
    errorMsg.value = `${TEXT.speechUnavailable}\n${reason}${autoDisabledNotice}\n${fallbackMessage}`
    return false
  } finally {
    switchingSpeechEngine = false
  }
}

async function handleRealtimeSpeechError(message: string) {
  if (activeSpeechEngine.value === 'realtime') {
    const switched = await trySwitchToBrowserSpeech(message, true)
    if (switched) {
      return
    }
    if (errorMsg.value) {
      stopSpeechSafely(false)
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
    const switched = await trySwitchToBrowserSpeech(realtimeMessage, true)
    if (switched) {
      return
    }

    isListening.value = false
    speechUiState.value = 'idle'
    speechTranscript = ''
    inputText.value = speechInputPrefix
    speechInputPrefix = ''
    activeSpeechEngine.value = null
    if (!errorMsg.value) {
      errorMsg.value = `${TEXT.speechUnavailable}\n${realtimeMessage}`
    }
  }
}

function resetSession() {
  stopSpeechSafely(true)
  resetBackendSpeechFailureState()
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
  activeFloatingPanel.value = null
  showAiConfig.value = true
}

function toggleFloatingPanel(panel: FloatingPanel) {
  activeFloatingPanel.value = activeFloatingPanel.value === panel ? null : panel
}

function handleFloatingModeSwitch(nextMode: InterviewMode) {
  handleModeSwitch(nextMode)
  activeFloatingPanel.value = null
}

function handleFloatingResumeToggle() {
  showResumePreview.value = !showResumePreview.value
  activeFloatingPanel.value = null
}

function handleDocumentPointerDown(event: MouseEvent) {
  const target = event.target as Node | null
  if (!target || !floatingActionsRef.value) return
  if (!floatingActionsRef.value.contains(target)) {
    activeFloatingPanel.value = null
  }
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
  document.addEventListener('mousedown', handleDocumentPointerDown)
  ticker = setInterval(() => {
    if (!sessionStarted.value || !timerRunning.value) return
    if (remainingSeconds.value <= 0) return
    elapsedSeconds.value += 1
  }, 1000)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
  document.removeEventListener('mousedown', handleDocumentPointerDown)
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
      <button
        class="history-refresh-btn"
        :class="{ loading: loadingSessionHistory }"
        type="button"
        :disabled="loadingSessionHistory"
        :title="historyRefreshText"
        aria-label="刷新历史"
        :aria-busy="loadingSessionHistory"
        @click="handleRefreshSessionHistory"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M20 11a8 8 0 1 0-2.34 5.66" />
          <path d="M20 4v7h-7" />
        </svg>
      </button>
      <span
        class="interview-status-pill"
        :class="{
          active: sessionStarted && !sessionFinished && remainingSeconds > 0,
          finished: sessionFinished || remainingSeconds === 0,
        }"
      >
        <span class="interview-status-dot" aria-hidden="true" />
        {{ interviewStatusText }}
      </span>
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
        :show-controls="false"
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

    <div ref="floatingActionsRef" class="interview-floating-tools" aria-label="AI 面试快捷操作">
      <div class="floating-actions-stack">
        <button
          class="floating-action-btn"
          type="button"
          :title="configTooltipText"
          :aria-label="configTooltipText"
          @click="handleOpenAiConfig"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 17v-3" />
            <path d="M4 10V7" />
            <path d="M12 19v-5" />
            <path d="M12 10V5" />
            <path d="M20 16v-2" />
            <path d="M20 10V6" />
            <path d="M2.5 14h3" />
            <path d="M10.5 10h3" />
            <path d="M18.5 14h3" />
          </svg>
        </button>

        <div class="floating-action-anchor">
          <button
            class="floating-action-btn"
            :class="{ active: activeFloatingPanel === 'mode' }"
            type="button"
            title="模式切换"
            aria-label="模式切换"
            aria-haspopup="dialog"
            :aria-expanded="activeFloatingPanel === 'mode'"
            @click="toggleFloatingPanel('mode')"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M7 7h10" />
              <path d="m14 4 3 3-3 3" />
              <path d="M17 17H7" />
              <path d="m10 14-3 3 3 3" />
            </svg>
          </button>

          <div v-if="activeFloatingPanel === 'mode'" class="floating-popover mode-popover" role="dialog" aria-label="模式切换">
            <p class="floating-popover-title">模式切换</p>
            <div class="mode-option-list">
              <button
                type="button"
                class="mode-option-btn"
                :class="{ active: mode === 'candidate' }"
                @click="handleFloatingModeSwitch('candidate')"
              >
                {{ TEXT.modeCandidate }}
              </button>
              <button
                type="button"
                class="mode-option-btn"
                :class="{ active: mode === 'interviewer' }"
                @click="handleFloatingModeSwitch('interviewer')"
              >
                {{ TEXT.modeInterviewer }}
              </button>
            </div>
          </div>
        </div>

        <button
          class="floating-action-btn"
          type="button"
          :title="showResumePreview ? TEXT.hideResume : TEXT.showResume"
          :aria-label="showResumePreview ? TEXT.hideResume : TEXT.showResume"
          @click="handleFloatingResumeToggle"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M7 3h8l4 4v14H7z" />
            <path d="M15 3v5h4" />
            <path d="M10 12h6" />
            <path d="M10 16h5" />
          </svg>
        </button>

        <div class="floating-action-anchor">
          <button
            class="floating-action-btn console-action-btn"
            :class="{ active: activeFloatingPanel === 'controls' }"
            type="button"
            title="面试控制台"
            aria-label="面试控制台"
            aria-haspopup="dialog"
            :aria-expanded="activeFloatingPanel === 'controls'"
            @click="toggleFloatingPanel('controls')"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M4 6h16" />
              <path d="M4 12h16" />
              <path d="M4 18h16" />
              <circle cx="8" cy="6" r="2" />
              <circle cx="16" cy="12" r="2" />
              <circle cx="10" cy="18" r="2" />
            </svg>
          </button>

          <div
            v-if="activeFloatingPanel === 'controls'"
            class="floating-popover controls-popover"
            role="dialog"
            aria-label="面试控制台"
          >
            <div class="console-header">
              <div>
                <p class="floating-popover-title">面试控制台</p>
                <p class="console-helper">调整时长并控制当前会话</p>
              </div>
              <span class="console-status-pill" :class="{ active: timerRunning }">{{ timerStatusText }}</span>
            </div>

            <div class="console-timer-row">
              <span class="console-label">时长</span>
              <button type="button" class="console-mini-btn" @click="adjustDuration(-5)">-5m</button>
              <span class="console-timer-value">{{ timerText }}</span>
              <button type="button" class="console-mini-btn" @click="adjustDuration(5)">+5m</button>
            </div>

            <div class="console-action-grid">
              <button v-if="canStart" type="button" class="console-btn primary" :disabled="isLoading" @click="handleStart">
                开始
              </button>
              <button v-else type="button" class="console-btn" :disabled="!canTogglePause" @click="handleTogglePause">
                {{ pauseButtonLabel }}
              </button>
              <button type="button" class="console-btn ghost" :disabled="isLoading" @click="handleReset">重置</button>
              <button type="button" class="console-btn danger console-finish-btn" :disabled="!canFinish" @click="handleFinish">
                结束并评分
              </button>
            </div>
          </div>
        </div>
      </div>
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
  padding: 10px 12px;
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 34px auto;
  align-items: center;
  gap: 8px;
}

.history-select {
  width: 100%;
  min-width: 0;
  height: 34px;
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

.history-refresh-btn {
  width: 34px;
  height: 34px;
  padding: 0;
  border-radius: 9px;
  border: 1px solid #ddd2c6;
  background: #f7f3ee;
  color: #5f5448;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: border-color 0.18s ease, color 0.18s ease, transform 0.18s ease;
}

.history-refresh-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: #d97745;
  color: #d97745;
}

.history-refresh-btn:disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

.history-refresh-btn svg {
  width: 17px;
  height: 17px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.history-refresh-btn.loading svg {
  animation: refreshSpin 0.8s linear infinite;
}

@keyframes refreshSpin {
  to {
    transform: rotate(360deg);
  }
}

.interview-status-pill {
  min-width: 90px;
  height: 34px;
  border-radius: 999px;
  border: 1px solid #ded4c8;
  background: #f6f1ea;
  color: #6d6054;
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 12px;
  white-space: nowrap;
}

.interview-status-pill.active {
  border-color: #cbe5d0;
  background: #edf8f0;
  color: #2b7a45;
}

.interview-status-pill.finished {
  border-color: #efd2c4;
  background: #fff1ec;
  color: #b74a30;
}

.interview-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: currentColor;
  box-shadow: 0 0 0 4px color-mix(in srgb, currentColor 16%, transparent);
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

.interview-floating-tools {
  position: fixed;
  right: 24px;
  bottom: calc(clamp(190px, 24vh, 280px) + env(safe-area-inset-bottom));
  z-index: 260;
  pointer-events: none;
}

.floating-actions-stack {
  display: inline-flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: auto;
}

.floating-action-anchor {
  position: relative;
}

.floating-action-btn {
  width: 52px;
  height: 52px;
  padding: 0;
  border-radius: 50%;
  border: 1px solid #2d2521;
  background: #2d2521;
  color: #fff;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 12px 22px rgba(45, 37, 33, 0.24);
  transition: transform 0.16s ease, box-shadow 0.16s ease, background-color 0.16s ease, border-color 0.16s ease;
}

.floating-action-btn:hover,
.floating-action-btn.active {
  transform: translateY(-1px);
  border-color: #d97745;
  background: #d97745;
  box-shadow: 0 16px 28px rgba(217, 119, 69, 0.28);
}

.console-action-btn {
  background: #2d2521;
  border-color: #2d2521;
}

.console-action-btn:hover,
.console-action-btn.active {
  background: #d97745;
  border-color: #d97745;
}

.floating-action-btn svg {
  width: 21px;
  height: 21px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.floating-popover {
  position: absolute;
  right: calc(100% + 12px);
  bottom: 0;
  width: min(360px, calc(100vw - 112px));
  max-height: min(72dvh, 520px);
  overflow: auto;
  border: 1px solid #e1d4c6;
  border-radius: 18px;
  background: rgba(255, 252, 248, 0.98);
  box-shadow: 0 22px 54px rgba(45, 37, 33, 0.2);
  padding: 14px;
  backdrop-filter: blur(14px);
}

.floating-popover-title {
  color: #2d2521;
  font-size: 14px;
  font-weight: 800;
}

.mode-popover {
  width: min(310px, calc(100vw - 112px));
}

.mode-option-list {
  margin-top: 12px;
  display: grid;
  gap: 8px;
}

.mode-option-btn {
  min-height: 40px;
  border-radius: 12px;
  border: 1px solid #dfd2c2;
  background: #fff;
  color: #5f5448;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.35;
  padding: 9px 10px;
  text-align: left;
  cursor: pointer;
}

.mode-option-btn.active {
  border-color: #2d2521;
  background: #2d2521;
  color: #fff;
}

.controls-popover {
  width: min(380px, calc(100vw - 112px));
}

.console-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.console-helper {
  margin-top: 4px;
  color: #8a7461;
  font-size: 12px;
}

.console-status-pill {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 5px 10px;
  background: #f0ece6;
  color: #7f7162;
  font-size: 12px;
  font-weight: 800;
}

.console-status-pill.active {
  background: #eaf7ed;
  color: #2b7a45;
}

.console-timer-row {
  margin-top: 14px;
  display: grid;
  grid-template-columns: auto 1fr 1.2fr 1fr;
  gap: 6px;
  align-items: center;
}

.console-label {
  color: #7c7062;
  font-size: 12px;
  font-weight: 700;
}

.console-mini-btn,
.console-timer-value,
.console-btn {
  min-height: 36px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.console-mini-btn,
.console-btn {
  border: 1px solid #dfd2c2;
  background: #f7f3ee;
  color: #5f5448;
  cursor: pointer;
}

.console-timer-value {
  border: 1px solid #dfd2c2;
  background: #fff;
  color: #2d2521;
}

.console-action-grid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.console-btn.primary {
  border-color: #2d2521;
  background: #2d2521;
  color: #fff;
}

.console-btn.danger {
  border-color: #d97745;
  background: #d97745;
  color: #fff;
}

.console-btn.ghost {
  background: #fff;
}

.console-finish-btn {
  grid-column: 1 / -1;
  min-height: 40px;
}

.console-mini-btn:disabled,
.console-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

@media (max-width: 860px) {
  .ai-interviewer-panel {
    padding: 10px;
    gap: 7px;
    overflow-y: auto;
    overflow-x: hidden;
  }

  .topbar {
    grid-template-columns: minmax(0, 1fr) 36px auto;
    padding: 8px;
  }
}

@media (max-width: 600px) {
  .ai-interviewer-panel {
    padding: 6px 6px calc(6px + env(safe-area-inset-bottom));
    overflow: hidden;
  }

  .topbar {
    grid-template-columns: 32px minmax(0, 1fr);
    gap: 5px;
    padding: 6px;
    border-radius: 9px;
    overflow: hidden;
  }

  .history-select {
    grid-column: 1 / -1;
    width: 100%;
    min-width: 0;
    height: 32px;
    text-overflow: ellipsis;
    padding: 0 7px;
  }

  .history-refresh-btn {
    width: 32px;
    height: 30px;
    border-radius: 8px;
  }

  .history-refresh-btn svg {
    width: 15px;
    height: 15px;
  }

  .interview-status-pill {
    width: 100%;
    min-width: 0;
    height: 30px;
    font-size: 10.5px;
    gap: 5px;
    padding: 0 7px;
  }

  .interview-status-dot {
    width: 6px;
    height: 6px;
  }

  .final-banner {
    padding: 6px 8px;
    font-size: 11px;
    line-height: 1.5;
  }

  .workspace {
    flex: 1 1 auto;
    display: flex;
    min-height: 0;
  }

  .workspace > :first-child {
    flex: 1;
    min-height: 0;
  }

  .interview-floating-tools {
    right: 8px;
    bottom: calc(150px + env(safe-area-inset-bottom));
  }

  .floating-actions-stack {
    gap: 6px;
  }

  .floating-action-btn {
    width: 40px;
    height: 40px;
  }

  .floating-action-btn svg {
    width: 18px;
    height: 18px;
  }

  .floating-popover {
    right: calc(100% + 7px);
    width: min(292px, calc(100vw - 60px));
    max-height: min(72dvh, 540px);
    padding: 8px;
    border-radius: 12px;
  }

  .mode-popover,
  .controls-popover {
    width: min(292px, calc(100vw - 60px));
  }

  .console-header {
    flex-direction: column;
    gap: 8px;
  }

  .console-status-pill {
    width: 100%;
    text-align: center;
  }

  .console-timer-row {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin-top: 8px;
    gap: 5px;
  }

  .console-label {
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .console-mini-btn,
  .console-timer-value,
  .console-btn {
    min-width: 0;
    font-size: 10.5px;
    min-height: 30px;
    border-radius: 8px;
  }

  .console-action-grid {
    gap: 6px;
    margin-top: 8px;
  }

  .console-finish-btn {
    min-height: 34px;
  }
}
</style>
