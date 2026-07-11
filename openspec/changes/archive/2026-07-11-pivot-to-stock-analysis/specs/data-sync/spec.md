## ADDED Requirements

### Requirement: A股日K线数据增量同步

系统 SHALL 提供增量同步能力，每日收盘后自动拉取沪深300成分股的最新日K线数据（OHLCV）并存储到 `daily_bars` 表。增量同步 SHALL 只拉取上次同步以来的缺失交易日数据，不重复拉取已有数据。

#### Scenario: 首次全量拉取沪深300历史日K线
- **WHEN** 系统首次部署，`daily_bars` 表为空，用户触发全量同步
- **THEN** 系统 SHALL 拉取沪深300全部成分股最近 8 年的日K线数据（前复权），逐只存入 `daily_bars` 表
- **AND** 每只股票拉取完成后 SHALL 记录同步进度，支持中断后断点续传
- **AND** 已成功拉取的股票在重试时 SHALL 被跳过

#### Scenario: 每日增量同步最新交易日数据
- **WHEN** 交易日收盘后（默认 16:30 CST），定时任务触发增量同步
- **THEN** 系统 SHALL 对沪深300每只成分股，拉取自上次同步日期以来的缺失日K线数据
- **AND** 新数据 SHALL 追加到 `daily_bars` 表，不覆盖已有记录
- **AND** 同步完成后 SHALL 更新该股票的 `last_synced_date`

#### Scenario: AKShare 调用失败时断点续传
- **WHEN** 增量同步过程中某只股票的 AKShare 调用失败（网络错误 / 限频 / 接口异常）
- **THEN** 系统 SHALL 记录失败股票和错误原因，继续处理其余股票
- **AND** 下次同步时 SHALL 优先重试之前失败的股票
- **AND** 失败率超过 50% 时 SHALL 通过 WebSocket 推送告警

### Requirement: 沪深300成分股列表同步

系统 SHALL 定期（每月第一个交易日）同步沪深300成分股列表，更新 `stocks` 表中的成分股标记和行业分类。

#### Scenario: 月度成分股列表更新
- **WHEN** 每月第一个交易日定时任务触发
- **THEN** 系统 SHALL 从 AKShare 获取最新沪深300成分股列表
- **AND** 新进入成分股 SHALL 被标记为 `in_csi300=true` 并触发历史数据拉取
- **AND** 退出成分股 SHALL 被标记为 `in_csi300=false`，历史数据 SHALL 保留不删除

### Requirement: 基本面数据同步

系统 SHALL 每周同步沪深300成分股的核心基本面指标（PE TTM、PB、ROE、营收增速、资产负债率、股息率），存储到 `stock_factors` 表或独立基本面快照表。

#### Scenario: 周度基本面数据更新
- **WHEN** 每周日晚定时任务触发基本面同步
- **THEN** 系统 SHALL 获取沪深300成分股的最新基本面指标
- **AND** 数据 SHALL 存储为带时间戳的快照记录
- **AND** 无法获取某项指标的股票 SHALL 对该字段填 NULL，不阻断整体同步

### Requirement: 北向资金持仓数据同步

系统 SHALL 每日同步沪深300成分股的北向资金（沪股通+深股通）持股比例和持仓变化数据。

#### Scenario: 每日北向资金数据同步
- **WHEN** 交易日收盘后增量同步执行时
- **THEN** 系统 SHALL 获取每只成分股的北向资金持股数量和比例
- **AND** 计算 `northbound_holding_change`（相对前一日的变化比例）作为资金流因子

### Requirement: 数据完整性校验

系统 SHALL 在每次同步完成后对数据进行完整性校验，确保关键数据无缺失。

#### Scenario: 日K线数据缺失交易日检测
- **WHEN** 增量同步完成后执行数据校验
- **THEN** 系统 SHALL 检测每只股票在同步范围内是否有交易日数据缺失（排除节假日）
- **AND** 缺失交易日超过 3 个连续交易日的股票 SHALL 被标记为 `data_quality=warning`
- **AND** 校验结果 SHALL 通过 WebSocket 推送给前端
