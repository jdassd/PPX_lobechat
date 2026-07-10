<template>
  <div class="login-page">
    <div class="auth-bg">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
      <div class="grid-overlay"></div>
    </div>
    <div class="auth-card">
      <div class="auth-brand">
        <svg class="brand-icon" width="36" height="36" viewBox="0 0 24 24" fill="none">
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
        <h1>MindMap</h1>
      </div>
      <p class="auth-subtitle">Sign in to your workspace</p>
      <form @submit.prevent="handleLogin">
        <div class="field">
          <label>Username</label>
          <div class="input-wrap">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            <input v-model="username" type="text" required autocomplete="username" placeholder="Enter your username" />
          </div>
        </div>
        <div class="field">
          <label>Password</label>
          <div class="input-wrap">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            <input v-model="password" type="password" required autocomplete="current-password" placeholder="Enter your password" />
          </div>
        </div>
        <p v-if="error" class="error">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
          {{ error }}
        </p>
        <button type="submit" :disabled="submitting" class="btn-primary">
          <span v-if="submitting" class="spinner"></span>
          {{ submitting ? 'Signing in...' : 'Sign In' }}
        </button>
      </form>
      <p class="switch">
        Don't have an account? <router-link to="/register">Create one</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)

async function handleLogin() {
  error.value = ''
  submitting.value = true
  try {
    await auth.login(username.value, password.value)
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (e: any) {
    error.value = e.message || 'Login failed'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: #fdfdfd;
  position: relative;
  overflow: hidden;
}

.auth-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.15;
}

.orb-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, var(--accent), transparent 70%);
  top: -15%;
  right: -5%;
  animation: float1 25s ease-in-out infinite;
}

.orb-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, #818cf8, transparent 70%);
  bottom: -15%;
  left: -5%;
  animation: float2 30s ease-in-out infinite;
}

.orb-3 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, #f472b6, transparent 70%);
  top: 40%;
  left: 30%;
  animation: float3 20s ease-in-out infinite;
}

.grid-overlay {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(#f1f5f9 1.5px, transparent 1.5px),
    linear-gradient(90deg, #f1f5f9 1.5px, transparent 1.5px);
  background-size: 50px 50px;
  opacity: 0.5;
}

@keyframes float1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(-40px, 60px) scale(1.1); }
  66% { transform: translate(30px, -30px) scale(0.9); }
}

@keyframes float2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(50px, -40px) scale(1.15); }
  66% { transform: translate(-30px, 30px) scale(0.85); }
}

@keyframes float3 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(20px, 20px) scale(1.2); }
}

.auth-card {
  position: relative;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-xl);
  padding: 56px 48px;
  width: 440px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(0, 0, 0, 0.02);
  backdrop-filter: blur(40px);
  animation: cardIn 0.8s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes cardIn {
  from {
    opacity: 0;
    transform: translateY(40px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.auth-brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  margin-bottom: 8px;
}

.brand-icon {
  color: var(--accent);
  filter: drop-shadow(0 4px 12px var(--accent-glow));
}

.auth-brand h1 {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.04em;
}

.auth-subtitle {
  text-align: center;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-tertiary);
  margin-bottom: 40px;
}

.field {
  margin-bottom: 24px;
}

.field label {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 8px;
  padding-left: 4px;
}

.input-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  background: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: var(--radius-md);
  transition: all var(--duration-normal) var(--ease-out);
}

.input-wrap svg {
  color: var(--text-tertiary);
  flex-shrink: 0;
  transition: color var(--duration-fast);
}

.input-wrap:focus-within {
  border-color: var(--accent);
  background: #ffffff;
  box-shadow: 0 0 0 4px var(--accent-glow);
}

.input-wrap:focus-within svg {
  color: var(--accent);
}

.input-wrap input {
  flex: 1;
  padding: 14px 0;
  background: none;
  border: none;
  font-size: 15px;
  font-weight: 500;
  font-family: var(--font-body);
  color: var(--text-primary);
  outline: none;
}

.input-wrap input::placeholder {
  color: #94a3b8;
}

.error {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-error);
  font-size: 13px;
  font-weight: 500;
  margin: 0 0 20px;
  padding: 12px 16px;
  background: #fef2f2;
  border-radius: var(--radius-md);
  border: 1px solid rgba(239, 68, 68, 0.1);
}

.btn-primary {
  width: 100%;
  padding: 14px;
  background: #0f172a;
  color: #ffffff;
  border: none;
  border-radius: var(--radius-md);
  font-size: 15px;
  font-weight: 700;
  font-family: var(--font-body);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  transition: all var(--duration-normal) var(--ease-out);
  box-shadow: 0 10px 15px -3px rgba(15, 23, 42, 0.1);
}

.btn-primary:hover:not(:disabled) {
  background: #1e293b;
  transform: translateY(-2px);
  box-shadow: 0 20px 25px -5px rgba(15, 23, 42, 0.15);
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

.btn-primary:disabled {
  background: #94a3b8;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2.5px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.switch {
  text-align: center;
  margin-top: 32px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-tertiary);
}

.switch a {
  color: var(--accent);
  text-decoration: none;
  font-weight: 700;
  transition: all var(--duration-fast);
  padding: 2px 4px;
}

.switch a:hover {
  background: var(--accent-glow);
  border-radius: 4px;
}
</style>
