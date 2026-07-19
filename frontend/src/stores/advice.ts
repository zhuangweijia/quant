import { defineStore } from 'pinia'
import { ref } from 'vue'

import { adviceApi } from '@/api/advice'
import { usePortfolioStore } from '@/stores/portfolio'
import type {
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
      await Promise.all([loadToday(), portfolioStore.loadPortfolio()])
      return response.data
    })
  }

  function todayFromAdvice(advice: DailyAdviceResponse): AdviceTodayResponse {
    return {
      state: advice.status,
      setup_required: false,
      advice,
      error_code: advice.error_code,
      error_message: advice.error_message,
    } as AdviceTodayResponse
  }

  function applyExecution(response: ExecutionResponse) {
    const current = today.value
    if (!current?.advice) return
    today.value = {
      ...current,
      state: response.advice_state,
      advice: {
        ...current.advice,
        status: response.advice_state,
        items: current.advice.items.map((item) =>
          item.id === response.item.id ? response.item : item,
        ),
      },
    } as AdviceTodayResponse
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
