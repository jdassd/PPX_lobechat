<template>
  <div class="team-detail-page">
    <div v-if="team" class="content">
      <div class="team-header">
        <div class="team-header-left">
          <router-link to="/teams" class="back-link">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
            Back
          </router-link>
          <div v-if="!editingName" class="team-title">
            <h1>{{ team.name }}</h1>
            <button v-if="isAdmin" class="btn-edit" @click="editingName = true">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
          </div>
          <div v-else class="edit-name">
            <input v-model="editName" @keyup.enter="saveName" />
            <button class="btn-save" @click="saveName">Save</button>
            <button class="btn-cancel" @click="editingName = false">Cancel</button>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-header">
          <h2>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            Members
          </h2>
          <span class="count">{{ members.length }}</span>
        </div>
        <div class="member-list">
          <div v-for="m in members" :key="m.id" class="member-item">
            <div class="member-avatar">{{ (m.display_name || m.username || '').slice(0, 2).toUpperCase() }}</div>
            <div class="member-info">
              <span class="member-name">{{ m.display_name || m.username }}</span>
              <span class="member-email">{{ m.email }}</span>
            </div>
            <div class="member-actions">
              <select
                v-if="isAdmin && m.role !== 'owner'"
                :value="m.role"
                class="role-select"
                @change="changeRole(m.id, ($event.target as HTMLSelectElement).value)"
              >
                <option value="admin">admin</option>
                <option value="editor">editor</option>
                <option value="viewer">viewer</option>
              </select>
              <span v-else class="role-badge" :class="m.role">{{ m.role }}</span>
              <button
                v-if="isAdmin && m.role !== 'owner'"
                class="btn-remove"
                @click="removeMember(m.id)"
              >Remove</button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="isAdmin" class="section">
        <div class="section-header">
          <h2>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></svg>
            Invite Member
          </h2>
        </div>
        <div class="invite-form">
          <div class="invite-input-group">
            <svg class="invite-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
            <input v-model="inviteEmail" type="email" placeholder="Email address" />
          </div>
          <select v-model="inviteRole" class="role-select">
            <option value="viewer">viewer</option>
            <option value="editor">editor</option>
            <option value="admin">admin</option>
          </select>
          <button class="btn-invite" @click="inviteMember">Invite</button>
        </div>
        <p v-if="inviteError" class="msg-error">{{ inviteError }}</p>
        <p v-if="inviteSuccess" class="msg-success">{{ inviteSuccess }}</p>
      </div>

      <div class="section">
        <div class="section-header">
          <h2>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="2.5"/><circle cx="5" cy="8" r="1.5" opacity="0.5"/><circle cx="19" cy="8" r="1.5" opacity="0.5"/></svg>
            Team Maps
          </h2>
          <span class="count">{{ teamMaps.length }}</span>
        </div>
        <div class="map-list">
          <div v-for="m in teamMaps" :key="m.id" class="map-item" @click="router.push(`/map/${m.id}`)">
            <div class="map-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="2.5"/><circle cx="5" cy="8" r="1.5" opacity="0.5"/><circle cx="19" cy="8" r="1.5" opacity="0.5"/>
                <line x1="10" y1="11" x2="6.5" y2="9" opacity="0.3"/><line x1="14" y1="11" x2="17.5" y2="9" opacity="0.3"/>
              </svg>
            </div>
            <span class="map-name">{{ m.name }}</span>
            <svg class="chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
          </div>
          <p v-if="teamMaps.length === 0" class="empty">No maps in this team yet.</p>
        </div>
      </div>
    </div>
    <div v-else class="loading">
      <span class="spinner"></span>
      Loading...
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiJson } from '../services/api'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const team = ref<any>(null)
const members = ref<any[]>([])
const teamMaps = ref<any[]>([])
const editingName = ref(false)
const editName = ref('')
const inviteEmail = ref('')
const inviteRole = ref('viewer')
const inviteError = ref('')
const inviteSuccess = ref('')

const teamId = computed(() => route.params.id as string)

const myRole = computed(() => {
  const me = members.value.find(m => m.id === auth.user?.id)
  return me?.role || ''
})

const isAdmin = computed(() => ['owner', 'admin'].includes(myRole.value))

async function fetchTeam() {
  team.value = await apiJson(`/api/teams/${teamId.value}`)
  editName.value = team.value.name
}

async function fetchMembers() {
  members.value = await apiJson(`/api/teams/${teamId.value}/members`)
}

async function fetchTeamMaps() {
  const allMaps = await apiJson('/api/maps')
  teamMaps.value = allMaps.filter((m: any) => m.team_id === teamId.value)
}

async function saveName() {
  await apiJson(`/api/teams/${teamId.value}`, {
    method: 'PUT',
    body: JSON.stringify({ name: editName.value }),
  })
  team.value.name = editName.value
  editingName.value = false
}

