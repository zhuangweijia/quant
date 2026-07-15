import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useSetupPolling } from './useSetupPolling'

describe('useSetupPolling', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('polls only while setup is initializing and stops when ready', async () => {
    const fetchStatus = vi.fn()
      .mockResolvedValueOnce({ readiness: 'ready' })
    const onStatus = vi.fn()
    const polling = useSetupPolling(fetchStatus, onStatus)

    polling.sync({ readiness: 'uninitialized' })
    await vi.advanceTimersByTimeAsync(3_000)
    expect(fetchStatus).not.toHaveBeenCalled()

    polling.sync({ readiness: 'initializing' })
    await vi.advanceTimersByTimeAsync(3_000)
    expect(fetchStatus).toHaveBeenCalledTimes(1)
    expect(onStatus).toHaveBeenCalledWith({ readiness: 'ready' })

    await vi.advanceTimersByTimeAsync(30_000)
    expect(fetchStatus).toHaveBeenCalledTimes(1)
  })

  it('backs off failed requests and clears timers on stop', async () => {
    const fetchStatus = vi.fn()
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce({ readiness: 'initializing' })
    const polling = useSetupPolling(fetchStatus, vi.fn())

    polling.sync({ readiness: 'initializing' })
    await vi.advanceTimersByTimeAsync(3_000)
    expect(fetchStatus).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(5_999)
    expect(fetchStatus).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(1)
    expect(fetchStatus).toHaveBeenCalledTimes(2)

    polling.stop()
    await vi.advanceTimersByTimeAsync(30_000)
    expect(fetchStatus).toHaveBeenCalledTimes(2)
  })
})
