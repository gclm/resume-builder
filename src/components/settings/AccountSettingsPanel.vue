<!-- author: jf -->
<script setup lang="ts">
type ThemeMode = 'light' | 'dark'

const props = defineProps<{
  themeMode: ThemeMode
}>()

const emit = defineEmits<{
  (e: 'set-theme', mode: ThemeMode): void
}>()

const themeOptions: Array<{
  mode: ThemeMode
  label: string
}> = [
  {
    mode: 'light',
    label: '光明',
  },
  {
    mode: 'dark',
    label: '黑暗',
  },
]

function selectTheme(mode: ThemeMode) {
  if (props.themeMode === mode) return
  emit('set-theme', mode)
}
</script>

<template>
  <main class="account-settings-panel" :class="{ dark: props.themeMode === 'dark' }">
    <section class="theme-setting-card" aria-labelledby="theme-setting-title">
      <div class="theme-setting-main">
        <span class="theme-setting-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M12 3v2m0 14v2M5 5l1.4 1.4M17.6 17.6 19 19M3 12h2m14 0h2M5 19l1.4-1.4M17.6 6.4 19 5" />
            <circle cx="12" cy="12" r="4" />
          </svg>
        </span>
        <div class="theme-setting-copy">
          <h2 id="theme-setting-title">主题模式</h2>
          <span>{{ props.themeMode === 'dark' ? '当前黑暗' : '当前光明' }}</span>
        </div>
      </div>

      <div class="theme-toggle-group" role="radiogroup" aria-label="主题模式">
        <button
          v-for="option in themeOptions"
          :key="option.mode"
          class="theme-toggle-option"
          :class="{ active: props.themeMode === option.mode }"
          type="button"
          role="radio"
          :aria-checked="props.themeMode === option.mode"
          @click="selectTheme(option.mode)"
        >
          {{ option.label }}
        </button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.account-settings-panel {
  --config-bg: #f7f2ec;
  --config-surface: rgba(255, 252, 248, 0.94);
  --config-surface-soft: #fff7ef;
  --config-border: rgba(122, 91, 68, 0.14);
  --config-text: #2d2521;
  --config-muted: #7b6a5b;
  --config-accent: #d97745;
  --config-accent-strong: #2d2521;
  --config-shadow: 0 24px 48px rgba(45, 37, 33, 0.1);

  flex: 1;
  min-width: 0;
  height: 100%;
  overflow: auto;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 32px;
  background:
    radial-gradient(circle at 18% 10%, rgba(217, 119, 69, 0.12), transparent 28%),
    linear-gradient(135deg, var(--config-bg) 0%, #efe4d8 100%);
  color: var(--config-text);
}

.account-settings-panel.dark {
  --config-bg: #100f0d;
  --config-surface: rgba(24, 20, 16, 0.96);
  --config-surface-soft: #201912;
  --config-border: rgba(255, 208, 168, 0.14);
  --config-text: #f7efe5;
  --config-muted: #c8b7a5;
  --config-accent: #f08a45;
  --config-accent-strong: #ffd0a8;
  --config-shadow: 0 28px 58px rgba(0, 0, 0, 0.38);
  background:
    radial-gradient(circle at 18% 10%, rgba(240, 138, 69, 0.12), transparent 28%),
    linear-gradient(135deg, #100f0d 0%, #18120d 100%);
}

.theme-setting-card {
  width: min(720px, 100%);
  min-height: 88px;
  padding: 18px;
  border: 1px solid var(--config-border);
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.52), transparent),
    var(--config-surface);
  box-shadow: var(--config-shadow);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.account-settings-panel.dark .theme-setting-card {
  background:
    linear-gradient(135deg, rgba(240, 138, 69, 0.08), transparent),
    var(--config-surface);
}

.theme-setting-main {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.theme-setting-icon {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  background: var(--config-accent-strong);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.account-settings-panel.dark .theme-setting-icon {
  color: #15100c;
}

.theme-setting-icon svg {
  width: 20px;
  height: 20px;
}

.theme-setting-icon path,
.theme-setting-icon circle {
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.theme-setting-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.theme-setting-copy h2 {
  margin: 0;
  color: var(--config-text);
  font-size: 16px;
  font-weight: 900;
  line-height: 1.25;
}

.theme-setting-copy span {
  color: var(--config-muted);
  font-size: 12px;
  font-weight: 800;
  line-height: 1.25;
}

.theme-toggle-group {
  padding: 4px;
  border-radius: 999px;
  background: var(--config-surface-soft);
  border: 1px solid var(--config-border);
  display: inline-flex;
  gap: 4px;
  flex-shrink: 0;
}

.theme-toggle-option {
  min-width: 64px;
  height: 34px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--config-muted);
  font-size: 13px;
  font-weight: 900;
  cursor: pointer;
  transition:
    background-color 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}

.theme-toggle-option:hover,
.theme-toggle-option:focus-visible {
  color: var(--config-text);
  outline: none;
}

.theme-toggle-option.active {
  background: var(--config-accent);
  color: #15100c;
  box-shadow: 0 8px 18px rgba(217, 119, 69, 0.18);
}

@media (max-width: 760px) {
  .account-settings-panel {
    padding: 8px;
  }

  .theme-setting-card {
    min-height: 68px;
    padding: 10px;
    border-radius: 16px;
    gap: 8px;
  }

  .theme-setting-main {
    gap: 8px;
  }

  .theme-setting-icon {
    width: 30px;
    height: 30px;
    border-radius: 10px;
  }

  .theme-setting-icon svg {
    width: 16px;
    height: 16px;
  }

  .theme-setting-copy h2 {
    font-size: 13px;
  }

  .theme-setting-copy span {
    font-size: 10px;
  }

  .theme-toggle-group {
    padding: 3px;
    gap: 2px;
  }

  .theme-toggle-option {
    min-width: 48px;
    height: 28px;
    font-size: 11px;
  }
}
</style>
