## ADDED Requirements

### Requirement: Dashboard auto-refreshes on WebSocket events

The dashboard SHALL subscribe to WebSocket events `order_update`, `trade_fill`, and `risk_alert` while the dashboard page is active. When any of these events are received, the system SHALL invalidate the corresponding vue-query cache entries to trigger automatic data refresh.

#### Scenario: Order fill event received
- **WHEN** the user is on the dashboard page and a `trade_fill` WebSocket event is received
- **THEN** the system invalidates the `['dashboard', 'overview']`, `['trade', 'positions']`, and `['trade', 'orders']` query caches
- **AND** the dashboard cards, position chart, and recent orders table refresh automatically

#### Scenario: Risk alert event received
- **WHEN** the user is on the dashboard page and a `risk_alert` WebSocket event is received
- **THEN** the system invalidates the `['risk', 'alerts']` and `['dashboard', 'overview']` query caches
- **AND** the unread alert count and strategy status card refresh automatically

#### Scenario: WebSocket disconnects
- **WHEN** the WebSocket connection drops while the user is on the dashboard page
- **THEN** the dashboard continues to function with HTTP polling (vue-query staleTime-based refetch)
- **AND** the system attempts to reconnect using exponential backoff (1s → 2s → 4s → max 30s)
- **AND** when the WebSocket reconnects, it immediately invalidates all dashboard query caches to recover missed events
- **AND** event-based refresh resumes

#### Scenario: WebSocket reconnect with expired token
- **WHEN** the WebSocket reconnection attempt fails due to an expired authentication token
- **THEN** the system refreshes the access token first
- **AND** retries the WebSocket connection with the new token

#### Scenario: User navigates away from dashboard
- **WHEN** the user navigates away from the dashboard page
- **THEN** the WebSocket event listeners for dashboard refresh are cleaned up
