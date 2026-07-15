import { describe, expect, it } from 'vitest'

import { getSetupPresentation } from './setup-state'

describe('getSetupPresentation', () => {
  it('offers first-time setup for an empty installation', () => {
    const view = getSetupPresentation({ readiness: 'uninitialized' }, null)

    expect(view.title).toBe('完成首次配置')
    expect(view.action).toBe('start_setup')
    expect(view.emptyMessage).toContain('首次配置')
  })

  it('shows progress without offering another action while initializing', () => {
    const view = getSetupPresentation({ readiness: 'initializing' }, null)

    expect(view.title).toBe('正在准备推荐系统')
    expect(view.action).toBeNull()
  })

  it('offers a retry after setup fails', () => {
    const view = getSetupPresentation({ readiness: 'failed' }, null)

    expect(view.action).toBe('start_setup')
    expect(view.actionLabel).toBe('继续初始化')
  })

  it('offers daily analysis only after setup is ready', () => {
    const view = getSetupPresentation(
      { readiness: 'ready' },
      { status: 'idle' },
    )

    expect(view.action).toBe('run_analysis')
    expect(view.actionLabel).toBe('运行今日分析')
  })

  it('does not claim a completed analysis failed when no strong picks exist', () => {
    const view = getSetupPresentation(
      { readiness: 'ready' },
      { status: 'done' },
    )

    expect(view.emptyMessage).toContain('未产生符合条件的强推股票')
  })
})
