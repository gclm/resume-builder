// author: jf
import {
  type RealtimeClientSecretRequest,
  type RealtimeClientSecretResponse,
  postRealtimeCallSdp,
  postRealtimeClientSecret,
} from '@/api/realtimeSpeechApi'
import type { SpeechRuntimeState } from '@/services/browserSpeechService'

const TEXT = {
  getSecretFailed: '\u83b7\u53d6\u5b9e\u65f6\u8bed\u97f3\u4f1a\u8bdd\u5931\u8d25',
  missingSecret: '\u540e\u7aef\u672a\u8fd4\u56de\u53ef\u7528\u7684\u5b9e\u65f6\u4f1a\u8bdd\u5bc6\u94a5',
  missingRealtimeBaseUrl: '\u540e\u7aef\u672a\u8fd4\u56de\u5b9e\u65f6\u670d\u52a1\u5730\u5740',
  unsupportedMediaDevice: '\u5f53\u524d\u6d4f\u89c8\u5668\u4e0d\u652f\u6301\u9ea6\u514b\u98ce\u8bbf\u95ee',
  unsupportedWebrtc: '\u5f53\u524d\u6d4f\u89c8\u5668\u4e0d\u652f\u6301\u5b9e\u65f6\u8bed\u97f3\u8bc6\u522b',
  dataChannelError: '\u5b9e\u65f6\u8bed\u97f3\u901a\u9053\u5f02\u5e38\uff0c\u8bf7\u91cd\u8bd5',
  connectionDisconnected: '\u5b9e\u65f6\u8bed\u97f3\u8fde\u63a5\u65ad\u5f00\uff0c\u8bf7\u91cd\u8bd5',
  connectFailed: '\u5efa\u7acb\u5b9e\u65f6\u8bed\u97f3\u8fde\u63a5\u5931\u8d25',
  recognitionFailed: '\u5b9e\u65f6\u8bed\u97f3\u8bc6\u522b\u5931\u8d25',
  connectionTimeout: '\u5b9e\u65f6\u8bed\u97f3\u8fde\u63a5\u8d85\u65f6\uff0c\u8bf7\u91cd\u8bd5',
} as const

export interface RealtimeTranscriptionCallbacks {
  onPartialText?: (text: string) => void
  onFinalText?: (segment: string, mergedText: string) => void
  onStateChange?: (state: SpeechRuntimeState) => void
  onError?: (message: string) => void
}

export interface RealtimeTranscriptionOptions {
  model?: string
  language?: string
  callbacks?: RealtimeTranscriptionCallbacks
}

function extractErrorText(text: string): string {
  const cleaned = text.trim()
  if (!cleaned) return ''
  try {
    const parsed = JSON.parse(cleaned) as { error?: string; message?: string }
    return parsed.message?.trim() || parsed.error?.trim() || cleaned
  } catch {
    return cleaned
  }
}

function normalizeBaseUrl(baseUrl: string): string {
  return (baseUrl || '').trim().replace(/\/+$/, '')
}

function normalizePath(path: string, fallback: string): string {
  const value = (path || '').trim() || fallback
  return value.startsWith('/') ? value : `/${value}`
}

function buildRealtimeCallsUrl(baseUrl: string, callsPath?: string): string {
  return `${normalizeBaseUrl(baseUrl)}${normalizePath(callsPath || '', '/v1/realtime/calls')}`
}

