import { defineStore } from 'pinia'
import { ref } from 'vue'

import { adviceApi } from '@/api/advice'
import { usePortfolioStore } from '@/stores/portfolio'
import type {
  AdviceState,
  AdviceTodayResponse,
  DailyAdviceResponse,
  ExecutionResponse,
  ExecutionUpdateRequest,
} from '@/types/advice'

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  if (
    typeof error === 'object' &&
    error !== null &&
    'message' in error &&
    typeof error.message === 'string'
  ) {
    return error.message
  }
  return String(error)
}

interface AdviceTodayMetadata {
  setup_required: boolean
  error_code: string | null
  error_message: string | null
}

function requireAdvice(
  state: AdviceState,
  advice: DailyAdviceResponse | null,
): DailyAdviceResponse {
  if (advice === null) {
    throw new Error(`Advice state ${state} requires advice data`)
  }
  return advice
}

function adviceTodayForState(
  state: AdviceState,
  advice: DailyAdviceResponse | null,
  metadata: AdviceTodayMetadata,
): AdviceTodayResponse {
  switch (state) {
    case 'not_generated':
      return { state, advice: null, ...metadata }
    case 'generating':
    case 'failed':
      return { state, advice, ...metadata }
    case 'ready':
    case 'partially_handled':
    case 'handled':
    case 'expired':
      return { state, advice: requireAdvice(state, advice), ...metadata }
    default:
      return assertNever(state)
  }
}

function assertNever(value: never): never {
  throw new Error(`Unsupported advice state: ${value}`)
}

export const EXECUTION_REFRESH_WARNING = '执行已记录，但刷新最新状态失败，请重试刷新'

export const useAdviceStore = defineStore('advice', () => {
  const today = ref<AdviceTodayResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  let activeRequests = 0

  async function request<T>(operation: () => Promise<T>): Promise<T> {
    activeRequests += 1
    loading.value = true
    error.value = null
    try {
      return await operation()
    } catch (caught) {
      error.value = errorMessage(caught)
      throw caught
    } finally {
      activeRequests -= 1
      loading.value = activeRequests > 0
    }
  }

  function loadToday() {
    return request(async () => {
      const response = await adviceApi.getToday()
      today.value = response.data
      return response.data
    })
  }

  function generate(force = false) {
    return request(async () => {
      const response = await adviceApi.generate(force)
      today.value = todayFromAdvice(response.data)
      return response.data
    })
  }

  function updateExecution(itemId: string, payload: ExecutionUpdateRequest) {
    return request(async () => {
      const response = await adviceApi.updateExecution(
        itemId,
        payload,
        crypto.randomUUID(),
      )
      applyExecution(response.data)
      const portfolioStore = usePortfolioStore()
      const refreshResults = await Promise.all([
        loadToday().then(
          () => true,
          () => false,
        ),
        portfolioStore.loadPortfolio().then(
          () => true,
          () => false,
        ),
      ])
      if (refreshResults.includes(false)) {
        error.value = EXECUTION_REFRESH_WARNING
      }
      return response.data
    })
  }

  function todayFromAdvice(advice: DailyAdviceResponse): AdviceTodayResponse {
    return adviceTodayForState(advice.status, advice, {
      setup_required: false,
      error_code: advice.error_code,
      error_message: advice.error_message,
    })
  }

  function applyExecution(response: ExecutionResponse) {
    const current = today.value
    if (!current?.advice) return
    const updatedAdvice: DailyAdviceResponse = {
      ...current.advice,
      status: response.advice_state,
      items: current.advice.items.map((item) =>
        item.id === response.item.id ? response.item : item,
      ),
    }
    today.value = adviceTodayForState(response.advice_state, updatedAdvice, {
      setup_required: current.setup_required,
      error_code: current.error_code,
      error_message: current.error_message,
    })
  }

  return {
    today,
    loading,
    error,
    loadToday,
    generate,
    updateExecution,
  }
})
