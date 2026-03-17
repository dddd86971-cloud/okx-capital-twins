# OKX 模拟盘 API

这个服务把 OKX 官方 `Demo Trading` 接口包装成一个本地 API，方便你直接用 `curl`、Postman 或前端页面测试。

## 官方依据

- Demo Trading 基础地址：`https://us.okx.com`
- Demo 请求头必须包含：`x-simulated-trading: 1`
- 官方说明 Demo 环境不支持部分功能，例如 `withdraw`、`deposit`、`purchase/redemption`

参考：

- [OKX Demo Trading Services](https://app.okx.com/docs-v5/en/)
- [Get balance `GET /api/v5/account/balance`](https://app.okx.com/docs-v5/en/)
- [Funds transfer `POST /api/v5/asset/transfer`](https://app.okx.com/docs-v5/en/)
- [Place order `POST /api/v5/trade/order`](https://app.okx.com/docs-v5/en/)

## 环境变量

先配置你的 Demo API Key：

```bash
export OKX_API_KEY=你的_demo_api_key
export OKX_SECRET_KEY=你的_demo_secret
export OKX_PASSPHRASE=你的_demo_passphrase
export OKX_DEMO=1
```

可选：

```bash
export OKX_BASE_URL=https://us.okx.com
```

## 启动服务

```bash
python3 okx_demo_api.py
```

默认地址：

```text
http://127.0.0.1:8787
```

## 可用接口

### 1. 健康检查

```bash
curl http://127.0.0.1:8787/health
```

### 2. 查看当前配置

```bash
curl http://127.0.0.1:8787/api/demo/config
```

### 3. 查询交易账户余额

```bash
curl "http://127.0.0.1:8787/api/demo/account/balance?ccy=USDT"
```

### 4. 查询资金账户余额

```bash
curl "http://127.0.0.1:8787/api/demo/asset/balances?ccy=USDT"
```

### 5. 查询持仓

```bash
curl "http://127.0.0.1:8787/api/demo/account/positions?instType=SWAP"
```

### 6. 模拟盘资金划转

官方示例里，资金账户到交易账户常用：

- `from=6`
- `to=18`

```bash
curl -X POST http://127.0.0.1:8787/api/demo/asset/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "ccy": "USDT",
    "amt": "10",
    "from": "6",
    "to": "18"
  }'
```

### 7. 模拟盘下单

现货市价买单示例：

```bash
curl -X POST http://127.0.0.1:8787/api/demo/trade/order \
  -H "Content-Type: application/json" \
  -d '{
    "instId": "BTC-USDT",
    "tdMode": "cash",
    "side": "buy",
    "ordType": "market",
    "sz": "0.001"
  }'
```

限价单示例：

```bash
curl -X POST http://127.0.0.1:8787/api/demo/trade/order \
  -H "Content-Type: application/json" \
  -d '{
    "instId": "BTC-USDT",
    "tdMode": "cash",
    "side": "buy",
    "ordType": "limit",
    "sz": "0.001",
    "px": "20000"
  }'
```

## 注意

- 这不是 OKX 官方二次封装 SDK，而是本地代理服务
- 请求最终还是直接打到 OKX 官方 Demo Trading 环境
- 如果你用的是模拟盘 Key，就不要把 `OKX_DEMO` 改成 `0`
- `Earn` 相关申购赎回不建议在 Demo 环境里作为核心闭环，因为官方明确说 Demo 不支持部分这类功能
