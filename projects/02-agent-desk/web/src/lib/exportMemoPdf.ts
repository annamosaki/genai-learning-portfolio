/**
 * Beautiful print-ready PDF export for Agent Desk investment memos.
 * Uses jsPDF with a clean editorial layout (navy + teal on warm paper).
 */

import { jsPDF } from 'jspdf'

export type MemoPdfMeta = {
  ticker?: string
  title?: string
  generatedAt?: Date
}

type Block =
  | { kind: 'h1'; text: string }
  | { kind: 'h2'; text: string }
  | { kind: 'h3'; text: string }
  | { kind: 'p'; text: string }
  | { kind: 'li'; text: string; ordered?: boolean; index?: number }
  | { kind: 'quote'; text: string }
  | { kind: 'hr' }
  | { kind: 'spacer' }

const COLORS = {
  paper: [250, 248, 244] as [number, number, number],
  ink: [15, 31, 48] as [number, number, number],
  muted: [90, 105, 122] as [number, number, number],
  accent: [13, 148, 136] as [number, number, number], // teal — print-safe
  rule: [210, 205, 196] as [number, number, number],
  band: [11, 31, 51] as [number, number, number],
  white: [255, 255, 255] as [number, number, number],
}

function stripMd(text: string): string {
  return text
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/^#+\s*/, '')
    .trim()
}

function peekNextNonEmpty(lines: string[], from: number): string | null {
  for (let j = from; j < lines.length; j += 1) {
    if (lines[j].trim()) return lines[j]
  }
  return null
}

function parseBlocks(memo: string): Block[] {
  const lines = memo.replace(/\r\n/g, '\n').split('\n')
  const blocks: Block[] = []
  let i = 0
  let olIndex = 0

  while (i < lines.length) {
    const line = lines[i]

    if (!line.trim()) {
      // Keep ordered-list numbering across blank lines / item body paragraphs
      const next = peekNextNonEmpty(lines, i + 1)
      if (!(next && /^\d+\.\s+/.test(next))) {
        olIndex = 0
      }
      blocks.push({ kind: 'spacer' })
      i += 1
      continue
    }
    if (line.startsWith('---')) {
      blocks.push({ kind: 'hr' })
      i += 1
      olIndex = 0
      continue
    }
    if (line.startsWith('# ')) {
      blocks.push({ kind: 'h1', text: stripMd(line.slice(2)) })
      i += 1
      olIndex = 0
      continue
    }
    if (line.startsWith('## ')) {
      blocks.push({ kind: 'h2', text: stripMd(line.slice(3)) })
      i += 1
      olIndex = 0
      continue
    }
    if (line.startsWith('### ')) {
      blocks.push({ kind: 'h3', text: stripMd(line.slice(4)) })
      i += 1
      olIndex = 0
      continue
    }
    if (line.startsWith('> ')) {
      const parts: string[] = []
      while (i < lines.length && lines[i].startsWith('> ')) {
        parts.push(stripMd(lines[i].slice(2)))
        i += 1
      }
      blocks.push({ kind: 'quote', text: parts.join(' ') })
      olIndex = 0
      continue
    }
    if (/^[-*]\s+/.test(line)) {
      blocks.push({ kind: 'li', text: stripMd(line.replace(/^[-*]\s+/, '')) })
      i += 1
      olIndex = 0
      continue
    }
    if (/^\d+\.\s+/.test(line)) {
      olIndex += 1
      const head = stripMd(line.replace(/^\d+\.\s+/, ''))
      const body: string[] = []
      i += 1
      while (i < lines.length) {
        const nxt = lines[i]
        if (!nxt.trim()) {
          const peek = peekNextNonEmpty(lines, i + 1)
          if (peek && /^\d+\.\s+/.test(peek)) break
          if (
            peek &&
            !peek.startsWith('#') &&
            !peek.startsWith('---') &&
            !peek.startsWith('> ') &&
            !/^[-*]\s+/.test(peek)
          ) {
            i += 1
            continue
          }
          break
        }
        if (
          nxt.startsWith('#') ||
          nxt.startsWith('---') ||
          nxt.startsWith('> ') ||
          /^[-*]\s+/.test(nxt) ||
          /^\d+\.\s+/.test(nxt)
        ) {
          break
        }
        body.push(stripMd(nxt))
        i += 1
      }
      blocks.push({
        kind: 'li',
        ordered: true,
        index: olIndex,
        text: body.length ? `${head} ${body.join(' ')}` : head,
      })
      continue
    }

    const para: string[] = [line]
    i += 1
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].startsWith('#') &&
      !lines[i].startsWith('---') &&
      !lines[i].startsWith('> ') &&
      !/^[-*]\s+/.test(lines[i]) &&
      !/^\d+\.\s+/.test(lines[i])
    ) {
      para.push(lines[i])
      i += 1
    }
    blocks.push({ kind: 'p', text: stripMd(para.join(' ')) })
    // Paragraph between numbered items (continuation) — don't reset if next is numbered
    const next = peekNextNonEmpty(lines, i)
    if (!(next && /^\d+\.\s+/.test(next))) {
      olIndex = 0
    }
  }

  return blocks
}

