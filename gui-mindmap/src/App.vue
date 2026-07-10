<template>
  <div class="app">
    <AppHeader v-if="auth.isAuthenticated && !isEditorRoute" />
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'
import AppHeader from './components/AppHeader.vue'

const auth = useAuthStore()
const route = useRoute()

const isEditorRoute = computed(() => route.name === 'map-editor')
</script>

<style>
:root {
  /* Surface palette - Light Theme */
  --bg-base: #f8fafc;
  --bg-surface: #ffffff;
  --bg-elevated: #ffffff;
  --bg-hover: #f1f5f9;
  --bg-active: #e2e8f0;

  /* Border palette */
  --border-subtle: rgba(0, 0, 0, 0.04);
  --border-default: rgba(0, 0, 0, 0.08);
  --border-strong: rgba(0, 0, 0, 0.12);

  /* Text palette */
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-tertiary: #94a3b8;
  --text-inverse: #ffffff;

  /* Accent palette */
  --accent: #2563eb;
  --accent-hover: #1d4ed8;
  --accent-glow: rgba(37, 99, 235, 0.1);
  --accent-glow-strong: rgba(37, 99, 235, 0.2);

  /* Secondary accent */
  --accent-green: #10b981;
  --accent-green-glow: rgba(16, 185, 129, 0.1);

  /* Semantic colors */
  --color-error: #ef4444;
  --color-error-bg: #fef2f2;
  --color-warning: #f59e0b;
  --color-warning-bg: #fffbeb;
  --color-success: #10b981;
  --color-success-bg: #f0fdf4;
  --color-info: #3b82f6;
  --color-info-bg: #eff6ff;

  /* Typography */
  --font-display: 'Plus Jakarta Sans', 'Sora', sans-serif;
  --font-body: 'Inter', 'DM Sans', sans-serif;

  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
  --shadow-glow: 0 0 20px rgba(37, 99, 235, 0.1), 0 0 60px rgba(37, 99, 235, 0.05);

  /* Radii */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 18px;
  --radius-xl: 28px;

  /* Transitions */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-fast: 0.15s;
  --duration-normal: 0.25s;
  --duration-slow: 0.4s;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  width: 100%;
  height: 100%;
  font-family: var(--font-body);
  background: var(--bg-base);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--border-strong);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--text-tertiary);
}

/* Selection */
::selection {
  background: var(--accent-glow-strong);
  color: var(--text-primary);
}

.app {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* Global focus styles */
*:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
</style>
