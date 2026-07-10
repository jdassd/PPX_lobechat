<template>
  <header class="app-header">
    <router-link to="/" class="logo">
      <span class="logo-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="3" fill="currentColor"/>
          <circle cx="4" cy="6" r="2" fill="currentColor" opacity="0.6"/>
          <circle cx="20" cy="6" r="2" fill="currentColor" opacity="0.6"/>
          <circle cx="4" cy="18" r="2" fill="currentColor" opacity="0.6"/>
          <circle cx="20" cy="18" r="2" fill="currentColor" opacity="0.6"/>
          <line x1="10" y1="11" x2="5.5" y2="7" stroke="currentColor" stroke-width="1.2" opacity="0.4"/>
          <line x1="14" y1="11" x2="18.5" y2="7" stroke="currentColor" stroke-width="1.2" opacity="0.4"/>
          <line x1="10" y1="13" x2="5.5" y2="17" stroke="currentColor" stroke-width="1.2" opacity="0.4"/>
          <line x1="14" y1="13" x2="18.5" y2="17" stroke="currentColor" stroke-width="1.2" opacity="0.4"/>
        </svg>
      </span>
      <span class="logo-text">MindMap</span>
    </router-link>
    <nav class="nav-links">
      <router-link to="/" class="nav-item">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
        Maps
      </router-link>
      <router-link to="/teams" class="nav-item">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        Teams
      </router-link>
    </nav>
    <div class="user-menu">
      <div class="user-avatar">{{ initials }}</div>
      <span class="user-name">{{ auth.user?.display_name || auth.user?.username }}</span>
      <button class="btn-logout" @click="handleLogout">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const initials = computed(() => {
  const name = auth.user?.display_name || auth.user?.username || ''
  return name.slice(0, 2).toUpperCase()
})

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  gap: 32px;
  padding: 0 24px;
  height: 56px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
  backdrop-filter: blur(12px);
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--accent);
}

.logo-icon {
  display: flex;
  align-items: center;
}

.logo-text {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.nav-links {
  display: flex;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  text-decoration: none;
  padding: 7px 14px;
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast) var(--ease-out);
}

.nav-item:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.nav-item.router-link-active {
  color: var(--accent);
  background: var(--accent-glow);
}

.user-menu {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), #818cf8);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-inverse);
  letter-spacing: 0.02em;
}

.user-name {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.btn-logout {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: none;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.btn-logout:hover {
  border-color: var(--color-error);
  color: var(--color-error);
  background: var(--color-error-bg);
}
</style>
