## ADDED Requirements

### Requirement: Scheduled data cleanup job
系统 SHALL 每日 03:00 UTC 自动执行数据清理任务，删除超过保留天数的过期记录。

#### Scenario: Cleanup runs on schedule
- **WHEN** 系统时间到达每日 03:00 UTC
- **THEN** 系统自动执行数据清理任务，按各数据类型的保留天数删除过期记录

### Requirement: Configurable retention days
系统 SHALL 从 `settings` 表读取各数据类型的保留天数配置，支持动态调整。

#### Scenario: Default retention values
- **WHEN** `settings` 表中未配置保留天数
- **THEN** 系统使用默认值：`data_retention_days=90`、`alert_retention_days=30`、`log_retention_days=30`

#### Scenario: Custom retention values
- **WHEN** 管理员在 `settings` 表中配置了自定义保留天数
- **THEN** 系统使用自定义值进行清理

### Requirement: Batch deletion
系统 SHALL 分批删除过期数据，每批不超过 5000 条，避免长事务锁表。

#### Scenario: Large volume cleanup
- **WHEN** 过期记录超过 5000 条
- **THEN** 系统分批删除，每批 5000 条，直到所有过期记录清除

### Requirement: Cleanup scope
系统 SHALL 清理以下数据表中的过期记录：`strategy_logs`、`alerts`、`notification_logs`、`market_data`。

#### Scenario: Strategy logs cleanup
- **WHEN** `strategy_logs` 中存在 `created_at` 早于 `log_retention_days` 天前的记录
- **THEN** 这些记录被删除

#### Scenario: Alerts cleanup
- **WHEN** `alerts` 中存在 `created_at` 早于 `alert_retention_days` 天前的记录
- **THEN** 这些记录被删除

#### Scenario: Market data cleanup
- **WHEN** `market_data` 中存在 `created_at` 早于 `data_retention_days` 天前的记录
- **THEN** 这些记录被删除

#### Scenario: Notification logs cleanup
- **WHEN** `notification_logs` 中存在 `created_at` 早于 `log_retention_days` 天前的记录
- **THEN** 这些记录被删除

### Requirement: Cleanup logging
系统 SHALL 记录每次清理任务的执行情况，包括清理的表名、删除条数、执行耗时。

#### Scenario: Cleanup completion logging
- **WHEN** 一次清理任务完成
- **THEN** 系统以 INFO 级别记录各表的删除条数和总耗时
