import { describe, expect, it } from 'vitest'

import routes from './routes'

function child(path: string) {
  const layout = routes.find(route => route.path === '/')
  const record = layout?.children?.find(route => route.path === path)
  if (!record) throw new Error(`Missing child route ${path}`)
  return record
}

describe('phase one routes', () => {
  it('redirects legacy entry points and exposes every daily-decision route', () => {
    const layout = routes.find(route => route.path === '/')
    expect(layout?.redirect).toBe('/today')
    expect(child('dashboard').redirect).toBe('/today')
    expect(child('ranking').redirect).toBe('/selection')
    expect(child('today').name).toBe('Today')
    expect(child('portfolio/setup').name).toBe('PortfolioSetup')
    expect(child('portfolio').name).toBe('Portfolio')
    expect(child('selection').name).toBe('Selection')
    expect(child('market').name).toBe('Market')
    expect(child('admin/tasks').name).toBe('AnalysisTasks')
    expect(child('model').meta?.adminOnly).toBe(true)
    expect(child('settings').name).toBe('Settings')
    expect(child('stock/:symbol').name).toBe('StockDetail')
  })

  it('reuses RankingView for selection and AnalysisTasksView for admin tasks', async () => {
    const selection = child('selection').component as () => Promise<{ default: { __name?: string } }>
    const tasks = child('admin/tasks').component as () => Promise<{ default: { __name?: string } }>
    expect((await selection()).default.__name).toBe('RankingView')
    expect((await tasks()).default.__name).toBe('AnalysisTasksView')
  })
})
