export const GEO_PALETTE = [
  '#BDB6FF', // Lavender
  '#54DCFC', // Sky blue
  '#83FFEA', // Aqua mint
  '#FFB7AB', // Soft coral
  '#FFEC8D', // Pale yellow
  '#735CC6', // Deep lavender
  '#465EFF', // Royal blue
  '#00EBD0', // Teal
  '#F97A70', // Warm coral
  '#FCFC30', // Bright yellow
] as const

const BANK_COLOR_OVERRIDES: Record<string, string> = {
  'Banco do Brasil': '#465EFF',
  'bb.com.br': '#465EFF',
  'Banco do B': '#465EFF',
  'Santander': '#F97A70',
  'santander.com.br': '#F97A70',
  'Banco Santander': '#F97A70',
  'Itaú': '#FFB7AB',
  'Itau': '#FFB7AB',
  'itau.com.br': '#FFB7AB',
  'Banco Itaú': '#FFB7AB',
  'Bradesco': '#BDB6FF',
  'banco.bradesco': '#BDB6FF',
  'bradesco.com.br': '#BDB6FF',
  'Nubank': '#735CC6',
  'Nu': '#735CC6',
  'nubank.com.br': '#735CC6',
  'Inter': '#00EBD0',
  'Banco Inter': '#00EBD0',
  'inter.com.br': '#00EBD0',
  'C6': '#465EFF',
  'C6 Bank': '#465EFF',
  'c6bank.com.br': '#465EFF',
  'Caixa': '#54DCFC',
  'caixa.gov.br': '#54DCFC',
  'Caixa Econômica': '#54DCFC',
  'Neon': '#83FFEA',
  'neon.com.br': '#83FFEA',
  'Will': '#FFEC8D',
  'Will Bank': '#FFEC8D',
  'Picpay': '#F97A70',
  'picpay.com': '#F97A70',
  Outros: '#BDB6FF',
}

export function getGeoColorByName(name: string | null | undefined, index: number): string {
  if (name) {
    const normalized = name.trim()
    if (normalized in BANK_COLOR_OVERRIDES) {
      return BANK_COLOR_OVERRIDES[normalized]
    }

    const lower = normalized.toLowerCase()
    const match = Object.entries(BANK_COLOR_OVERRIDES).find(([key]) => lower.includes(key.toLowerCase()))
    if (match) {
      return match[1]
    }
  }

  return GEO_PALETTE[index % GEO_PALETTE.length]
}

export function getGeoColorByIndex(index: number): string {
  return GEO_PALETTE[index % GEO_PALETTE.length]
}

export function geoColorWithAlpha(hex: string, alpha: number): string {
  const sanitized = hex.startsWith('#') ? hex.slice(1) : hex
  const normalized = sanitized.length === 3
    ? sanitized.split('').map((char) => char + char).join('')
    : sanitized

  const bigint = parseInt(normalized, 16)
  const r = (bigint >> 16) & 255
  const g = (bigint >> 8) & 255
  const b = bigint & 255

  const clampedAlpha = Math.max(0, Math.min(alpha, 1))
  return `rgba(${r}, ${g}, ${b}, ${clampedAlpha})`
}