function inferTitle(memo: string, meta?: MemoPdfMeta): string {
  if (meta?.title) return stripMd(meta.title)
  const m = memo.match(/^#\s+(.+)$/m)
  if (m) return stripMd(m[1])
  if (meta?.ticker) return `Investment Memo — ${meta.ticker.toUpperCase()}`
  return 'Investment Memo'
}

export async function exportMemoToPdf(memo: string, meta: MemoPdfMeta = {}): Promise<void> {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'pt',
    format: 'letter',
  })

  const pageW = doc.internal.pageSize.getWidth()
  const pageH = doc.internal.pageSize.getHeight()
  const marginX = 54
  const marginTop = 72
  const marginBottom = 56
  const contentW = pageW - marginX * 2

  const title = inferTitle(memo, meta)
  const ticker = (meta.ticker || '').toUpperCase()
  const when = meta.generatedAt || new Date()
  const dateStr = when.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  let y = 0
  let page = 1

  const fillPaper = () => {
    doc.setFillColor(...COLORS.paper)
    doc.rect(0, 0, pageW, pageH, 'F')
  }

  const drawHeaderBand = (isCover: boolean) => {
    if (isCover) {
      doc.setFillColor(...COLORS.band)
      doc.rect(0, 0, pageW, 92, 'F')
      doc.setFillColor(...COLORS.accent)
      doc.rect(0, 92, pageW, 3, 'F')

      doc.setTextColor(...COLORS.white)
      doc.setFont('helvetica', 'bold')
      doc.setFontSize(11)
      doc.text('AGENT DESK', marginX, 36)

      doc.setFont('helvetica', 'normal')
      doc.setFontSize(9)
      doc.setTextColor(180, 190, 200)
      doc.text('Multi-agent investment research', marginX, 52)

      if (ticker) {
        doc.setFont('helvetica', 'bold')
        doc.setFontSize(22)
        doc.setTextColor(...COLORS.white)
        doc.text(ticker, pageW - marginX, 44, { align: 'right' })
      }
    } else {
      doc.setDrawColor(...COLORS.rule)
      doc.setLineWidth(0.6)
      doc.line(marginX, 36, pageW - marginX, 36)
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(8)
      doc.setTextColor(...COLORS.muted)
      doc.text('Agent Desk', marginX, 28)
      doc.text(ticker || 'Memo', pageW - marginX, 28, { align: 'right' })
    }
  }

  const drawFooter = () => {
    doc.setDrawColor(...COLORS.rule)
    doc.setLineWidth(0.5)
    doc.line(marginX, pageH - 36, pageW - marginX, pageH - 36)
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(8)
    doc.setTextColor(...COLORS.muted)
    doc.text('Confidential research · Not investment advice', marginX, pageH - 22)
    doc.text(`Page ${page}`, pageW - marginX, pageH - 22, { align: 'right' })
  }

  const newPage = (cover = false) => {
    if (page > 1 || y > 0) {
      drawFooter()
      doc.addPage()
      page += 1
    }
    fillPaper()
    drawHeaderBand(cover && page === 1)
    y = cover && page === 1 ? 128 : marginTop
    if (!(cover && page === 1)) {
      // running header already drawn
    }
  }

  const ensureSpace = (need: number) => {
    if (y + need > pageH - marginBottom) {
      newPage(false)
    }
  }

  // Cover
  fillPaper()
  drawHeaderBand(true)
  y = 128

  doc.setTextColor(...COLORS.ink)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(22)
  const titleLines = doc.splitTextToSize(title, contentW)
  doc.text(titleLines, marginX, y)
  y += titleLines.length * 26 + 10

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(10)
  doc.setTextColor(...COLORS.muted)
  doc.text(`${dateStr}  ·  Generated by Agent Desk`, marginX, y)
  y += 18

  doc.setDrawColor(...COLORS.accent)
  doc.setLineWidth(1.5)
  doc.line(marginX, y, marginX + 64, y)
  y += 28

  // Body
  const blocks = parseBlocks(memo)
  // Skip duplicate H1 if it matches cover title
  let started = false

  for (const block of blocks) {
    if (!started && block.kind === 'h1' && stripMd(block.text) === title) {
      started = true
      continue
    }
    started = true

    if (block.kind === 'spacer') {
      y += 8
      continue
    }

    if (block.kind === 'hr') {
      ensureSpace(16)
      doc.setDrawColor(...COLORS.rule)
      doc.setLineWidth(0.7)
      doc.line(marginX, y, pageW - marginX, y)
      y += 16
      continue
    }

    if (block.kind === 'h2') {
      ensureSpace(36)
      y += 10
      doc.setFont('helvetica', 'bold')
      doc.setFontSize(13)
      doc.setTextColor(...COLORS.ink)
      const lines = doc.splitTextToSize(block.text, contentW)
      doc.text(lines, marginX, y)
      y += lines.length * 16 + 4
      doc.setDrawColor(...COLORS.accent)
      doc.setLineWidth(1)
      doc.line(marginX, y, marginX + 36, y)
      y += 12
      continue
    }

    if (block.kind === 'h3') {
      ensureSpace(28)
      y += 6
      doc.setFont('helvetica', 'bold')
      doc.setFontSize(11)
      doc.setTextColor(...COLORS.accent)
      const lines = doc.splitTextToSize(block.text, contentW)
      doc.text(lines, marginX, y)
      y += lines.length * 14 + 6
      continue
    }

    if (block.kind === 'quote') {
      const lines = doc.splitTextToSize(block.text, contentW - 18)
      const boxH = lines.length * 13 + 16
      ensureSpace(boxH + 8)
      doc.setFillColor(236, 242, 240)
      doc.roundedRect(marginX, y - 10, contentW, boxH, 3, 3, 'F')
      doc.setFillColor(...COLORS.accent)
      doc.rect(marginX, y - 10, 3, boxH, 'F')
      doc.setFont('helvetica', 'italic')
      doc.setFontSize(9.5)
      doc.setTextColor(...COLORS.muted)
      doc.text(lines, marginX + 14, y + 2)
      y += boxH + 6
      continue
    }

    if (block.kind === 'li') {
      const bullet = block.ordered ? `${block.index}.` : '•'
      const indent = 14
      const lines = doc.splitTextToSize(block.text, contentW - indent - 10)
      ensureSpace(lines.length * 13 + 6)
      doc.setFont('helvetica', 'bold')
      doc.setFontSize(9.5)
      doc.setTextColor(...COLORS.accent)
      doc.text(bullet, marginX, y)
      doc.setFont('helvetica', 'normal')
      doc.setTextColor(...COLORS.ink)
      doc.text(lines, marginX + indent + 4, y)
      y += lines.length * 13 + 4
      continue
    }

    // paragraph
    if (block.kind === 'p') {
      const lines = doc.splitTextToSize(block.text, contentW)
      ensureSpace(lines.length * 13 + 8)
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(9.8)
      doc.setTextColor(...COLORS.ink)
      doc.text(lines, marginX, y)
      y += lines.length * 13 + 8
    }
  }

  drawFooter()

  const filename = `${(ticker || 'memo').toLowerCase()}-agent-desk-memo.pdf`
  doc.save(filename)
}
