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
type ResumeMobilePane = 'editor' | 'preview'
const activeMenu = ref<PrimaryMenuKey>('resume-editor')
const activeResumePane = ref<ResumeMobilePane>('editor')

function handleSelectMenu(key: PrimaryMenuKey) {
  activeMenu.value = key
  if (key === 'resume-editor') {
    activeResumePane.value = 'editor'
  }
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
        <div class="mobile-resume-tabs" role="tablist" aria-label="简历移动端视图切换">
          <button
            class="mobile-resume-tab"
            :class="{ active: activeResumePane === 'editor' }"
            type="button"
            role="tab"
            :aria-selected="activeResumePane === 'editor'"
            @click="activeResumePane = 'editor'"
          >
            编辑
          </button>
          <button
            class="mobile-resume-tab"
            :class="{ active: activeResumePane === 'preview' }"
            type="button"
            role="tab"
            :aria-selected="activeResumePane === 'preview'"
            @click="activeResumePane = 'preview'"
          >
            预览
          </button>
        </div>
        <EditorPanel
          class="resume-workspace-pane"
          :class="{ 'mobile-pane-hidden': activeResumePane !== 'editor' }"
        />
        <PreviewPanel
          class="resume-workspace-pane"
          :class="{ 'mobile-pane-hidden': activeResumePane !== 'preview' }"
        />
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
  min-height: 100vh;
  overflow: hidden;
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-width: 0;
}

.mobile-resume-tabs {
  display: none;
}

@supports (height: 100dvh) {
  .app-layout {
    height: 100dvh;
    min-height: 100dvh;
  }
}

@media (max-width: 760px) {
  .app-layout {
    height: 100dvh;
    min-height: 100dvh;
    padding-bottom: calc(68px + env(safe-area-inset-bottom));
    background: #f7f2ec;
  }

  .main-content {
    position: relative;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .mobile-resume-tabs {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 5px;
    padding: 7px 8px 6px;
    background: rgba(247, 242, 236, 0.96);
    border-bottom: 1px solid #e4d8cb;
    flex-shrink: 0;
    z-index: 4;
  }

  .mobile-resume-tab {
    min-height: 34px;
    border: 1px solid #dfd2c2;
    border-radius: 12px;
    background: #fff;
    color: #7b6a5b;
    font-size: 12px;
    font-weight: 800;
  }

  .mobile-resume-tab.active {
    border-color: #2d2521;
    background: #2d2521;
    color: #fff;
    box-shadow: 0 10px 20px rgba(45, 37, 33, 0.12);
  }

  .resume-workspace-pane {
    flex: 1 1 auto;
    min-height: 0;
    width: 100%;
  }

  .mobile-pane-hidden {
    display: none !important;
  }
}
</style>
