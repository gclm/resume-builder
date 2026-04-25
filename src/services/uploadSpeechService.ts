// author: jf
import { transcribeInterviewAudio } from '@/services/speechService'
import type { SpeechSession, SpeechTranscriptionCallbacks } from '@/services/browserSpeechService'

const TEXT = {
  unsupportedMediaDevice: '当前浏览器不支持麦克风访问',
  unsupportedRecorder: '当前浏览器不支持录音上传转写',
  emptyRecording: '录音内容为空，请重试',
  recordingFailed: '录音失败，请检查麦克风权限后重试',
} as const

export interface UploadSpeechTranscriptionOptions {
  language?: string
  callbacks?: SpeechTranscriptionCallbacks
}

function resolveRecorderMimeType(): string {
  if (typeof MediaRecorder === 'undefined' || typeof MediaRecorder.isTypeSupported !== 'function') {
    return 'audio/webm'
  }

  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/mpeg']
  for (const item of candidates) {
    if (MediaRecorder.isTypeSupported(item)) {
      return item
    }
  }
  return 'audio/webm'
}

function stopStreamTracks(stream: MediaStream | null) {
  if (!stream) return
  for (const track of stream.getTracks()) {
    track.stop()
  }
}

function asErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message
  }
  return TEXT.recordingFailed
}

export class UploadSpeechTranscriptionSession implements SpeechSession {
  private readonly language: string
  private readonly callbacks: SpeechTranscriptionCallbacks

  private mediaRecorder: MediaRecorder | null = null
  private mediaStream: MediaStream | null = null
  private chunks: Blob[] = []
  private stopped = false
  private pendingStopPromise: Promise<void> | null = null

  constructor(options: UploadSpeechTranscriptionOptions = {}) {
    this.language = (options.language || 'zh').trim() || 'zh'
    this.callbacks = options.callbacks || {}
  }

  async start(): Promise<void> {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error(TEXT.unsupportedMediaDevice)
    }
    if (typeof MediaRecorder === 'undefined') {
      throw new Error(TEXT.unsupportedRecorder)
    }

    this.stopped = false
    this.pendingStopPromise = null
    this.chunks = []
    this.callbacks.onStateChange?.('connecting')

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
      const mimeType = resolveRecorderMimeType()
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)

      this.mediaStream = stream
      this.mediaRecorder = recorder
      recorder.onstart = () => {
        if (this.stopped) return
        this.callbacks.onStateChange?.('connected')
      }
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          this.chunks.push(event.data)
        }
      }
      recorder.onerror = () => {
        if (this.stopped) return
        this.callbacks.onError?.(TEXT.recordingFailed)
        void this.stop({ silent: true })
      }
      recorder.start(250)
    } catch (error) {
      await this.stop({ silent: true })
      throw error
    }
  }

  async stop(options: { silent?: boolean } = {}): Promise<void> {
    if (this.pendingStopPromise) {
      return this.pendingStopPromise
    }
    if (this.stopped && !this.mediaRecorder && !this.mediaStream) {
      return
    }

    this.stopped = true
    const recorder = this.mediaRecorder
    const stream = this.mediaStream
    this.mediaRecorder = null
    this.mediaStream = null

    const finalize = async () => {
      try {
        if (!options.silent) {
          const blob = new Blob(this.chunks, { type: recorder?.mimeType || resolveRecorderMimeType() || 'audio/webm' })
          if (!blob || blob.size <= 0) {
            throw new Error(TEXT.emptyRecording)
          }
          this.callbacks.onStateChange?.('transcribing')
          const transcript = await transcribeInterviewAudio(blob)
          const mergedText = transcript.trim()
          if (mergedText) {
            this.callbacks.onFinalText?.(mergedText, mergedText)
            this.callbacks.onPartialText?.(mergedText)
          }
        }
        this.callbacks.onStateChange?.('closed')
      } catch (error) {
        this.callbacks.onError?.(asErrorMessage(error))
      } finally {
        this.chunks = []
        stopStreamTracks(stream)
        this.pendingStopPromise = null
      }
    }

    this.pendingStopPromise = new Promise((resolve) => {
      const finalizeOnce = async () => {
        await finalize()
        resolve()
      }

      if (!recorder || recorder.state === 'inactive') {
        void finalizeOnce()
        return
      }

      recorder.onstop = () => {
        void finalizeOnce()
      }
      try {
        recorder.stop()
      } catch {
        void finalizeOnce()
      }
    })

    return this.pendingStopPromise
  }
}
