<template>
  <div class="teams-page">
    <div class="page-header">
      <h1>Teams</h1>
      <p class="page-desc">Manage your teams and collaborate with others</p>
    </div>

    <div v-if="invitations.length > 0" class="section">
      <div class="section-header">
        <h2>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
          Pending Invitations
        </h2>
        <span class="count pulse">{{ invitations.length }}</span>
      </div>
      <div class="invite-list">
        <div v-for="inv in invitations" :key="inv.id" class="invite-item">
          <div class="invite-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </div>
          <div class="invite-info">
            <strong>{{ inv.team_name }}</strong>
            <span class="invite-meta">Invited by {{ inv.inviter_name }} as <span class="role-highlight">{{ inv.role }}</span></span>
          </div>
          <div class="invite-actions">
            <button class="btn-accept" @click="accept(inv.id)">Accept</button>
            <button class="btn-decline" @click="decline(inv.id)">Decline</button>
          </div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-header">
        <h2>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          My Teams
        </h2>
        <span class="count">{{ teams.length }}</span>
      </div>
      <div class="team-list">
        <div v-for="t in teams" :key="t.id" class="team-item" @click="router.push(`/teams/${t.id}`)">
          <div class="team-avatar">{{ t.name.slice(0, 2).toUpperCase() }}</div>
          <div class="team-info">
            <span class="team-name">{{ t.name }}</span>
            <span class="badge" :class="t.role">{{ t.role }}</span>
          </div>
          <button v-if="t.role === 'owner'" class="btn-delete" @click.stop="removeTeam(t.id)" title="Delete team">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          </button>
          <svg class="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
        </div>
        <div v-if="teams.length === 0" class="empty-state">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          <p>No teams yet. Create one to start collaborating.</p>
        </div>
      </div>
    </div>

    <div class="create-section">
      <div class="create-form">
        <div class="create-input-group">
          <svg class="create-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          <input v-model="newTeamName" placeholder="Create a new team..." @keyup.enter="createTeam" />
        </div>
        <button class="btn-create" @click="createTeam">
          Create Team
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTeamsStore } from '../stores/teams'
import { storeToRefs } from 'pinia'

const router = useRouter()
const teamsStore = useTeamsStore()
const { teams, invitations } = storeToRefs(teamsStore)
const newTeamName = ref('')

async function createTeam() {
  const name = newTeamName.value.trim()
  if (!name) return
  await teamsStore.createTeam(name)
  newTeamName.value = ''
}

async function removeTeam(id: string) {
  await teamsStore.deleteTeam(id)
}

async function accept(id: string) {
  await teamsStore.acceptInvitation(id)
}

async function decline(id: string) {
  await teamsStore.declineInvitation(id)
}

onMounted(() => {
  teamsStore.fetchTeams()
  teamsStore.fetchInvitations()
})
</script>

<style scoped>
.teams-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 64px 32px;
  animation: pageIn 0.6s var(--ease-out) both;
}

@keyframes pageIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.page-header {
  margin-bottom: 48px;
  text-align: center;
}

.page-header h1 {
  font-family: var(--font-display);
  font-size: 36px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.04em;
  margin-bottom: 12px;
}

.page-desc {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-secondary);
}

.section {
  margin-bottom: 48px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle);
}

.section-header h2 {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.count {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  background: var(--bg-hover);
  padding: 4px 10px;
  border-radius: 100px;
}

.count.pulse {
  background: var(--color-warning-bg);
  color: #92400e;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.05); }
}

.invite-list, .team-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.invite-item {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px;
  background: #fffbeb;
  border: 1.5px solid #fde68a;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.invite-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  background: #fef3c7;
  color: #d97706;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.invite-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.invite-info strong {
  font-size: 18px;
  font-weight: 700;
  color: #92400e;
}

.invite-meta {
  font-size: 14px;
  color: #b45309;
}

.role-highlight {
  background: #fef3c7;
  padding: 2px 6px;
  border-radius: 4px;
  color: #d97706;
  font-weight: 700;
}

.invite-actions {
  display: flex;
  gap: 10px;
  margin-top: 4px;
}

.btn-accept {
  flex: 1;
  padding: 10px;
  background: #059669;
  color: #ffffff;
  border: none;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.btn-accept:hover {
  background: #047857;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(5, 150, 105, 0.2);
}

.btn-decline {
  flex: 1;
  padding: 10px;
  background: #ffffff;
  border: 1.5px solid #d1d5db;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  color: #4b5563;
  transition: all var(--duration-fast);
}

.btn-decline:hover {
  border-color: var(--color-error);
  color: var(--color-error);
}

.team-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out);
  box-shadow: var(--shadow-sm);
  position: relative;
}

.team-item:hover {
  border-color: var(--accent);
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.team-avatar {
  width: 52px;
  height: 52px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, #0f172a, #334155);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 800;
  color: #ffffff;
  flex-shrink: 0;
  transition: transform var(--duration-normal);
}

.team-item:hover .team-avatar {
  transform: scale(1.1) rotate(-5deg);
}

.team-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.team-name {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.badge {
  font-size: 10px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 100px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  display: inline-flex;
  width: fit-content;
}

.badge.owner {
  background: #fef2f2;
  color: #991b1b;
}

.badge.admin {
  background: #eff6ff;
  color: #1e40af;
}

.badge.editor {
  background: #f0fdf4;
  color: #166534;
}

.chevron {
  color: var(--text-tertiary);
  opacity: 0.5;
}

.btn-delete {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: 50%;
  transition: all var(--duration-fast);
  opacity: 0;
}

.team-item:hover .btn-delete {
  opacity: 1;
}

.btn-delete:hover {
  color: var(--color-error);
  background: var(--color-error-bg);
  border-color: var(--color-error);
  transform: rotate(90deg);
}

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 64px 32px;
  color: var(--text-tertiary);
  font-size: 15px;
  background: var(--bg-hover);
  border-radius: var(--radius-lg);
  border: 2px dashed var(--border-default);
}

.create-section {
  margin-top: 24px;
  padding: 40px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
}

.create-form {
  display: flex;
  gap: 16px;
}

.create-input-group {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
  background: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: var(--radius-lg);
  transition: all var(--duration-normal) var(--ease-out);
}

.create-input-group:focus-within {
  border-color: var(--accent);
  background: #ffffff;
  box-shadow: 0 0 0 4px var(--accent-glow);
}

.create-input-group input {
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

.btn-create {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 28px;
  background: #0f172a;
  color: #ffffff;
  border: none;
  border-radius: var(--radius-lg);
  cursor: pointer;
  font-size: 15px;
  font-weight: 700;
  font-family: var(--font-body);
  transition: all var(--duration-normal) var(--ease-out);
}

.btn-create:hover {
  background: #1e293b;
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(15, 23, 42, 0.15);
}
</style>
