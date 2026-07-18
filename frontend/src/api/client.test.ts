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
})
