import type { MindNode } from './tree'

const NODE_H_GAP = 60   // horizontal gap between parent and children
const NODE_V_GAP = 12   // vertical gap between siblings
const NODE_MIN_WIDTH = 100
const NODE_HEIGHT = 40
const NODE_PADDING = 32

export interface LayoutResult {
  nodePositions: Map<string, { x: number; y: number; width: number; height: number }>
  totalWidth: number
  totalHeight: number
}

function measureNode(node: MindNode): { width: number; height: number } {
  const content = node.content || ''
  
  // Heuristic for text width:
  // - Chinese/Japanese/Korean characters are roughly 14px (at 14px font size)
  // - Alphanumeric/symbols are roughly 8px
  let estimatedWidth = 0
  for (let i = 0; i < content.length; i++) {
    const code = content.charCodeAt(i)
    if (code >= 0 && code <= 128) {
      estimatedWidth += 8.5
    } else {
      estimatedWidth += 15
    }
  }

  const width = Math.max(NODE_MIN_WIDTH, estimatedWidth + NODE_PADDING)
  return {
    width,
    height: NODE_HEIGHT,
  }
}

interface LayoutNode {
  node: MindNode
  width: number
  height: number
  subtreeHeight: number
  x: number
  y: number
  children: LayoutNode[]
}

function buildLayoutTree(node: MindNode): LayoutNode {
  const { width, height } = measureNode(node)
  const children: LayoutNode[] = []

  if (!node.collapsed && node.children) {
    for (const child of node.children) {
      children.push(buildLayoutTree(child))
    }
  }

  let subtreeHeight = height
  if (children.length > 0) {
    subtreeHeight = children.reduce((sum, c) => sum + c.subtreeHeight, 0) +
      (children.length - 1) * NODE_V_GAP
    subtreeHeight = Math.max(subtreeHeight, height)
  }

  return { node, width, height, subtreeHeight, x: 0, y: 0, children }
}

function assignPositions(ln: LayoutNode, x: number, y: number) {
  ln.x = x
  ln.y = y + (ln.subtreeHeight - ln.height) / 2

  if (ln.children.length > 0) {
    const childX = x + ln.width + NODE_H_GAP
    let childY = y
    for (const child of ln.children) {
      assignPositions(child, childX, childY)
      childY += child.subtreeHeight + NODE_V_GAP
    }
  }
}

function collectPositions(ln: LayoutNode, result: Map<string, { x: number; y: number; width: number; height: number }>) {
  result.set(ln.node.id, { x: ln.x, y: ln.y, width: ln.width, height: ln.height })
  for (const child of ln.children) {
    collectPositions(child, result)
  }
}

export function computeLayout(root: MindNode): LayoutResult {
  const layoutRoot = buildLayoutTree(root)
  const startX = 60
  const startY = 60
  assignPositions(layoutRoot, startX, startY)

  const positions = new Map<string, { x: number; y: number; width: number; height: number }>()
  collectPositions(layoutRoot, positions)

  let maxX = 0, maxY = 0
  for (const pos of positions.values()) {
    maxX = Math.max(maxX, pos.x + pos.width)
    maxY = Math.max(maxY, pos.y + pos.height)
  }

  return {
    nodePositions: positions,
    totalWidth: maxX + 60,
    totalHeight: maxY + 60,
  }
}
