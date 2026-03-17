# System Design

## Product Name

- 中文：`OKX 财管双子星`
- 英文副标：`CFO-Trader A2A System`

## Goal

构建一个双 Agent 资金治理系统，让用户的闲置资金在 `Savings / Borrow / Trading` 三者之间动态流动，并通过风险阈值自动完成预算拨付与回收。

## Target Users

- 有闲置稳定币但不想长期躺平的用户
- 经常做现货/合约但缺少纪律约束的交易者
- 希望让 AI 辅助资金管理，而不是只生成信号的用户

## Problems

- 钱躺在账户里时效率低
- 手动赎回和手动转账效率低
- 交易冲动会吞噬本金
- 多个策略之间缺乏统一预算控制

## System Roles

### CFO Agent

职责：

- 获取全账户余额
- 监控闲置资金规模
- 评估 `Savings` 收益与借贷成本
- 结合 Trader 历史胜率决定是否拨付预算
- 监控风险阈值并执行预算回收

原则：

- 第一目标是保本
- 只在风险收益比合理时发放预算
- 任何超限行为优先触发冻结和回收

### Trader Agent

职责：

- 接收 CFO 批准的预算
- 在预算内执行现货/合约策略
- 回报交易结果、PnL、风险暴露
- 无权突破预算与风险约束

原则：

- 所有交易必须绑定预算编号
- 预算过期或撤销时立即停止开仓
- 所有结果都必须可回放

## Core Objects

### 预算授权 BudgetGrant

- `grant_id`
- `amount`
- `currency`
- `reason`
- `issued_at`
- `expires_at`
- `status`

状态：

- `PENDING`
- `APPROVED`
- `ACTIVE`
- `REVOKED`
- `SETTLED`

### 风险快照 RiskSnapshot

- `drawdown_pct`
- `consecutive_losses`
- `borrow_rate`
- `trader_win_rate`
- `unrealized_pnl`
- `status`

## Core Flows

### 1. 预算拨付

1. CFO 读取账户余额和收益/借贷参数
2. CFO 判断是否满足拨付条件
3. CFO 写入预算授权
4. Trader 确认并激活预算

### 2. 交易执行

1. Trader 读取有效预算
2. Trader 执行策略
3. Trader 回传交易结果
4. 账本累计已用预算和当前 PnL

### 3. 风险回收

触发条件：

- 连续亏损达到阈值
- 回撤超过阈值
- 借贷利率超过可接受范围
- 预算过期

动作：

- CFO 撤销预算
- Trader 停止新交易
- 资金回转 `Savings`
- 输出风险处置报告

## MVP Scope

第一版仅实现：

- 本地账本
- 双 Agent 决策循环
- 预算拨付与回收
- 基于模拟数据的交易结果
- 可读日志输出

后续版本再接：

- OKX ATK
- 实时行情
- Web 控制台
- 历史学习与预算调优
