import { beforeEach, describe, expect, it, vi } from 'vitest'

import client from './client'
import { adviceApi } from './advice'

vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}))

describe('adviceApi', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads and generates advice for the current user', async () => {
    vi.mocked(client.get).mockResolvedValue({ data: {} } as never)
    vi.mocked(client.post).mockResolvedValue({ data: {} } as never)

    await adviceApi.getToday()
    await adviceApi.generate(true)

    expect(client.get).toHaveBeenCalledWith('/api/v1/advice/today')
    expect(client.post).toHaveBeenCalledWith(
      '/api/v1/advice/generate',
      undefined,
      { params: { force: true } },
    )
  })

  it('sends execution money strings, idempotency, and revision', async () => {
    vi.mocked(client.put).mockResolvedValue({ data: {} } as never)
    const payload = {
      disposition: 'skipped' as const,
      quantity: 0,
      price: null,
      fee: '0',
      executed_at: null,
      reason: '',
      expected_revision: 0,
      acknowledge_outside_advice: false,
    }

    await adviceApi.updateExecution('item-1', payload, 'mutation-123')

    expect(client.put).toHaveBeenCalledWith(
      '/api/v1/advice/items/item-1/execution',
      payload,
      { headers: { 'Idempotency-Key': 'mutation-123' } },
    )
  })
})
