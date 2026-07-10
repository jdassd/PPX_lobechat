import { defineStore } from 'pinia'
import { ref, computed, shallowRef } from 'vue'
import type { MindNode } from '../utils/tree'
import { buildTree } from '../utils/tree'
import { computeLayout, type LayoutResult } from '../utils/layout'

export const useMindmapStore = defineStore('mindmap', () => {
  const mapId = ref<string | null>(null)
  const mapName = ref('')
  const nodes = ref<Map<string, MindNode>>(new Map())
  const root = ref<MindNode | null>(null)
  const layout = shallowRef<LayoutResult | null>(null)
  const selectedNodeId = ref<string | null>(null)
  const clientId = ref<string>('')
  const version = ref(0)
  const locks = ref<Map<string, { user_id: string; username: string }>>(new Map())

  const selectedNode = computed(() => {
    if (!selectedNodeId.value) return null
    return nodes.value.get(selectedNodeId.value) ?? null
  })

  function loadMap(mapData: { id: string; name: string; version?: number; nodes: MindNode[] }) {
    mapId.value = mapData.id
    mapName.value = mapData.name
    version.value = mapData.version ?? 0
    const nodeMap = new Map<string, MindNode>()
    for (const n of mapData.nodes) {
      nodeMap.set(n.id, n)
    }
    nodes.value = nodeMap
    rebuildTree()
  }

  function rebuildTree() {
    const flatNodes = Array.from(nodes.value.values())
    root.value = buildTree(flatNodes)
    if (root.value) {
      layout.value = computeLayout(root.value)
    }
  }

  function applyNodeCreate(nodeData: MindNode) {
    nodes.value.set(nodeData.id, nodeData)
    rebuildTree()
  }

  function applyNodeUpdate(nodeData: MindNode) {
    const existing = nodes.value.get(nodeData.id)
    if (existing) {
      Object.assign(existing, nodeData)
    } else {
      nodes.value.set(nodeData.id, nodeData)
    }
    rebuildTree()
  }

  function applyNodeDelete(nodeId: string) {
    // Delete node and all descendants
    const toDelete = [nodeId]
    const findChildren = (parentId: string) => {
      for (const n of nodes.value.values()) {
        if (n.parent_id === parentId) {
          toDelete.push(n.id)
          findChildren(n.id)
        }
      }
    }
    findChildren(nodeId)
    for (const id of toDelete) {
      nodes.value.delete(id)
    }
    if (selectedNodeId.value && toDelete.includes(selectedNodeId.value)) {
      selectedNodeId.value = null
    }
    rebuildTree()
  }

  function selectNode(id: string | null) {
    selectedNodeId.value = id
  }

  function getNextPosition(parentId: string): number {
    let max = -1
    for (const n of nodes.value.values()) {
      if (n.parent_id === parentId && n.position > max) {
        max = n.position
      }
    }
    return max + 1
  }

  function updateLocks(lockList: Array<{ node_id: string; user_id: string; username: string }>) {
    const newLocks = new Map<string, { user_id: string; username: string }>()
    for (const l of lockList) {
      newLocks.set(l.node_id, { user_id: l.user_id, username: l.username })
    }
    locks.value = newLocks
  }

  function isLockedByOther(nodeId: string, currentUserId: string): boolean {
    const lock = locks.value.get(nodeId)
    return lock !== undefined && lock.user_id !== currentUserId
  }

  return {
    mapId,
    mapName,
    nodes,
    root,
    layout,
    selectedNodeId,
    selectedNode,
    clientId,
    version,
    loadMap,
    rebuildTree,
    applyNodeCreate,
    applyNodeUpdate,
    applyNodeDelete,
    selectNode,
    getNextPosition,
    locks,
    updateLocks,
    isLockedByOther,
  }
})
