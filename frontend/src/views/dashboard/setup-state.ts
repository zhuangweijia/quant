import type { SetupReadiness } from '@/api/setup'

export type SetupAction = 'start_setup' | 'run_analysis' | null

interface SetupLike {
  readiness: SetupReadiness
}

interface AnalysisLike {
  status: string
}

export interface SetupPresentation {
  title: string
  description: string
  action: SetupAction
  actionLabel: string | null
  emptyMessage: string
}

export function getSetupPresentation(
  setup: SetupLike,
  analysis: AnalysisLike | null,
): SetupPresentation {
  if (setup.readiness === 'uninitialized') {
    return {
      title: '完成首次配置',
      description: '自动同步市场数据、训练模型，并生成第一批股票推荐。',
      action: 'start_setup',
      actionLabel: '一键初始化并生成推荐',
      emptyMessage: '完成首次配置后，这里会展示模型生成的股票推荐。',
    }
  }

  if (setup.readiness === 'initializing') {
    return {
      title: '正在准备推荐系统',
      description: '正在同步数据并训练模型，离开页面也不会中断。',
      action: null,
      actionLabel: null,
      emptyMessage: '首次配置正在进行，完成后将自动生成股票推荐。',
    }
  }

  if (setup.readiness === 'failed') {
    return {
      title: '初始化未完成',
      description: '可以从已完成的步骤继续，无需重新下载全部数据。',
      action: 'start_setup',
      actionLabel: '继续初始化',
      emptyMessage: '首次配置尚未完成，请处理提示后继续初始化。',
    }
  }

  if (analysis?.status === 'running') {
    return {
      title: '今日分析运行中',
      description: '模型正在计算因子、预测并生成推荐排名。',
      action: null,
      actionLabel: null,
      emptyMessage: '今日分析正在运行，推荐结果生成后会自动刷新。',
    }
  }

  if (analysis?.status === 'done') {
    return {
      title: '推荐系统已就绪',
      description: '市场数据和模型均可用。',
      action: null,
      actionLabel: null,
      emptyMessage: '模型今日未产生符合条件的强推股票。',
    }
  }

  return {
    title: '推荐系统已就绪',
    description: '市场数据和模型均可用，可以生成今天的推荐。',
    action: 'run_analysis',
    actionLabel: '运行今日分析',
    emptyMessage: '今日尚未运行分析，运行后将在这里展示股票推荐。',
  }
}
