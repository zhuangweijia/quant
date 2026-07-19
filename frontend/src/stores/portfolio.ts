import { defineStore } from 'pinia'
import { ref } from 'vue'

import { portfolioApi } from '@/api/portfolio'
import type {
  CashMovementRequest,
  HoldingsReconcileRequest,
  InvestmentProfileInput,
  PortfolioResponse,
  PortfolioSetupRequest,
  PortfolioSetupStatus,
} from '@/types/portfolio'

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

export const usePortfolioStore = defineStore('portfolio', () => {
  const setupStatus = ref<PortfolioSetupStatus | null>(null)
  const portfolio = ref<PortfolioResponse | null>(null)
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

  function loadSetupStatus() {
    return request(async () => {
      const response = await portfolioApi.getSetupStatus()
      setupStatus.value = response.data
      return response.data
    })
  }

  function loadPortfolio() {
    return request(async () => {
      const response = await portfolioApi.getPortfolio()
      portfolio.value = response.data
      return response.data
    })
  }

  function completeSetup(payload: PortfolioSetupRequest) {
    return request(async () => {
      const response = await portfolioApi.completeSetup(payload)
      portfolio.value = response.data
      await Promise.all([loadSetupStatus(), loadPortfolio()])
      return response.data
    })
  }

  function updateProfile(payload: InvestmentProfileInput) {
    return request(async () => {
      const response = await portfolioApi.updateProfile(payload)
      if (portfolio.value) {
        portfolio.value = { ...portfolio.value, profile: response.data }
      }
      return response.data
    })
  }

  function reconcileHoldings(payload: HoldingsReconcileRequest) {
    return request(async () => {
      const response = await portfolioApi.reconcileHoldings(payload)
      portfolio.value = response.data
      return response.data
    })
  }

  function recordCashMovement(payload: CashMovementRequest) {
    return request(async () => {
      const response = await portfolioApi.recordCashMovement(payload)
      portfolio.value = response.data
      return response.data
    })
  }

  return {
    setupStatus,
    portfolio,
    loading,
    error,
    loadSetupStatus,
    completeSetup,
    loadPortfolio,
    updateProfile,
    reconcileHoldings,
    recordCashMovement,
  }
})
