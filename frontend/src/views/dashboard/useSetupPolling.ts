import { getCurrentScope, onScopeDispose } from 'vue'

import type { SetupReadiness } from '@/api/setup'

interface ReadinessLike {
  readiness: SetupReadiness
}

const INITIAL_DELAY = 3_000
const MAX_DELAY = 30_000

export function useSetupPolling<T extends ReadinessLike>(
  fetchStatus: () => Promise<T>,
  onStatus: (status: T) => void,
) {
  let timer: ReturnType<typeof setTimeout> | null = null
  let active = false
  let delay = INITIAL_DELAY

  function clearTimer() {
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
  }

  function schedule() {
    clearTimer()
    if (!active) return
    timer = setTimeout(poll, delay)
  }

  async function poll() {
    timer = null
    if (!active) return

    try {
      const status = await fetchStatus()
      onStatus(status)
      delay = INITIAL_DELAY
      active = status.readiness === 'initializing'
    } catch {
      delay = Math.min(delay * 2, MAX_DELAY)
    }

    schedule()
  }

  function sync(status: ReadinessLike) {
    const shouldPoll = status.readiness === 'initializing'
    if (!shouldPoll) {
      active = false
      delay = INITIAL_DELAY
      clearTimer()
      return
    }

    if (active && timer !== null) return
    active = true
    delay = INITIAL_DELAY
    schedule()
  }

  function stop() {
    active = false
    clearTimer()
  }

  if (getCurrentScope()) onScopeDispose(stop)

  return { sync, stop }
}
