import { describe, expect, it } from 'vitest'

import { getAdminNav, getPrimaryNav } from './items'

describe('role-aware navigation', () => {
  it('shows the phase-one user path without unfinished review', () => {
    expect(getPrimaryNav('trader').map(item => [item.title, item.path])).toEqual([
      ['今日', '/today'],
      ['持仓', '/portfolio'],
      ['选股', '/selection'],
      ['市场', '/market'],
    ])
    expect(getAdminNav('trader')).toEqual([])
  })

  it('uses the user path for every non-administrator role', () => {
    expect(getPrimaryNav('user').map(item => item.title)).toEqual(['今日', '持仓', '选股', '市场'])
    expect(getAdminNav('user')).toEqual([])
    expect(getAdminNav('')).toEqual([])
  })

  it('adds administrator operations in a separate group', () => {
    expect(getAdminNav('admin').map(item => [item.title, item.path])).toEqual([
      ['分析任务', '/admin/tasks'],
      ['模型与回测', '/model'],
    ])
  })

  it('stores icons as component references', () => {
    for (const item of [...getPrimaryNav('trader'), ...getAdminNav('admin')]) {
      expect(item.icon).toBeTruthy()
      expect(typeof item.icon).not.toBe('string')
    }
  })
})
