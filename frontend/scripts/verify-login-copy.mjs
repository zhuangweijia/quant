import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const loginViewPath = fileURLToPath(new URL('../src/views/login/LoginView.vue', import.meta.url))
const source = readFileSync(loginViewPath, 'utf8')

const requiredCopy = [
  '每日智能选股',
  '每日分析沪深 300，筛出值得关注的股票，并用简单清楚的理由解释每一次推荐。',
  '股票池',
  '沪深 300',
  '更新频率',
  '每个交易日',
  '分析结果',
  '强推 · 观望 · 回避',
  '登录 Quant Desk',
  '查看今日选股',
  '创建 Quant Desk 账户',
  '创建账户，开始查看每日选股分析。',
]

const obsoleteCopy = [
  'Trading workspace',
  '面向多市场量化交易的统一控制台',
  'A股 / US / Crypto',
  '&lt; 150 ms routing',
  'Rules + alerts',
  '登录你的交易工作台',
  '继续访问策略、行情、交易与风控模块。',
  '查看今日选股结果、股票排名与推荐理由。',
]

const exactCopy = [
  "'查看下一交易日组合建议、仓位调整依据与主要风险'",
]

for (const text of requiredCopy) {
  if (!source.includes(text)) throw new Error(`Missing approved login copy: ${text}`)
}

for (const text of exactCopy) {
  const count = source.split(text).length - 1
  if (count !== 1) throw new Error(`Expected exact login copy once, found ${count}: ${text}`)
}

for (const text of obsoleteCopy) {
  if (source.includes(text)) throw new Error(`Obsolete login copy remains: ${text}`)
}

console.log('Login copy verification passed.')
