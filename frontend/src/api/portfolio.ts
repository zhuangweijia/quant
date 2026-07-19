import type { ResponseBase } from '@/types/common'
import type {
  CashMovementRequest,
  HoldingsReconcileRequest,
  InvestmentProfileInput,
  InvestmentProfileResponse,
  PortfolioResponse,
  PortfolioSetupRequest,
  PortfolioSetupStatus,
} from '@/types/portfolio'
import client from './client'

type ApiResult<T> = Promise<ResponseBase<T>>

export const portfolioApi = {
  getSetupStatus: () =>
    client.get<ResponseBase<PortfolioSetupStatus>>(
      '/api/v1/portfolio/setup-status',
    ) as unknown as ApiResult<PortfolioSetupStatus>,
  completeSetup: (data: PortfolioSetupRequest) =>
    client.post<ResponseBase<PortfolioResponse>>(
      '/api/v1/portfolio/setup',
      data,
    ) as unknown as ApiResult<PortfolioResponse>,
  getPortfolio: () =>
    client.get<ResponseBase<PortfolioResponse>>(
      '/api/v1/portfolio',
    ) as unknown as ApiResult<PortfolioResponse>,
  updateProfile: (data: InvestmentProfileInput) =>
    client.put<ResponseBase<InvestmentProfileResponse>>(
      '/api/v1/portfolio/profile',
      data,
    ) as unknown as ApiResult<InvestmentProfileResponse>,
  reconcileHoldings: (data: HoldingsReconcileRequest) =>
    client.put<ResponseBase<PortfolioResponse>>(
      '/api/v1/portfolio/holdings',
      data,
    ) as unknown as ApiResult<PortfolioResponse>,
  recordCashMovement: (data: CashMovementRequest) =>
    client.post<ResponseBase<PortfolioResponse>>(
      '/api/v1/portfolio/cash-movements',
      data,
    ) as unknown as ApiResult<PortfolioResponse>,
}
