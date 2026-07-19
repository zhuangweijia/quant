import { describe, expect, it } from 'vitest'

import { ApiError, apiErrorFromAxios } from './client'

describe('apiErrorFromAxios', () => {
  it('retains FastAPI field validation detail', () => {
    const detail = [
      {
        loc: ['body', 'params', 'analysis_time'],
        msg: '分析时间必须为 HH:mm',
        type: 'value_error',
      },
    ]
    const error = apiErrorFromAxios({
      message: 'Request failed with status code 422',
      response: { data: { detail } },
    } as never)

    expect(error).toBeInstanceOf(ApiError)
    expect(error.detail).toEqual(detail)
  })

  it('uses FastAPI string detail as the user-facing message', () => {
    const error = apiErrorFromAxios({
      message: 'Request failed with status code 400',
      response: { data: { detail: '当前密码不正确' } },
    } as never)

    expect(error.message).toBe('当前密码不正确')
    expect(error.detail).toBe('当前密码不正确')
  })

  it('uses a structured FastAPI detail message as the user-facing message', () => {
    const detail = {
      code: 'ranked_predictions_missing',
      message: '暂无可用的当日排名，请等待分析完成后再生成建议',
    }
    const error = apiErrorFromAxios({
      message: 'Request failed with status code 409',
      response: { status: 409, data: { detail } },
    } as never)

    expect(error.message).toBe('暂无可用的当日排名，请等待分析完成后再生成建议')
    expect(error.detail).toEqual(detail)
    expect(error.status).toBe(409)
  })

  it('retains the HTTP status without breaking the existing constructor', () => {
    const legacy = new ApiError('旧调用', { code: 'legacy' })
    const conflict = apiErrorFromAxios({
      message: 'Request failed with status code 409',
      response: { status: 409, data: { detail: { code: 'stale_portfolio' } } },
    } as never)

    expect(legacy.status).toBeUndefined()
    expect(conflict.status).toBe(409)
    expect(conflict.detail).toEqual({ code: 'stale_portfolio' })
  })
})
