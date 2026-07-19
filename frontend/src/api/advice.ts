import type {
  AdviceTodayResponse,
  DailyAdviceResponse,
  ExecutionResponse,
  ExecutionUpdateRequest,
} from '@/types/advice'
import type { ResponseBase } from '@/types/common'
import client from './client'

type ApiResult<T> = Promise<ResponseBase<T>>

export const adviceApi = {
  getToday: () =>
    client.get<ResponseBase<AdviceTodayResponse>>(
      '/api/v1/advice/today',
    ) as unknown as ApiResult<AdviceTodayResponse>,
  generate: (force = false) =>
    client.post<ResponseBase<DailyAdviceResponse>>(
      '/api/v1/advice/generate',
      undefined,
      { params: { force } },
    ) as unknown as ApiResult<DailyAdviceResponse>,
  updateExecution: (
    itemId: string,
    data: ExecutionUpdateRequest,
    idempotencyKey: string,
  ) =>
    client.put<ResponseBase<ExecutionResponse>>(
      `/api/v1/advice/items/${itemId}/execution`,
      data,
      { headers: { 'Idempotency-Key': idempotencyKey } },
    ) as unknown as ApiResult<ExecutionResponse>,
}
