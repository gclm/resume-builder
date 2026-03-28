import ResumeTemplate from './ResumeTemplate.vue'
import { resolveTemplatePreviewImage } from '../previewImage'
import type { ResumeTemplateDefinition } from '../types'

const previewImage = resolveTemplatePreviewImage('../../../assets/templates/resume/green-icon-linear-preview.svg', import.meta.url)

export const GREEN_ICON_LINEAR_TEMPLATE: ResumeTemplateDefinition = {
  key: 'green-icon-linear',
  name: '绿色图标线性模板',
  previewImage,
  component: ResumeTemplate,
}
