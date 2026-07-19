import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = resolve(__dirname, '..')

const checks = [
  {
    file: 'src/components/layout/AppLayout.vue',
    expected: ['h-16', '<UiSidebarTrigger class="size-9" />', 'max-w-7xl px-5 py-7'],
    expectedCounts: { '<CommandMenu': 1 },
    forbidden: [
      'openCommandMenu',
      '<Search',
      '搜索...',
      '⌘K',
      'toggleTheme',
      '<SunMedium',
      '<MoonStar',
    ],
  },
  {
    file: 'src/components/app-sidebar/index.vue',
    expected: ['group-data-[collapsible=icon]:hidden', 'px-2 py-3', 'gap-3'],
  },
  {
    file: 'src/components/ui/button/Button.vue',
    expected: ['inline-flex items-center justify-center gap-2'],
  },
  {
    file: 'src/components/ui/sidebar/utils.ts',
    expected: ['SIDEBAR_WIDTH_ICON = "4rem"'],
  },
  {
    file: 'src/components/ui/sidebar/index.ts',
    expected: ['group-data-[collapsible=icon]:size-10!', 'default: "h-10 text-sm"'],
  },
  {
    file: 'src/views/model/ModelView.vue',
    expected: ['flex flex-col gap-5 md:flex-row', 'min-w-32', '<span>训练新模型</span>'],
    forbidden: ['flex flex-col gap-5 sm:flex-row'],
  },
  {
    file: 'src/views/dashboard/DashboardView.vue',
    expected: ['<SetupStatusCard', '{{ emptyMessage }}', '@run-analysis="handleRunAnalysis"'],
    forbidden: ['暂无推荐数据，请先运行分析 Pipeline'],
  },
  {
    file: 'src/views/dashboard/SetupStatusCard.vue',
    expected: ['data-testid="setup-primary-action"', '<Progress :model-value="progress" />'],
  },
  {
    file: 'src/views/dashboard/setup-state.ts',
    expected: ['一键初始化并生成推荐', '运行今日分析', '未产生符合条件的强推股票'],
  },
]

const failures = []

for (const check of checks) {
  const contents = readFileSync(resolve(root, check.file), 'utf8')

  for (const expected of check.expected) {
    if (!contents.includes(expected)) {
      failures.push(`${check.file} is missing: ${expected}`)
    }
  }

  for (const forbidden of check.forbidden ?? []) {
    if (contents.includes(forbidden)) {
      failures.push(`${check.file} still contains: ${forbidden}`)
    }
  }

  for (const [expected, count] of Object.entries(check.expectedCounts ?? {})) {
    const actual = contents.split(expected).length - 1
    if (actual !== count) {
      failures.push(`${check.file} contains ${actual} occurrences of ${expected}; expected ${count}`)
    }
  }
}

if (failures.length > 0) {
  console.error('Spacious layout verification failed:')
  for (const failure of failures) {
    console.error(`- ${failure}`)
  }
  process.exit(1)
}

console.log('Spacious layout verification passed.')
