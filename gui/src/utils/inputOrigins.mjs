// Only explicit, still-selected file objects may carry a direct task origin.
// Plain paths and ordinary picker results never acquire origins by lookup.
export function fileIdentity(path) {
  const value = String(path || '')
  return /^[a-z]:[\\/]|^\\\\|^\/\//i.test(value) ? value.replace(/\\/g, '/').toLowerCase() : value
}

export function getInputOrigins(files = []) {
  if (!Array.isArray(files)) return []
  const origins = []
  const seen = new Set()
  for (const file of files) {
    const origin = file?.origin
    if (!origin || typeof file.path !== 'string' || typeof origin.sourceTaskId !== 'string' || !origin.sourceTaskId || typeof origin.sourceAssetPath !== 'string') continue
    if (fileIdentity(file.path) !== fileIdentity(origin.sourceAssetPath)) continue
    const identity = `${origin.sourceTaskId}\n${fileIdentity(file.path)}`
    if (seen.has(identity)) continue
    seen.add(identity)
    origins.push({ inputPath: file.path, sourceTaskId: origin.sourceTaskId, sourceAssetPath: origin.sourceAssetPath })
    // Keep one overflow entry so the backend can disclose its 200-item bound.
    if (origins.length > 200) break
  }
  return origins
}
