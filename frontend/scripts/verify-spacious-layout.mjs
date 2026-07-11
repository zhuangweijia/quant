import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = resolve(__dirname, '..')

const checks = [
  {
    file: 'src/components/layout/AppLayout.vue',
    expected: ['h-16', 'sm:w-64', 'max-w-7xl px-5 py-7'],
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
    expected: ['flex flex-col gap-5 sm:flex-row', 'min-w-32', '<span>训练新模型</span>'],
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
}

if (failures.length > 0) {
  console.error('Spacious layout verification failed:')
  for (const failure of failures) {
    console.error(`- ${failure}`)
  }
  process.exit(1)
}

console.log('Spacious layout verification passed.')
