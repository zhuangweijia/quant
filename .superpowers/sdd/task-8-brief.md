### Task 8: Add Typed Frontend APIs and Stores

**Files:**
- Create: `frontend/src/types/portfolio.ts`
- Create: `frontend/src/types/advice.ts`
- Create: `frontend/src/api/portfolio.ts`
- Create: `frontend/src/api/portfolio.test.ts`
- Create: `frontend/src/api/advice.ts`
- Create: `frontend/src/api/advice.test.ts`
- Create: `frontend/src/stores/portfolio.ts`
- Create: `frontend/src/stores/portfolio.test.ts`
- Create: `frontend/src/stores/advice.ts`
- Create: `frontend/src/stores/advice.test.ts`

**Interfaces:**
- Produces `portfolioApi`, `adviceApi`, `usePortfolioStore`, and `useAdviceStore` matching Tasks 2–7 exactly.
- `usePortfolioStore`: `setupStatus`, `portfolio`, `loading`, `error`, `loadSetupStatus`, `completeSetup`, `loadPortfolio`, `updateProfile`, `reconcileHoldings`, `recordCashMovement`.
- `useAdviceStore`: `today`, `loading`, `error`, `loadToday`, `generate`, `updateExecution`.

- [ ] **Step 1: Write failing API and store tests**

```ts
// frontend/src/api/advice.test.ts
import { describe, expect, it, vi } from 'vitest'
import client from './client'
import { adviceApi } from './advice'

vi.mock('./client', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }))

it('sends execution idempotency and revision', async () => {
  vi.mocked(client.put).mockResolvedValue({ data: {} } as never)
  await adviceApi.updateExecution('item-1', { disposition: 'skipped', quantity: 0, fee: 0, reason: '', expected_revision: 0, acknowledge_outside_advice: false }, 'mutation-123')
  expect(client.put).toHaveBeenCalledWith(
    '/api/v1/advice/items/item-1/execution', expect.any(Object),
    { headers: { 'Idempotency-Key': 'mutation-123' } },
  )
})
```

Store tests mock clients and assert errors do not erase the last successful state, setup success refreshes both status and portfolio, and execution success replaces the matching advice item and refreshes portfolio.

- [ ] **Step 2: Run and verify missing modules**

Run: `npm --prefix frontend test -- --run src/api/portfolio.test.ts src/api/advice.test.ts src/stores/portfolio.test.ts src/stores/advice.test.ts`

Expected: FAIL for missing modules.

- [ ] **Step 3: Implement exact DTOs and APIs**

Use ISO datetime strings, decimal strings for monetary values, and numbers for bounded ratios/weights/scores. Model the discriminated states and action values as string unions. Follow `settingsApi`'s `ApiResult<T>` cast because the Axios interceptor returns the unwrapped `ResponseBase`.

- [ ] **Step 4: Implement the stores**

Keep request errors as `error: string`; do not translate failed requests to empty data. Generate idempotency keys with `crypto.randomUUID()` in the store, not the component. After successful execution, call `Promise.all([loadToday(), portfolioStore.loadPortfolio()])`.

- [ ] **Step 5: Run tests and commit**

Run: `npm --prefix frontend test -- --run src/api/portfolio.test.ts src/api/advice.test.ts src/stores/portfolio.test.ts src/stores/advice.test.ts`

Expected: PASS.

```bash
git add frontend/src/types/portfolio.ts frontend/src/types/advice.ts frontend/src/api/portfolio.ts frontend/src/api/portfolio.test.ts frontend/src/api/advice.ts frontend/src/api/advice.test.ts frontend/src/stores/portfolio.ts frontend/src/stores/portfolio.test.ts frontend/src/stores/advice.ts frontend/src/stores/advice.test.ts
git commit -m "feat: add portfolio advice frontend state"
```
