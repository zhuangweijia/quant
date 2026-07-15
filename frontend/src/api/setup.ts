import client from './client'
import type { ResponseBase } from '@/types/common'

export type SetupReadiness = 'uninitialized' | 'initializing' | 'failed' | 'ready'

export interface SetupStage {
  status: 'pending' | 'running' | 'done' | 'failed'
  started_at?: string
  finished_at?: string
  error?: string
  current?: number
  total?: number
  succeeded?: number
  failed?: number
  symbol?: string
}

export interface SetupRun {
  run_id: string
  status: 'running' | 'completed' | 'failed' | 'interrupted'
  current_stage: string | null
  stages: Record<string, SetupStage>
  started_at: string
  finished_at: string | null
  error: string | null
}

export interface SetupStatus {
  readiness: SetupReadiness
  counts: {
    stocks: number
    daily_bars: number
    models: number
    today_predictions: number
  }
  active_model: string | null
  run: SetupRun | null
  can_start: boolean
  can_run_analysis: boolean
}

export const setupApi = {
  getStatus: () =>
    client.get<ResponseBase<SetupStatus>>('/api/v1/setup/status'),

  start: () =>
    client.post<ResponseBase<{ run_id: string; status: string }>>('/api/v1/setup/start'),
}
