<template>
  <div class="home-page">
    <div class="page-header">
      <h1>Your Maps</h1>
      <p class="page-desc">Create, organize, and collaborate on mind maps</p>
    </div>

    <div class="section" v-if="personalMaps.length > 0 || teamMaps.length === 0">
      <div class="section-header">
        <h2>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          Personal
        </h2>
        <span class="count">{{ personalMaps.length }}</span>
      </div>
      <div class="map-list">
        <div v-for="m in personalMaps" :key="m.id" class="map-item" @click="openMap(m.id)">
          <div class="map-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="2.5"/><circle cx="5" cy="8" r="1.5" opacity="0.5"/><circle cx="19" cy="8" r="1.5" opacity="0.5"/><circle cx="5" cy="16" r="1.5" opacity="0.5"/><circle cx="19" cy="16" r="1.5" opacity="0.5"/>
              <line x1="10" y1="11" x2="6.5" y2="9" opacity="0.3"/><line x1="14" y1="11" x2="17.5" y2="9" opacity="0.3"/><line x1="10" y1="13" x2="6.5" y2="15" opacity="0.3"/><line x1="14" y1="13" x2="17.5" y2="15" opacity="0.3"/>
            </svg>
          </div>
          <div class="map-info">
            <span class="map-name">{{ m.name }}</span>
            <span v-if="!m.owner_id" class="badge legacy">Legacy</span>
          </div>
          <div class="map-actions">
            <button v-if="!m.owner_id" class="btn-claim" @click.stop="claimMap(m.id)">Claim</button>
            <button class="btn-delete" @click.stop="removeMap(m.id)" title="Delete map">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>
        <div v-if="personalMaps.length === 0" class="empty-state">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3">
            <circle cx="12" cy="12" r="3"/><circle cx="4" cy="6" r="2"/><circle cx="20" cy="6" r="2"/><circle cx="4" cy="18" r="2"/><circle cx="20" cy="18" r="2"/>
          </svg>
          <p>No personal maps yet. Create one below.</p>
        </div>
      </div>
    </div>

    <div v-if="teamMaps.length > 0" class="section">
      <div class="section-header">
        <h2>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          Team Maps
        </h2>
        <span class="count">{{ teamMaps.length }}</span>
      </div>
      <div class="map-list">
        <div v-for="m in teamMaps" :key="m.id" class="map-item" @click="openMap(m.id)">
          <div class="map-icon team-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="2.5"/><circle cx="5" cy="8" r="1.5" opacity="0.5"/><circle cx="19" cy="8" r="1.5" opacity="0.5"/><circle cx="5" cy="16" r="1.5" opacity="0.5"/><circle cx="19" cy="16" r="1.5" opacity="0.5"/>
              <line x1="10" y1="11" x2="6.5" y2="9" opacity="0.3"/><line x1="14" y1="11" x2="17.5" y2="9" opacity="0.3"/><line x1="10" y1="13" x2="6.5" y2="15" opacity="0.3"/><line x1="14" y1="13" x2="17.5" y2="15" opacity="0.3"/>
            </svg>
          </div>
          <div class="map-info">
            <span class="map-name">{{ m.name }}</span>
            <span class="badge team">Team</span>
          </div>
          <button class="btn-delete" @click.stop="removeMap(m.id)" title="Delete map">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          </button>
        </div>
      </div>
    </div>

    <div class="create-section">
      <div class="create-form">
        <div class="create-input-group">
          <svg class="create-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          <input v-model="newMapName" placeholder="Create a new map..." @keyup.enter="createNewMap" />
        </div>
        <select v-model="selectedTeamId">
          <option value="">Personal</option>
          <option v-for="t in teams" :key="t.id" :value="t.id">{{ t.name }}</option>
        </select>
        <button class="btn-create" @click="createNewMap">
          Create
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiJson } from '../services/api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const maps = ref<any[]>([])
const teams = ref<any[]>([])
const newMapName = ref('')
const selectedTeamId = ref('')

const personalMaps = computed(() => maps.value.filter(m => !m.team_id))
const teamMaps = computed(() => maps.value.filter(m => m.team_id))

async function fetchMaps() {
  maps.value = await apiJson('/api/maps')
}

async function fetchTeams() {
  teams.value = await apiJson('/api/teams')
}

async function createNewMap() {
  const name = newMapName.value.trim()
  if (!name) return
  const body: any = { name }
  if (selectedTeamId.value) body.team_id = selectedTeamId.value
  const data = await apiJson('/api/maps', {
    method: 'POST',
    body: JSON.stringify(body),
  })
  newMapName.value = ''
  router.push(`/map/${data.id}`)
}

function openMap(id: string) {
  router.push(`/map/${id}`)
}

async function removeMap(id: string) {
  await apiJson(`/api/maps/${id}`, { method: 'DELETE' })
  await fetchMaps()
}

async function claimMap(id: string) {
  await apiJson(`/api/maps/${id}/claim`, { method: 'POST' })
  await fetchMaps()
}

onMounted(() => {
  fetchMaps()
  fetchTeams()
})
</script>

<style scoped>
.home-page {
  max-width: 900px;
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

.map-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
}

.map-item {
  display: flex;
  flex-direction: column;
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

.map-item:hover {
  border-color: var(--accent);
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.map-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  background: var(--accent-glow);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform var(--duration-normal);
}

.map-item:hover .map-icon {
  transform: scale(1.1);
}

.map-icon.team-icon {
  background: var(--accent-green-glow);
  color: var(--accent-green);
}

.map-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.map-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: -0.01em;
}

.map-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: auto;
}

.badge {
  font-size: 10px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 100px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  display: inline-flex;
}

.badge.legacy {
  background: var(--color-warning-bg);
  color: #92400e;
}

.badge.team {
  background: var(--color-success-bg);
  color: #065f46;
}

.btn-claim {
  padding: 6px 14px;
  background: var(--accent);
  color: #ffffff;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.btn-claim:hover {
  background: var(--accent-hover);
  box-shadow: var(--shadow-glow);
}

.btn-delete {
  position: absolute;
  top: 16px;
  right: 16px;
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

.map-item:hover .btn-delete {
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

.create-form select {
  padding: 0 16px;
  background: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: var(--radius-lg);
  font-size: 14px;
  font-weight: 600;
  font-family: var(--font-body);
  color: var(--text-secondary);
  outline: none;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.create-form select:focus {
  border-color: var(--accent);
  background: #ffffff;
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
