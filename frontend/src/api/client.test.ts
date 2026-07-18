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
})
