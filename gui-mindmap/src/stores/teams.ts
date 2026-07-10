import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiJson } from '../services/api'

export interface Team {
  id: string
  name: string
  owner_id: string
  role?: string
  created_at: string
  updated_at: string
}

export interface TeamMember {
  id: string
  username: string
  email: string
  display_name: string
  role: string
  created_at: string
}

export interface Invitation {
  id: string
  team_id: string
  team_name: string
  inviter_name: string
  invitee_email: string
  role: string
  status: string
  created_at: string
}

export const useTeamsStore = defineStore('teams', () => {
  const teams = ref<Team[]>([])
  const invitations = ref<Invitation[]>([])

  async function fetchTeams() {
    teams.value = await apiJson('/api/teams')
  }

  async function createTeam(name: string) {
    const team = await apiJson('/api/teams', {
      method: 'POST',
      body: JSON.stringify({ name }),
    })
    teams.value.unshift(team)
    return team
  }

  async function deleteTeam(id: string) {
    await apiJson(`/api/teams/${id}`, { method: 'DELETE' })
    teams.value = teams.value.filter(t => t.id !== id)
  }

  async function fetchInvitations() {
    invitations.value = await apiJson('/api/invitations')
  }

  async function acceptInvitation(id: string) {
    await apiJson(`/api/invitations/${id}/accept`, { method: 'POST' })
    invitations.value = invitations.value.filter(i => i.id !== id)
    await fetchTeams()
  }

  async function declineInvitation(id: string) {
    await apiJson(`/api/invitations/${id}/decline`, { method: 'POST' })
    invitations.value = invitations.value.filter(i => i.id !== id)
  }

  return {
    teams,
    invitations,
    fetchTeams,
    createTeam,
    deleteTeam,
    fetchInvitations,
    acceptInvitation,
    declineInvitation,
  }
})
