# Quant Desk Login Copy Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the outdated trading-workspace copy on the Quant Desk login page with the approved daily stock-selection messaging.

**Architecture:** Keep the existing Vue component structure and authentication behavior unchanged. Add a focused Node verification script that checks the required copy and rejects the obsolete trading claims, then make text-only edits in `LoginView.vue`.

**Tech Stack:** Vue 3, TypeScript, Node.js, npm

## Global Constraints

- Preserve the `Quant Desk` brand name.
- Use direct, understandable language without aggressive marketing claims.
- Do not change layout, interaction, authentication logic, or responsive behavior.
- The approved stock pool is 沪深 300 and the approved result labels are 强推 · 观望 · 回避.

---

### Task 1: Verify and Refresh Login Copy

**Files:**
- Create: `frontend/scripts/verify-login-copy.mjs`
- Modify: `frontend/package.json`
- Modify: `frontend/src/views/login/LoginView.vue`
- Test: `frontend/scripts/verify-login-copy.mjs`

**Interfaces:**
- Consumes: the UTF-8 source text of `frontend/src/views/login/LoginView.vue`
- Produces: npm command `npm run test:login-copy`, exiting with code 0 only when all approved strings exist and obsolete strings are absent

- [ ] **Step 1: Write the failing verification script**

```js
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
  '查看今日选股结果、股票排名与推荐理由。',
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
]

for (const text of requiredCopy) {
  if (!source.includes(text)) throw new Error(`Missing approved login copy: ${text}`)
}

for (const text of obsoleteCopy) {
  if (source.includes(text)) throw new Error(`Obsolete login copy remains: ${text}`)
}

console.log('Login copy verification passed.')
```

Add this script to `frontend/package.json`:

```json
"test:login-copy": "node scripts/verify-login-copy.mjs"
```

- [ ] **Step 2: Run the verification to confirm the old page fails**

Run: `npm run test:login-copy` from `frontend/`

Expected: FAIL with `Missing approved login copy: 每日智能选股`.

- [ ] **Step 3: Replace only the approved text in the Vue template**

Apply the exact mapping from `docs/superpowers/specs/2026-07-15-login-copy-refresh-design.md` to `frontend/src/views/login/LoginView.vue`. Keep `Quant Desk`, field labels, placeholders, validation messages, and login/register switching behavior unchanged.

- [ ] **Step 4: Run focused verification and the production build**

Run: `npm run test:login-copy` from `frontend/`

Expected: PASS with `Login copy verification passed.`

Run: `npm run build` from `frontend/`

Expected: PASS with a successful Vite production build.

- [ ] **Step 5: Commit the implementation**

```bash
git add frontend/package.json frontend/scripts/verify-login-copy.mjs frontend/src/views/login/LoginView.vue
git commit -m "style: refresh login page copy"
```
