# 真实跑通 Runbook

## 目标

把当前作品从“本地演示原型”推进到“真实 OKX API 跑通”的状态。

## 当前支持的两种模式

### 1. 演示模式

```bash
python3 app.py --mode simulated
```

用途：

- 稳定录制 Demo
- 展示 CFO 拨付预算、Trader 执行、CFO 强制回收
- 验证共享账本和状态机逻辑

### 2. OKX 快照模式

```bash
export OKX_API_KEY=...
export OKX_SECRET_KEY=...
export OKX_PASSPHRASE=...
export OKX_DEMO=1
python3 app.py --mode okx
```

用途：

- 读取真实 OKX 账户余额
- 读取资金账户余额
- 读取当前持仓数量
- 把快照写入 `ledger.json`

## 真实联调建议

### 第一步：只跑读接口

先验证以下接口能正常返回：

- `GET /api/v5/account/balance`
- `GET /api/v5/asset/balances`
- `GET /api/v5/account/positions`

只有读接口稳定以后，再碰写接口。

### 第二步：切模拟盘

建议优先使用 OKX `Demo Trading API`。

官方文档说明：

- 模拟盘请求头需要加 `x-simulated-trading: 1`
- Python SDK 示例中的 `flag = "1"` 也表示模拟盘

当前程序已经默认在 `OKX_DEMO=1` 时附带该请求头。

### 第三步：再接写操作

当前代码里已经预留了这些能力：

- `POST /api/v5/asset/transfer`
- `POST /api/v5/account/set-auto-earn`
- `POST /api/v5/trade/order`

但为了安全，程序现在默认没有自动执行这些动作。

建议按以下顺序逐个联调：

1. 资金划转
2. Auto Earn 开关
3. 小额现货单
4. 再考虑合约

## 比赛前必须跑通的最小闭环

最少需要完成下面这条链路，作品才算真正可交付：

1. 读取账户余额
2. 读取资金账户余额
3. 读取持仓或订单状态
4. 在模拟盘完成至少一次真实下单
5. 风险触发后完成一次真实资金动作或可验证的撤单/停机动作

## 目前仍需你提供的真实条件

要把写接口彻底跑通，后面还需要：

- 你的 OKX Demo API Key
- 账户模式信息
- 你打算先跑现货还是合约
- 允许测试的交易对和金额上限

## 官方参考

- [OKX API 总览](https://www.okx.com/docs-v5/en)
- [Demo Trading 说明](https://app.okx.com/docs-v5/en/)
- [账户余额 `GET /api/v5/account/balance`](https://www.okx.com/docs-v5/en)
- [资金余额 `GET /api/v5/asset/balances`](https://my.okx.com/docs-v5/en/)
- [资金划转 `POST /api/v5/asset/transfer`](https://my.okx.com/docs-v5/en/)
- [下单 `POST /api/v5/trade/order`](https://www.okx.com/docs-v5/en)
