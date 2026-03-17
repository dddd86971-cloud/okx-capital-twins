# 本地演示优先模式

## 目标

在真实 OKX API 尚未打通之前，把项目稳定运行在“本地可演示、后续可替换真实接口”的模式。

## 当前结构

项目现在分成两层：

- `Local Demo Provider`
  - 默认用于比赛演示
  - 不依赖真实账户
  - 基于 `scenarios.json` 提供市场、资金和 Trader 胜率快照
- `OKX Provider`
  - 用于后续接真实 OKX API
  - 当前仍保留，但不是主路径

实现位置：

- [`providers.py`](/Users/mac/Desktop/2/providers.py)
- [`app.py`](/Users/mac/Desktop/2/app.py)

## 推荐演示方式

### 1. 先看本地快照

```bash
python3 app.py --preview-provider local-demo --scenario loss_recall
```

这一步会展示：

- 演示资金池
- 模拟借贷利率
- 模拟 Savings 利率
- 模拟 Trader 胜率
- 推荐预算额度

### 2. 再跑完整闭环

```bash
python3 app.py --mode simulated --scenario loss_recall
```

### 3. 网页录屏

```bash
python3 web_console.py
```

## 为什么这样更适合比赛

- 不被真实 API 阻塞
- 每次都能稳定复现
- 能专注展示“资金治理逻辑”而不是接口偶发状态
- 未来只要替换 provider，不需要重写页面和 Agent 逻辑

## 后续接回真实 OKX 的最小改动

当 OKX API 可用后，只需要继续扩展 `OKX Provider`：

- 读取真实余额
- 读取真实持仓
- 读取真实订单结果
- 把 Trader 的脚本化 `pnl` 替换成真实订单/持仓数据

页面与 A2A 逻辑可以不动。