function asText(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

async function requestRealtimeClientSecret(
  payload: RealtimeClientSecretRequest = {},
  signal?: AbortSignal
): Promise<RealtimeClientSecretResponse> {
  const response = await postRealtimeClientSecret(payload, signal)

  if (!response.ok) {
    const errorText = extractErrorText(await response.text().catch(() => ''))
    throw new Error(`${TEXT.getSecretFailed} (${response.status}): ${errorText || response.statusText}`)
  }

  const data = (await response.json().catch(() => ({}))) as RealtimeClientSecretResponse
  const clientSecret = asText(data.clientSecret).trim()
  if (!clientSecret) {
    throw new Error(TEXT.missingSecret)
  }

  const realtimeApiBaseUrl = normalizeBaseUrl(data.realtimeApiBaseUrl)
  if (!realtimeApiBaseUrl) {
    throw new Error(TEXT.missingRealtimeBaseUrl)
  }

  return {
    ...data,
    clientSecret,
    realtimeApiBaseUrl,
    realtimeCallsPath: normalizePath(data.realtimeCallsPath || '', '/v1/realtime/calls'),
  }
}

function waitForIceGatheringComplete(peerConnection: RTCPeerConnection): Promise<void> {
  if (peerConnection.iceGatheringState === 'complete') {
    return Promise.resolve()
  }

  return new Promise((resolve) => {
    const handleStateChange = () => {
      if (peerConnection.iceGatheringState !== 'complete') {
        return
      }
      peerConnection.removeEventListener('icegatheringstatechange', handleStateChange)
      resolve()
    }

    peerConnection.addEventListener('icegatheringstatechange', handleStateChange)
    setTimeout(() => {
      peerConnection.removeEventListener('icegatheringstatechange', handleStateChange)
      resolve()
    }, 2000)
  })
}

function extractTranscriptFromEvent(payload: Record<string, unknown>, fallback: string): string {
  const direct = asText(payload.transcript).trim()
  if (direct) {
    return direct
  }

  const text = asText(payload.text).trim()
  if (text) {
    return text
  }

  const item = payload.item as Record<string, unknown> | undefined
  const content = Array.isArray(item?.content) ? item.content : []
  for (const part of content) {
    if (!part || typeof part !== 'object') continue
    const transcript = asText((part as Record<string, unknown>).transcript).trim()
    if (transcript) {
      return transcript
    }
    const innerText = asText((part as Record<string, unknown>).text).trim()
    if (innerText) {
      return innerText
    }
  }

  return fallback
}

export class RealtimeTranscriptionSession {
  private readonly model?: string
  private readonly language?: string
  private readonly callbacks: RealtimeTranscriptionCallbacks

  private peerConnection: RTCPeerConnection | null = null
  private dataChannel: RTCDataChannel | null = null
  private microphoneStream: MediaStream | null = null
  private finalSegments: string[] = []
  private partialSegment = ''
  private stopped = false

  constructor(options: RealtimeTranscriptionOptions = {}) {
    this.model = options.model?.trim()
    this.language = options.language?.trim()
    this.callbacks = options.callbacks || {}
  }

  async start(): Promise<void> {
    if (this.peerConnection) return
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error(TEXT.unsupportedMediaDevice)
    }
    if (typeof RTCPeerConnection === 'undefined') {
      throw new Error(TEXT.unsupportedWebrtc)
    }

    this.stopped = false
    this.callbacks.onStateChange?.('connecting')

    try {
      const clientSecret = await requestRealtimeClientSecret({
        model: this.model,
        language: this.language,
      })

      const microphoneStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
      const peerConnection = new RTCPeerConnection()

      this.microphoneStream = microphoneStream
      this.peerConnection = peerConnection

      for (const track of microphoneStream.getTracks()) {
        peerConnection.addTrack(track, microphoneStream)
      }

      const dataChannel = peerConnection.createDataChannel('oai-events')
      this.attachDataChannel(dataChannel)

      peerConnection.ondatachannel = (event) => {
        if (this.dataChannel) return
        this.attachDataChannel(event.channel)
      }

      peerConnection.onconnectionstatechange = () => {
        if (peerConnection.connectionState === 'connected') {
          this.callbacks.onStateChange?.('connected')
          return
        }

        if (['failed', 'disconnected', 'closed'].includes(peerConnection.connectionState)) {
          this.handleError(TEXT.connectionDisconnected)
        }
      }

      const offer = await peerConnection.createOffer()
      await peerConnection.setLocalDescription(offer)
      await waitForIceGatheringComplete(peerConnection)

      const localSdp = peerConnection.localDescription?.sdp || offer.sdp || ''
      const endpoint = buildRealtimeCallsUrl(clientSecret.realtimeApiBaseUrl, clientSecret.realtimeCallsPath)
      const response = await postRealtimeCallSdp(endpoint, clientSecret.clientSecret, localSdp)

      if (!response.ok) {
        const errorText = extractErrorText(await response.text().catch(() => ''))
        throw new Error(`${TEXT.connectFailed} (${response.status}): ${errorText || response.statusText}`)
      }

      const answerSdp = await response.text()
      await peerConnection.setRemoteDescription({
        type: 'answer',
        sdp: answerSdp,
      })

      await this.waitForConnected(peerConnection, 12000)
    } catch (error) {
      await this.stop({ silent: true })
      throw error
    }
  }

  async stop(options: { silent?: boolean } = {}): Promise<void> {
    if (this.stopped) return
    this.stopped = true

    const dataChannel = this.dataChannel
    const peerConnection = this.peerConnection
    const microphoneStream = this.microphoneStream

    this.dataChannel = null
    this.peerConnection = null
    this.microphoneStream = null
    this.partialSegment = ''

    if (dataChannel && dataChannel.readyState !== 'closed') {
      try {
        dataChannel.close()
      } catch {
        // Ignore close errors.
      }
    }

    if (peerConnection && peerConnection.connectionState !== 'closed') {
      try {
        peerConnection.close()
      } catch {
        // Ignore close errors.
      }
    }

    if (microphoneStream) {
      for (const track of microphoneStream.getTracks()) {
        track.stop()
      }
    }

    this.callbacks.onStateChange?.('closed')
    if (!options.silent) {
      this.emitMergedText()
    }
  }

  private attachDataChannel(channel: RTCDataChannel) {
    this.dataChannel = channel
    channel.onmessage = (event) => {
      this.handleRealtimeEvent(event.data)
    }
    channel.onerror = () => {
      this.handleError(TEXT.dataChannelError)
    }
  }

  private waitForConnected(peerConnection: RTCPeerConnection, timeoutMs: number): Promise<void> {
    if (peerConnection.connectionState === 'connected') {
      this.callbacks.onStateChange?.('connected')
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      let settled = false

      const onStateChange = () => {
        if (settled) return
        if (peerConnection.connectionState === 'connected') {
          settled = true
          cleanup()
          this.callbacks.onStateChange?.('connected')
          resolve()
          return
        }
        if (['failed', 'disconnected', 'closed'].includes(peerConnection.connectionState)) {
          settled = true
          cleanup()
          reject(new Error(TEXT.connectionDisconnected))
        }
      }

      const timer = setTimeout(() => {
        if (settled) return
        settled = true
        cleanup()
        reject(new Error(TEXT.connectionTimeout))
      }, timeoutMs)

      const cleanup = () => {
        clearTimeout(timer)
        peerConnection.removeEventListener('connectionstatechange', onStateChange)
      }

      peerConnection.addEventListener('connectionstatechange', onStateChange)
      onStateChange()
    })
  }

  private handleRealtimeEvent(raw: unknown) {
    const text = asText(raw)
    if (!text.trim()) return

    let payload: Record<string, unknown>
    try {
      payload = JSON.parse(text) as Record<string, unknown>
    } catch {
      return
    }

    const eventType = asText(payload.type)
    if (!eventType) return

    if (
      eventType === 'conversation.item.input_audio_transcription.delta' ||
      eventType === 'conversation.item.input_audio_transcription.partial'
    ) {
      const delta = asText(payload.delta) || asText(payload.text)
      if (!delta) return
      this.partialSegment += delta
      this.emitMergedText()
      return
    }

    if (
      eventType === 'conversation.item.input_audio_transcription.completed' ||
      eventType === 'conversation.item.input_audio_transcription.final'
    ) {
      const transcript = extractTranscriptFromEvent(payload, this.partialSegment).trim()
      this.partialSegment = ''
      if (transcript) {
        this.finalSegments.push(transcript)
      }

      const merged = this.buildMergedText()
      if (transcript) {
        this.callbacks.onFinalText?.(transcript, merged)
      }
      this.callbacks.onPartialText?.(merged)
      return
    }

    if (eventType === 'error' || eventType.endsWith('.failed')) {
      const message = this.extractRealtimeErrorMessage(payload)
      this.handleError(message || TEXT.recognitionFailed)
    }
  }

  private emitMergedText() {
    this.callbacks.onPartialText?.(this.buildMergedText())
  }

  private buildMergedText(): string {
    const parts = [...this.finalSegments]
    const partial = this.partialSegment.trim()
    if (partial) {
      parts.push(partial)
    }
    return parts.join('\n')
  }

  private extractRealtimeErrorMessage(payload: Record<string, unknown>): string {
    const directMessage = asText(payload.message).trim()
    if (directMessage) return directMessage

    const error = payload.error as Record<string, unknown> | undefined
    const nestedMessage = error ? asText(error.message).trim() : ''
    if (nestedMessage) return nestedMessage

    return ''
  }

  private handleError(message: string) {
    if (this.stopped) return
    this.callbacks.onError?.(message)
    void this.stop({ silent: true })
  }
}
