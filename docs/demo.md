# 可测试 Demo

## 目标

这个 Demo 用来展示 `CFO Agent` 和 `Trader Agent` 之间真实存在的 A2A 协作，而不是只有一段口头描述。

## 当前已支持的测试点

- CFO 根据市场参数和 Trader 胜率批准预算
- CFO 向 Trader 发送结构化 `budget_allocate` 消息
- Trader 激活预算并执行脚本化交易
- Trader 每次交易后向 CFO 发送 `status_report` 或 `alert` 消息
- 风险超限时，CFO 发送 `budget_recall` 消息并回收资金
- 所有消息都会写入 [`ledger.json`](/Users/mac/Desktop/2/ledger.json)

## 运行方式

### 风险回收场景

```bash
python3 app.py --mode simulated --scenario loss_recall
```

你会看到：

- CFO 批准预算
- 一条 `budget_allocate` JSON
- Trader 连续回报交易状态
- 接近阈值时触发 `alert`
- CFO 发出 `budget_recall`

### 盈利场景

```bash
python3 app.py --mode simulated --scenario profit_lock
```

你会看到：

- CFO 批准预算
- Trader 连续盈利
- 预算保持 `ACTIVE`
- 不触发强制回收

## A2A 消息格式

### CFO -> Trader

```json
{
  "from": "CFO",
  "to": "Trader",
  "type": "budget_allocate",
  "timestamp": "2026-03-15T00:00:00Z",
  "payload": {
    "grant_id": "abcd1234",
    "budget_amount": 1000.0,
    "currency": "USDT",
    "purpose": "BTC funding carry strategy",
    "max_loss_threshold_pct": 10.0,
    "max_position_ratio_pct": 5.0,
    "lock_until": "2026-03-15T01:00:00Z",
    "reason": "Low borrow cost and strong recent win rate",
    "require_confirmation": false
  }
}
```

### Trader -> CFO

```json
{
  "from": "Trader",
  "to": "CFO",
  "type": "status_report",
  "timestamp": "2026-03-15T00:10:00Z",
  "payload": {
    "grant_id": "abcd1234",
    "budget_used": 80.0,
    "current_pnl": 80.0,
    "pnl_percentage": 8.0,
    "positions": [
      {
        "instId": "BTC-USDT-SWAP",
        "side": "long",
        "size": 0.1,
        "avgPx": 87432.5
      }
    ],
    "risk_level": "low",
    "near_threshold": false,
    "message": "BTC-USDT-SWAP long executed."
  }
}
```

## 适合下一步接入的真实能力

- 用真实 OKX 余额替代默认账本
- 用真实订单结果替代脚本化 `pnl`
- 用真实资金划转动作替代账本模拟
- 把 `A2A` 消息通过文件、MCP 工具或 HTTP 通道发给双实例客户端
