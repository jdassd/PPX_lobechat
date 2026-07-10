export interface MindNode {
  id: string
  map_id: string
  parent_id: string | null
  content: string
  position: number
  style: string
  collapsed: boolean
  last_edited_by?: string
  last_edited_by_name?: string
  last_edited_at?: string
  // Layout computed fields
  x?: number
  y?: number
  width?: number
  height?: number
  children?: MindNode[]
}

/** Build tree from flat node list. Returns root node. */
export function buildTree(nodes: MindNode[]): MindNode | null {
  const map = new Map<string, MindNode>()
  let root: MindNode | null = null

  for (const node of nodes) {
    map.set(node.id, { ...node, children: [] })
  }

  for (const node of map.values()) {
    if (node.parent_id === null) {
      root = node
    } else {
      const parent = map.get(node.parent_id)
      if (parent) {
        parent.children!.push(node)
      }
    }
  }

  // Sort children by position
  for (const node of map.values()) {
    node.children!.sort((a, b) => a.position - b.position)
  }

  return root
}

/** Flatten tree back to node list. */
export function flattenTree(root: MindNode): MindNode[] {
  const result: MindNode[] = []
  const queue = [root]
  while (queue.length > 0) {
    const node = queue.shift()!
    result.push(node)
    if (node.children) {
      queue.push(...node.children)
    }
  }
  return result
}

/** Find a node by id in the flat map. */
export function findNode(nodes: Map<string, MindNode>, id: string): MindNode | undefined {
  return nodes.get(id)
}

/** Get all descendant ids of a node. */
export function getDescendantIds(nodesMap: Map<string, MindNode>, nodeId: string): string[] {
  const ids: string[] = []
  const node = nodesMap.get(nodeId)
  if (!node?.children) return ids
  for (const child of node.children) {
    ids.push(child.id)
    ids.push(...getDescendantIds(nodesMap, child.id))
  }
  return ids
}
