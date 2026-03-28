import ResumeTemplate from './ResumeTemplate.vue'
import { resolveTemplatePreviewImage } from '../previewImage'
import type { ResumeTemplateDefinition } from '../types'

const previewImage = resolveTemplatePreviewImage('../../../assets/templates/resume/blue-card-preview.svg', import.meta.url)

export const BLUE_CARD_TEMPLATE: ResumeTemplateDefinition = {
  key: 'blue-card',
  name: '蓝色卡片模板',
  previewImage,
  component: ResumeTemplate,
}
