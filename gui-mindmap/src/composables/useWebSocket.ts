import { ref } from 'vue'
import { useMindmapStore } from '../stores/mindmap'
import { getAccessToken } from '../services/api'

export function useWebSocket() {
  const store = useMindmapStore()
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  let currentMapId: string | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectDelay = 1000

  function connect(mapId: string) {
    disconnect()
    currentMapId = mapId
    reconnectDelay = 1000

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const token = getAccessToken() || ''
    const url = `${protocol}//${location.host}/ws/${mapId}?token=${encodeURIComponent(token)}`
    const socket = new WebSocket(url)
    ws.value = socket

    socket.onopen = () => {
      connected.value = true
      reconnectDelay = 1000
    }

    socket.onclose = () => {
      connected.value = false
      // Auto-reconnect if we haven't explicitly disconnected
      if (currentMapId === mapId) {
        scheduleReconnect(mapId)
      }
    }

    socket.onerror = () => {
      // onclose will fire after onerror, reconnect handled there
    }

    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      handleMessage(msg)
    }
  }

  function scheduleReconnect(mapId: string) {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = setTimeout(() => {
      if (currentMapId === mapId) {
        connect(mapId)
      }
    }, reconnectDelay)
    reconnectDelay = Math.min(reconnectDelay * 2, 10000)
  }

  function handleMessage(msg: any) {
    switch (msg.type) {
      case 'connected':
        store.clientId = msg.client_id
        store.version = msg.version
        break
      case 'ack':
        store.version = msg.version
        if (msg.original_type === 'node:create' && msg.data) {
          store.applyNodeCreate(msg.data)
        }
        break
      case 'node:create':
        if (msg.client_id !== store.clientId && msg.data) {
          store.applyNodeCreate(msg.data)
          store.version = msg.version
        }
        break
      case 'node:update':
        if (msg.client_id !== store.clientId && msg.data) {
          store.applyNodeUpdate(msg.data)
          store.version = msg.version
        }
        break
      case 'node:delete':
        if (msg.client_id !== store.clientId && msg.data) {
          store.applyNodeDelete(msg.data.id)
          store.version = msg.version
        }
        break
      case 'node:move':
        if (msg.client_id !== store.clientId && msg.data) {
          store.applyNodeUpdate(msg.data)
          store.version = msg.version
        }
        break
      case 'peer:disconnect':
        break
    }
  }

  function send(type: string, data: any) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type, data, version: store.version }))
    }
  }

  function createNode(parentId: string, content: string, id: string) {
    const position = store.getNextPosition(parentId)
    send('node:create', { id, parent_id: parentId, content, position })
  }

  function updateNode(nodeId: string, changes: Record<string, any>) {
    send('node:update', { id: nodeId, changes })
  }

  function deleteNode(nodeId: string) {
    send('node:delete', { id: nodeId })
  }

  function moveNode(nodeId: string, newParentId: string, position: number) {
    send('node:move', { id: nodeId, parent_id: newParentId, position })
  }

  function disconnect() {
    currentMapId = null
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws.value) {
      ws.value.onclose = null  // prevent reconnect on intentional close
      ws.value.close()
      ws.value = null
    }
    connected.value = false
  }

  return {
    connected,
    connect,
    disconnect,
    createNode,
    updateNode,
    deleteNode,
    moveNode,
  }
}
