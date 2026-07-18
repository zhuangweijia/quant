import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

type Oklch = [lightness: number, chroma: number, hue: number]

function readToken(block: string, token: string): Oklch {
  const match = block.match(new RegExp(`${token}:\\s*oklch\\(([^)]+)\\)`))
  if (!match) throw new Error(`Missing ${token}`)

  const values = match[1]!.trim().split(/\s+/).map(Number)
  if (values.length !== 3 || values.some(Number.isNaN)) {
    throw new Error(`Invalid ${token}`)
  }

  return values as Oklch
}

function relativeLuminance([lightness, chroma, hue]: Oklch) {
  const radians = (hue * Math.PI) / 180
  const a = chroma * Math.cos(radians)
  const b = chroma * Math.sin(radians)
  const lRoot = lightness + 0.3963377774 * a + 0.2158037573 * b
  const mRoot = lightness - 0.1055613458 * a - 0.0638541728 * b
  const sRoot = lightness - 0.0894841775 * a - 1.291485548 * b
  const l = lRoot ** 3
  const m = mRoot ** 3
  const s = sRoot ** 3
  const clamp = (value: number) => Math.max(0, Math.min(1, value))
  const red = clamp(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s)
  const green = clamp(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s)
  const blue = clamp(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s)

  return 0.2126 * red + 0.7152 * green + 0.0722 * blue
}

function contrastRatio(first: Oklch, second: Oklch) {
  const [lighter, darker] = [relativeLuminance(first), relativeLuminance(second)].sort(
    (a, b) => b - a,
  )
  return (lighter! + 0.05) / (darker! + 0.05)
}

describe('theme tokens', () => {
  it('keeps selected controls readable in the blue dark theme', () => {
    const css = readFileSync(resolve(process.cwd(), 'src/assets/themes.css'), 'utf8')
    const block = css.match(/\.theme-blue\.dark\s*\{([\s\S]*?)\}/)?.[1]
    if (!block) throw new Error('Missing blue dark theme')

    const primary = readToken(block, '--primary')
    const foreground = readToken(block, '--primary-foreground')
    const sidebarPrimary = readToken(block, '--sidebar-primary')
    const sidebarForeground = readToken(block, '--sidebar-primary-foreground')

    expect(contrastRatio(primary, foreground)).toBeGreaterThanOrEqual(4.5)
    expect(contrastRatio(sidebarPrimary, sidebarForeground)).toBeGreaterThanOrEqual(4.5)
  })
})
