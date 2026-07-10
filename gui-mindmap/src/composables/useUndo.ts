import { ref, computed } from 'vue'
import type { MindNode } from '../utils/tree'

export interface UndoEntry {
  type: 'create' | 'update' | 'delete'
  nodeId: string
  previousState?: Partial<MindNode>   // for update
  deletedNodes?: MindNode[]           // for delete (full subtree snapshot)
  parentId?: string                   // for create (to know which parent)
}

const MAX_STACK = 100

export function useUndo() {
  const stack = ref<UndoEntry[]>([])

  const canUndo = computed(() => stack.value.length > 0)

  function pushUndo(entry: UndoEntry) {
    stack.value.push(entry)
    if (stack.value.length > MAX_STACK) {
      stack.value.shift()
    }
  }

  function popUndo(): UndoEntry | undefined {
    return stack.value.pop()
  }

  function clear() {
    stack.value = []
  }

  return { stack, canUndo, pushUndo, popUndo, clear }
}
