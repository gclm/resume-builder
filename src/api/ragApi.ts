// author: jf
import { API_BASE_PATH } from './apiBase'

const RAG_UPLOAD_TIMEOUT_MS = 300_000

export interface RagUploadFileResult {
  fileName: string
  contentType: string
  sourceType: string
  ingestSource: string
  chunkCount: number
  insertedCount: number
  status: string
  errorMessage?: string | null
}

export interface RagUploadResponse {
  totalFiles: number
  succeededFiles: number
  failedFiles: number
  inserted: number
  files: RagUploadFileResult[]
}

export function getRagUploadEndpoint(): string {
  return `${API_BASE_PATH}/ai/rag/upload`
}

export async function uploadKnowledgeAssets(
  files: File[],
  signal?: AbortSignal
): Promise<RagUploadResponse> {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }

  const requestController = new AbortController()
  let didTimeout = false
  const handleExternalAbort = () => requestController.abort(signal?.reason)
  if (signal) {
    if (signal.aborted) {
      requestController.abort(signal.reason)
    } else {
      signal.addEventListener('abort', handleExternalAbort, { once: true })
    }
  }
  const timeoutId = setTimeout(() => {
    didTimeout = true
    requestController.abort()
  }, RAG_UPLOAD_TIMEOUT_MS)

  let response: Response
  try {
    response = await fetch(getRagUploadEndpoint(), {
      method: 'POST',
      headers: {
        Accept: 'application/json',
      },
      body: formData,
      signal: requestController.signal,
    })
  } catch (error) {
    if (didTimeout) {
      throw new Error(
        `知识库上传超时（${Math.floor(RAG_UPLOAD_TIMEOUT_MS / 1000)} 秒），请检查 Embedding 服务与 pgvector 连接`
      )
    }
    if (signal?.aborted) {
      throw new Error('已取消上传')
    }
    if (error instanceof Error && error.message) {
      throw new Error(`知识库上传失败：${error.message}`)
    }
    throw new Error('知识库上传失败')
  } finally {
    clearTimeout(timeoutId)
    if (signal) {
      signal.removeEventListener('abort', handleExternalAbort)
    }
  }

  const payload = (await response.json().catch(() => null)) as
    | RagUploadResponse
    | { detail?: string }
    | null

  if (!response.ok) {
    throw new Error(payload && 'detail' in payload && payload.detail ? payload.detail : '知识库上传失败')
  }

  if (!payload || !('files' in payload)) {
    throw new Error('知识库上传返回了无效响应')
  }

  return payload
}
