## MODIFIED Requirements

### Requirement: Dashboard auto-refreshes on WebSocket events

The dashboard SHALL subscribe to WebSocket events `analysis_progress`, `ranking_ready`, and `data_sync_alert` while the dashboard page is active. When `ranking_ready` is received, the system SHALL invalidate the ranking cache to trigger automatic refresh of the Top 10 stocks panel. When `analysis_progress` is received, the system SHALL update the pipeline status indicator. When `data_sync_alert` is received, the system SHALL display a warning banner.

#### Scenario: Dashboard refreshes when daily ranking is ready
- **WHEN** the daily analysis Pipeline completes and pushes `ranking_ready` event via WebSocket
- **THEN** the dashboard SHALL invalidate the vue-query cache for `todayRankings` and `marketOverview`
- **AND** the Top 10 stocks panel SHALL automatically update with the latest rankings
- **AND** the pipeline status indicator SHALL change from "运行中" to "已完成"

#### Scenario: Dashboard shows pipeline progress
- **WHEN** the dashboard receives an `analysis_progress` event with `stage=feature_engineering` and `status=running`
- **THEN** the dashboard SHALL display a progress indicator showing "正在计算因子特征..."
- **AND** the progress bar SHALL reflect the completed stages out of total stages

#### Scenario: Dashboard shows data sync warning
- **WHEN** the dashboard receives a `data_sync_alert` event with failure rate > 50%
- **THEN** the dashboard SHALL display a warning banner: "数据同步异常，部分股票数据可能不完整"
- **AND** the warning SHALL persist until the next successful sync
