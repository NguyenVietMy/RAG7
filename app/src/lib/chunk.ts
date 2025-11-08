export type ChunkOptions = {
  size?: number
  overlap?: number
}

export function chunkText(text: string, options: ChunkOptions = {}): string[] {
  const size = options.size ?? 1200
  let overlap = options.overlap ?? 200

  if (!text) return []
  if (size <= 0) return [text]
  if (overlap < 0) overlap = 0
  if (overlap >= size) overlap = Math.floor(size / 4)

  const normalized = text
    .replace(/\r\n/g, "\n")
    .replace(/\t/g, " ")
    .replace(/\u00A0/g, " ") // non-breaking space
    .replace(/[ \f\v]+/g, " ") // collapse multi spaces

  const chunks: string[] = []
  let start = 0

  while (start < normalized.length) {
    const end = Math.min(start + size, normalized.length)
    const slice = normalized.slice(start, end)
    chunks.push(slice.trim())
    if (end === normalized.length) break
    start = Math.max(0, end - overlap)
  }

  return chunks.filter(Boolean)
}