async function changeRole(memberId: string, role: string) {
  await apiJson(`/api/teams/${teamId.value}/members/${memberId}`, {
    method: 'PUT',
    body: JSON.stringify({ role }),
  })
  await fetchMembers()
}

async function removeMember(memberId: string) {
  await apiJson(`/api/teams/${teamId.value}/members/${memberId}`, { method: 'DELETE' })
  await fetchMembers()
}

async function inviteMember() {
  inviteError.value = ''
  inviteSuccess.value = ''
  try {
    await apiJson(`/api/teams/${teamId.value}/members`, {
      method: 'POST',
      body: JSON.stringify({ email: inviteEmail.value, role: inviteRole.value }),
    })
    inviteSuccess.value = `Invitation sent to ${inviteEmail.value}`
    inviteEmail.value = ''
  } catch (e: any) {
    inviteError.value = e.message
  }
}

onMounted(() => {
  fetchTeam()
  fetchMembers()
  fetchTeamMaps()
})
</script>

<style scoped>
.team-detail-page {
  max-width: 720px;
  margin: 0 auto;
  padding: 32px 24px 48px;
  animation: pageIn 0.4s var(--ease-out) both;
}

@keyframes pageIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.team-header {
  margin-bottom: 36px;
}

.team-header-left {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-tertiary);
  text-decoration: none;
  transition: color var(--duration-fast);
}

.back-link:hover {
  color: var(--accent);
}

.team-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.team-title h1 {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.03em;
  margin: 0;
}

.btn-edit {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  background: none;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.btn-edit:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-glow);
}

.edit-name {
  display: flex;
  gap: 8px;
  align-items: center;
}

.edit-name input {
  padding: 8px 12px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: 16px;
  font-family: var(--font-body);
  color: var(--text-primary);
  outline: none;
}

.edit-name input:focus {
  border-color: var(--accent);
}

.btn-save {
  padding: 8px 16px;
  background: var(--accent);
  color: var(--text-inverse);
  border: none;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-cancel {
  padding: 8px 16px;
  background: none;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
}

.section {
  margin-bottom: 32px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.section-header h2 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.count {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  background: var(--bg-elevated);
  padding: 2px 8px;
  border-radius: 10px;
}

.member-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}

.member-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, #818cf8, var(--accent));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-inverse);
  flex-shrink: 0;
}

.member-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.member-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.member-email {
  font-size: 12px;
  color: var(--text-tertiary);
}

.member-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.role-select {
  padding: 5px 10px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-family: var(--font-body);
  color: var(--text-secondary);
  outline: none;
  cursor: pointer;
}

.role-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: var(--bg-hover);
  color: var(--text-secondary);
}

.role-badge.owner {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.role-badge.admin {
  background: var(--accent-glow);
  color: var(--accent);
}

.role-badge.editor {
  background: var(--accent-green-glow);
  color: var(--accent-green);
}

.btn-remove {
  padding: 5px 12px;
  background: none;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  color: var(--color-error);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.btn-remove:hover {
  border-color: var(--color-error);
  background: var(--color-error-bg);
}

.invite-form {
  display: flex;
  gap: 8px;
}

.invite-input-group {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  transition: all var(--duration-fast) var(--ease-out);
}

.invite-icon {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.invite-input-group:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-glow);
}

.invite-input-group:focus-within .invite-icon {
  color: var(--accent);
}

.invite-input-group input {
  flex: 1;
  padding: 10px 0;
  background: none;
  border: none;
  font-size: 13px;
  font-family: var(--font-body);
  color: var(--text-primary);
  outline: none;
}

.invite-input-group input::placeholder {
  color: var(--text-tertiary);
}

.btn-invite {
  padding: 10px 20px;
  background: linear-gradient(135deg, var(--accent), #818cf8);
  color: var(--text-inverse);
  border: none;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font-body);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  white-space: nowrap;
}

.btn-invite:hover {
  box-shadow: var(--shadow-glow);
  transform: translateY(-1px);
}

.msg-error {
  color: var(--color-error);
  font-size: 13px;
  margin-top: 10px;
  padding: 8px 12px;
  background: var(--color-error-bg);
  border-radius: var(--radius-sm);
}

.msg-success {
  color: var(--color-success);
  font-size: 13px;
  margin-top: 10px;
  padding: 8px 12px;
  background: var(--color-success-bg);
  border-radius: var(--radius-sm);
}

.map-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.map-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.map-item:hover {
  background: var(--bg-elevated);
  border-color: var(--border-default);
  transform: translateX(4px);
}

.map-icon {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  background: var(--accent-glow);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.map-name {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.chevron {
  color: var(--text-tertiary);
  opacity: 0;
  transition: opacity var(--duration-fast);
}

.map-item:hover .chevron {
  opacity: 1;
}

.empty {
  color: var(--text-tertiary);
  font-size: 13px;
  padding: 24px 0;
  text-align: center;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 80px;
  color: var(--text-tertiary);
  font-size: 14px;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid var(--border-strong);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
