<!-- author: jf -->
<script setup lang="ts">
import { ref } from 'vue'
import KnowledgeBasePanel from '@/components/ai/knowledge/KnowledgeBasePanel.vue'
import AiInterviewerPanel from '@/components/ai/interview/AiInterviewerPanel.vue'
import ModuleSidebar from '@/components/common/ModuleSidebar.vue'
import EditorPanel from '@/components/resume/EditorPanel.vue'
import PreviewPanel from '@/components/resume/PreviewPanel.vue'

const sidebarCollapsed = ref(false)
type PrimaryMenuKey = 'resume-editor' | 'ai-interviewer' | 'knowledge-base'
const activeMenu = ref<PrimaryMenuKey>('resume-editor')

function handleSelectMenu(key: PrimaryMenuKey) {
  activeMenu.value = key
}
</script>

<template>
  <div class="app-layout">
    <ModuleSidebar
      :collapsed="sidebarCollapsed"
      :active-menu="activeMenu"
      @toggle-collapse="sidebarCollapsed = !sidebarCollapsed"
      @select-menu="handleSelectMenu"
    />
    <div class="main-content">
      <template v-if="activeMenu === 'resume-editor'">
        <EditorPanel />
        <PreviewPanel />
      </template>
      <AiInterviewerPanel v-else-if="activeMenu === 'ai-interviewer'" />
      <KnowledgeBasePanel v-else />
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-width: 0;
}
</style>
