const state = {
  scenarios: [],
  currentScenario: "loss_recall",
  pitchMode: false,
};

const els = {
  scenario: document.getElementById("scenario"),
  scenarioSummary: document.getElementById("scenario-summary"),
  scenarioMeta: document.getElementById("scenario-meta"),
  runButton: document.getElementById("run-button"),
  autoplayButton: document.getElementById("autoplay-button"),
  pitchButton: document.getElementById("pitch-button"),
  refreshButton: document.getElementById("refresh-button"),
  fullscreenButton: document.getElementById("fullscreen-button"),
  keepState: document.getElementById("keep-state"),
  statusPill: document.getElementById("status-pill"),
  headlineEvent: document.getElementById("headline-event"),
  heroSummary: document.getElementById("hero-summary"),
  balances: document.getElementById("balance-cards"),
  pitchScript: document.getElementById("pitch-script"),
  pitchBadge: document.getElementById("pitch-badge"),
  messages: document.getElementById("messages"),
  grants: document.getElementById("grants"),
  traderProfile: document.getElementById("trader-profile"),
  highlights: document.getElementById("highlights"),
  governanceScore: document.getElementById("governance-score"),
  baselineComparison: document.getElementById("baseline-comparison"),
  events: document.getElementById("events"),
  stdout: document.getElementById("stdout"),
  executionStages: document.getElementById("execution-stages"),
  riskGuards: document.getElementById("risk-guards"),
  capitalFlow: document.getElementById("capital-flow"),
  decisionSummary: document.getElementById("decision-summary"),
  spotlightBanner: document.getElementById("spotlight-banner"),
  spotlightBadge: document.getElementById("spotlight-badge"),
  messageCount: document.getElementById("message-count"),
  grantCount: document.getElementById("grant-count"),
  eventCount: document.getElementById("event-count"),
};

let autoplayRunning = false;

function setStatus(text, tone = "idle") {
  els.statusPill.textContent = text;
  els.statusPill.dataset.tone = tone;
}

function currency(value) {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function pct(value) {
  return `${Number(value || 0).toFixed(2)}%`;
}

function renderScenarioMeta(scenario) {
  if (!scenario) return;
  els.scenarioSummary.textContent = scenario.summary;
  els.heroSummary.textContent = state.pitchMode ? pitchHeroCopy(scenario) : scenario.summary;
  const items = [
    ["预算额度", `${scenario.budget.amount} ${scenario.budget.currency}`],
    ["借贷上限", `${scenario.budget.max_borrow_rate_pct}%`],
    ["最低胜率", `${scenario.budget.min_win_rate_pct}%`],
    ["最大亏损", `${scenario.risk.max_loss_threshold_pct}%`],
    ["连损阈值", `${scenario.risk.max_consecutive_losses} 次`],
    ["最大杠杆", `${scenario.risk.max_leverage ?? "-"}x`],
  ];
  els.scenarioMeta.innerHTML = items.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("");
}

function pitchHeroCopy(scenario) {
  if (!scenario) return "运行 Demo 后，这里会用一句话总结当前场景发生了什么。";
  if (scenario.name === "loss_recall") {
    return "这是一条完整的 ATK 闭环：研究给出做多提案，风控设边界，CFO 批预算，风险触发后立即收回资金。";
  }
  return "这是一条正常盈利路径：研究与风控先对齐，CFO 再拨付预算，Trader 在纪律内执行并保留预算。";
}

function renderBalances(balances = {}) {
  const entries = [
    ["总资金", balances.funding_usdt ?? 0, "Funding Account"],
    ["保守池", balances.savings_usdt ?? 0, "Savings / Earn"],
    ["交易池", balances.trading_usdt ?? 0, "Trader Budget"],
  ];
  els.balances.innerHTML = entries
    .map(
      ([label, value, hint]) => `
        <article class="balance-card">
          <p>${label}</p>
          <strong>${currency(value)}</strong>
          <span>${hint}</span>
        </article>
      `
    )
    .join("");
}

function humanizeMessage(message) {
  const payload = message.payload || {};
  if (message.type === "market_brief") {
    return {
      tone: "report",
      title: "Research 输出市场判断",
      summary: `${payload.primary_symbol} 偏 ${payload.direction}，市场状态 ${payload.market_regime}`,
      detail: `${payload.catalyst} 时间框架 ${payload.timeframe}，置信度 ${payload.conviction}.`,
    };
  }
  if (message.type === "sentiment_brief") {
    return {
      tone: "report",
      title: "Research 输出情绪摘要",
      summary: `市场情绪 ${payload.sentiment}，拥挤度 ${payload.crowding}`,
      detail: `${payload.headline} 置信度 ${payload.confidence}.`,
    };
  }
  if (message.type === "risk_brief") {
    return {
      tone: "alert",
      title: "Risk 设置安全围栏",
      summary: `风险等级 ${payload.risk_grade}，最大杠杆 ${payload.max_leverage}x`,
      detail: `${payload.stop_condition} 部署比例 ${payload.deployment_ratio_pct}%.`,
    };
  }
  if (message.type === "trade_plan") {
    return {
      tone: "approve",
      title: "Portfolio 提交交易计划",
      summary: `${payload.primary_symbol} ${payload.direction}，申请预算 ${payload.budget_request} USDT`,
      detail: `${payload.approved_playbook}。`,
    };
  }
  if (message.type === "budget_allocate") {
    return {
      tone: "approve",
      title: "CFO 批准预算",
      summary: `拨付 ${payload.budget_amount} ${payload.currency} 给 Trader，用于 ${payload.purpose || "策略执行"}`,
      detail: `原因：${payload.reason}。预算锁定至 ${payload.lock_until}。`,
    };
  }
  if (message.type === "budget_recall") {
    return {
      tone: "recall",
      title: "CFO 强制回收预算",
      summary: `收回 ${payload.reclaim_amount} ${payload.currency}，当前累计 PnL ${payload.total_pnl}`,
      detail: `原因：${payload.reason}。`,
    };
  }
  if (message.type === "alert") {
    return {
      tone: "alert",
      title: "Trader 发出风险告警",
      summary: `当前收益率 ${payload.pnl_percentage}% ，风险级别 ${payload.risk_level}`,
      detail: payload.message || "接近风险阈值。",
    };
  }
  return {
    tone: "report",
    title: "Trader 回报执行状态",
    summary: `当前累计 PnL ${payload.current_pnl}，收益率 ${payload.pnl_percentage}%`,
    detail: payload.message || "执行正常。",
  };
}

function spotlightFromMessage(message) {
  const card = humanizeMessage(message);
  if (message.type === "budget_allocate") {
    return {
      tone: "approve",
      badge: "APPROVED",
      title: "预算批准已生效",
      summary: card.summary,
    };
  }
  if (message.type === "budget_recall") {
    return {
      tone: "recall",
      badge: "RECALLED",
      title: "风险回收已触发",
      summary: card.summary,
    };
  }
  return {
    tone: "report",
    badge: "LIVE",
    title: card.title,
    summary: card.summary,
  };
}

function renderSpotlight(messages = []) {
  if (!messages.length) {
    els.spotlightBanner.className = "spotlight-banner empty";
    els.spotlightBanner.innerHTML = `
      <div class="spotlight-copy">
        <p class="eyebrow">SPOTLIGHT</p>
        <h3>等待关键动作</h3>
        <p>运行 Demo 后，这里会把最重要的治理动作放大展示。</p>
      </div>
      <div id="spotlight-badge" class="spotlight-badge">IDLE</div>
    `;
    return;
  }
  const important = [...messages].reverse().find((m) => m.type === "budget_recall" || m.type === "budget_allocate") || messages[messages.length - 1];
  const spotlight = spotlightFromMessage(important);
  els.spotlightBanner.className = `spotlight-banner tone-${spotlight.tone}`;
  els.spotlightBanner.innerHTML = `
    <div class="spotlight-copy">
      <p class="eyebrow">SPOTLIGHT</p>
      <h3>${spotlight.title}</h3>
      <p>${spotlight.summary}</p>
    </div>
    <div class="spotlight-badge">${spotlight.badge}</div>
  `;
}

function buildPitchLines(ledger = {}) {
  const summary = ledger.governance_summary || {};
  const grant = (ledger.budget_grants || []).slice(-1)[0];
  const baseline = ledger.baseline_comparison || {};
  const reasons = (summary.revoke_reasons || []).join("、") || "无";
  const budgetText = grant ? `${grant.amount} ${grant.currency}` : "一笔预算";
  const protectedText = currency(summary.protected_capital_usdt ?? 0);
  const committee = summary.committee_view || {};

  return [
    `这是 OKX Agent Trade Kit 的资金治理版，一条链路里有研究、风控、组合、CFO 和 Trader。`,
    `研究组先给出 ${committee.market_regime || "市场"} 判断，风控再把风险等级锁在 ${committee.risk_grade || "待定"}。`,
    `CFO 会结合健康评分和委员会结论，再决定是否给 Trader 拨付 ${budgetText}。`,
    `Trader 只能在这笔预算内执行，并且每一步都要回报盈亏和风险状态。`,
    grant?.status === "REVOKED"
      ? `这一场里，系统因为 ${reasons} 触发回收，直接把资金转回保守池。`
      : `这一场里，Trader 维持在纪律范围内，所以预算继续有效。`,
    baseline.final_trading_usdt
      ? `如果没有 CFO，这笔资金会继续暴露在市场里；而现在系统额外保护了 ${protectedText}。`
      : `系统会同步给出无 CFO 对照，让治理价值更直观。`,
  ];
}

function renderPitchScript(ledger = {}) {
  const lines = buildPitchLines(ledger);
  els.pitchScript.className = "pitch-script";
  els.pitchScript.innerHTML = lines.map((line, index) => `<p><span>0${index + 1}</span>${line}</p>`).join("");
  els.pitchBadge.textContent = state.pitchMode ? "LIVE" : "PITCH";
}

function renderMessages(messages = []) {
  els.messageCount.textContent = String(messages.length);
  if (!messages.length) {
    els.messages.className = "narrative-stream empty";
    els.messages.textContent = "运行场景后，这里会显示 CFO 与 Trader 的协作过程。";
    els.headlineEvent.textContent = "暂无关键动作";
    return;
  }
  els.messages.className = "narrative-stream";
  const latest = humanizeMessage(messages[messages.length - 1]);
  els.headlineEvent.textContent = latest.title;
  renderSpotlight(messages);
  els.messages.innerHTML = messages
    .map((message) => {
      const card = humanizeMessage(message);
      return `
        <div class="narrative-card-item tone-${card.tone}">
          <div class="narrative-top">
            <span class="actor">${message.from}</span>
            <span class="arrow">→</span>
            <span class="actor">${message.to}</span>
            <span class="type-chip">${message.type}</span>
          </div>
          <h4>${card.title}</h4>
          <p>${card.summary}</p>
          <small>${card.detail}</small>
          <details>
            <summary>查看原始消息</summary>
            <pre>${JSON.stringify(message, null, 2)}</pre>
          </details>
        </div>
      `;
    })
    .join("");
}

function renderDecisionSummary(ledger = {}) {
  const lastGrant = (ledger.budget_grants || []).slice(-1)[0];
  if (!lastGrant) {
    els.decisionSummary.className = "decision-summary empty";
    els.decisionSummary.textContent = "运行场景后，这里会总结系统当前的资金治理结论。";
    return;
  }

  const statusMap = {
    APPROVED: "CFO 已批准预算，等待 Trader 启用。",
    ACTIVE: "Trader 正在预算内执行策略，CFO 持续监控风险。",
    REVOKED: "风险触发，CFO 已撤销预算并要求资金回流。",
    SETTLED: "预算已完成结算。",
  };

  els.decisionSummary.className = "decision-summary";
  els.decisionSummary.innerHTML = `
    <strong>${statusMap[lastGrant.status] || "预算状态已更新。"}</strong>
    <p>最近一笔预算编号为 <b>${lastGrant.grant_id}</b>，额度 <b>${lastGrant.amount} ${lastGrant.currency}</b>。</p>
    <p>${lastGrant.reason}</p>
  `;
}

function renderGrants(grants = []) {
  els.grantCount.textContent = String(grants.length);
  if (!grants.length) {
    els.grants.className = "list empty";
    els.grants.textContent = "暂无预算授权";
    return;
  }
  els.grants.className = "list";
  els.grants.innerHTML = grants
    .map(
      (grant) => `
        <div class="list-row">
          <div>
            <strong>${grant.grant_id}</strong>
            <p>${grant.reason}</p>
          </div>
          <div class="align-right">
            <b>${grant.amount} ${grant.currency}</b>
            <span class="badge badge-${grant.status.toLowerCase()}">${grant.status}</span>
          </div>
        </div>
      `
    )
    .join("");
}

function renderStatList(target, items) {
  target.innerHTML = items
    .map(
      ([label, value]) => `
        <div class="stat">
          <span>${label}</span>
          <strong>${value}</strong>
        </div>
      `
    )
    .join("");
}

function renderTraderProfile(profile = {}) {
  renderStatList(els.traderProfile, [
    ["胜率", pct(profile.win_rate_pct)],
    ["最大回撤", pct(profile.max_drawdown_pct)],
    ["连续亏损", `${profile.consecutive_losses ?? 0}`],
  ]);
}

function renderHighlights(ledger = {}) {
  const trades = ledger.trade_results || [];
  const grants = ledger.budget_grants || [];
  const totalPnl = trades.reduce((sum, trade) => sum + Number(trade.pnl || 0), 0);
  const activeGrant = [...grants].reverse().find((item) => item.status === "ACTIVE");
  const revokedGrant = [...grants].reverse().find((item) => item.status === "REVOKED");
  const committee = ledger.governance_summary?.committee_view || {};
  renderStatList(els.highlights, [
    ["累计 PnL", currency(totalPnl)],
    ["委员会方向", committee.direction || "待生成"],
    ["当前激活预算", activeGrant ? activeGrant.grant_id : "无"],
    ["最近回收动作", revokedGrant ? revokedGrant.grant_id : "无"],
  ]);
}

function renderGovernanceScore(summary = {}) {
  const health = summary.approval_health || {};
  const revokeReasons = (summary.revoke_reasons || []).join(", ") || "无";
  const committee = summary.committee_view || {};
  renderStatList(els.governanceScore, [
    ["健康评分", health.health_score ? `${health.health_score}` : "待生成"],
    ["委员会风险级别", committee.risk_grade || "待生成"],
    ["自适应预算", summary.adaptive_budget ? currency(summary.adaptive_budget) : "待生成"],
    ["回收原因", revokeReasons],
  ]);
}

function renderBaselineComparison(baseline = {}, summary = {}) {
  const protectedCapital = summary.protected_capital_usdt ?? 0;
  renderStatList(els.baselineComparison, [
    ["无 CFO 最终仓位", baseline.final_trading_usdt ? currency(baseline.final_trading_usdt) : "待生成"],
    ["无 CFO 回撤", baseline.drawdown_pct !== undefined ? pct(baseline.drawdown_pct) : "待生成"],
    ["CFO 保护资金", currency(protectedCapital)],
  ]);
}

function renderEvents(events = []) {
  els.eventCount.textContent = String(events.length);
  if (!events.length) {
    els.events.className = "timeline empty";
    els.events.textContent = "暂无事件";
    return;
  }
  els.events.className = "timeline";
  els.events.innerHTML = events
    .slice(-10)
    .reverse()
    .map(
      (event) => `
        <div class="timeline-item">
          <div class="dot"></div>
          <div>
            <div class="timeline-head">
              <strong>${event.actor}</strong>
              <span>${event.event}</span>
            </div>
            <p>${event.timestamp}</p>
          </div>
        </div>
      `
    )
    .join("");
}

function renderExecutionStages(ledger = {}) {
  const summary = ledger.governance_summary || {};
  const grant = (ledger.budget_grants || []).slice(-1)[0];
  const trades = ledger.trade_results || [];
  const stages = [
    {
      tone: "done",
      title: "多 Agent 研究委员会对齐",
      detail: summary.committee_view?.market_regime
        ? `${summary.committee_view.market_regime} / ${summary.committee_view.sentiment} / 风险 ${summary.committee_view.risk_grade}。`
        : "Research、Risk、Portfolio 会先形成统一交易提案。",
    },
    {
      tone: "done",
      title: "CFO 读取账户健康度",
      detail: summary.approval_health?.health_score
        ? `健康评分 ${summary.approval_health.health_score}，开始评估拨款条件。`
        : "根据账户快照、借贷条件和 Trader 历史表现做决策。",
    },
    {
      tone: grant ? "done" : "pending",
      title: "预算授权生效",
      detail: grant
        ? `${grant.amount} ${grant.currency} 已授权给 Trader。`
        : "等待生成预算授权。",
    },
    {
      tone: trades.length ? "done" : "pending",
      title: "Trader 预算内执行",
      detail: trades.length
        ? `共执行 ${trades.length} 笔交易，累计 PnL ${currency(trades.reduce((sum, item) => sum + Number(item.pnl || 0), 0))}。`
        : "尚未产生交易结果。",
    },
    {
      tone: grant?.status === "REVOKED" ? "warning" : grant?.status === "ACTIVE" ? "live" : "pending",
      title: "治理决策落地",
      detail: grant?.status === "REVOKED"
        ? `触发回收：${(summary.revoke_reasons || []).join(" / ") || "风险超限"}。`
        : grant?.status === "ACTIVE"
          ? "预算继续有效，CFO 持续监控中。"
          : "等待最终治理结果。",
    },
  ];

  els.executionStages.className = "execution-stages";
  els.executionStages.innerHTML = stages
    .map(
      (stage, index) => `
        <article class="stage-card tone-${stage.tone}">
          <div class="stage-index">0${index + 1}</div>
          <div>
            <h4>${stage.title}</h4>
            <p>${stage.detail}</p>
          </div>
        </article>
      `
    )
    .join("");
}

function renderRiskGuards(ledger = {}) {
  const scenario = state.scenarios.find((item) => item.name === state.currentScenario) || {};
  const summary = ledger.governance_summary || {};
  const guardrails = [
    `委员会风险等级 ${summary.committee_view?.risk_grade ?? "-"}`,
    `预算只在健康评分达标后批准`,
    `最大亏损 ${scenario.risk?.max_loss_threshold_pct ?? "-"}%`,
    `最大连损 ${scenario.risk?.max_consecutive_losses ?? "-"} 次`,
    `最大杠杆 ${scenario.risk?.max_leverage ?? "-"}x`,
  ];

  if (summary.revoke_reasons?.length) {
    guardrails.push(`本场触发：${summary.revoke_reasons.join(" / ")}`);
  }

  els.riskGuards.className = "guard-list";
  els.riskGuards.innerHTML = guardrails
    .map((item) => `<span class="guard-chip">${item}</span>`)
    .join("");
}

function flowCard(label, value, hint, tone = "neutral") {
  return `
    <article class="flow-card tone-${tone}">
      <span>${label}</span>
      <strong>${value}</strong>
      <small>${hint}</small>
    </article>
  `;
}

function renderCapitalFlow(ledger = {}) {
  const balances = ledger.balances || {};
  const baseline = ledger.baseline_comparison || {};
  const summary = ledger.governance_summary || {};
  const protectedCapital = summary.protected_capital_usdt ?? 0;

  els.capitalFlow.className = "capital-flow";
  els.capitalFlow.innerHTML = `
    <div class="flow-row">
      ${flowCard("Funding", currency(balances.funding_usdt ?? 0), "主账户可调度资金", "neutral")}
      <div class="flow-arrow">→</div>
      ${flowCard("Trading", currency(balances.trading_usdt ?? 0), "Trader 当前使用的预算池", "live")}
      <div class="flow-arrow">→</div>
      ${flowCard("Savings", currency(balances.savings_usdt ?? 0), "CFO 回收后的保守池", "safe")}
    </div>
    <div class="flow-summary">
      <div>
        <span>无 CFO 对照</span>
        <strong>${baseline.final_trading_usdt ? currency(baseline.final_trading_usdt) : "待生成"}</strong>
      </div>
      <div>
        <span>CFO 保护资金</span>
        <strong>${currency(protectedCapital)}</strong>
      </div>
    </div>
  `;
}

function renderLedger(ledger) {
  renderBalances(ledger.balances);
  renderPitchScript(ledger);
  renderMessages(ledger.a2a_messages);
  renderDecisionSummary(ledger);
  renderGrants(ledger.budget_grants);
  renderTraderProfile(ledger.trader_profile);
  renderHighlights(ledger);
  renderGovernanceScore(ledger.governance_summary);
  renderBaselineComparison(ledger.baseline_comparison, ledger.governance_summary);
  renderEvents(ledger.event_log);
  renderExecutionStages(ledger);
  renderRiskGuards(ledger);
  renderCapitalFlow(ledger);
}

async function fetchJSON(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || data.stderr || "Request failed");
  }
  return data;
}

async function loadScenarios() {
  const data = await fetchJSON("/api/scenarios");
  state.scenarios = data.scenarios;
  els.scenario.innerHTML = state.scenarios
    .map((scenario) => `<option value="${scenario.name}">${scenario.name}</option>`)
    .join("");
  els.scenario.value = state.currentScenario;
  renderScenarioMeta(state.scenarios.find((item) => item.name === state.currentScenario));
}

async function loadState() {
  const data = await fetchJSON("/api/state");
  renderLedger(data.ledger);
}

async function runScenario() {
  setStatus("运行中", "running");
  els.runButton.disabled = true;
  els.autoplayButton.disabled = true;
  try {
    const data = await fetchJSON("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scenario: state.currentScenario,
        keep_state: els.keepState.checked,
      }),
    });
    renderLedger(data.ledger);
    els.stdout.textContent = data.stdout || "无输出";
    setStatus(`已完成: ${data.scenario}`, "success");
  } catch (error) {
    els.stdout.textContent = String(error);
    setStatus("运行失败", "error");
  } finally {
    els.runButton.disabled = false;
    els.autoplayButton.disabled = autoplayRunning;
  }
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runScenarioByName(name, keepState) {
  const data = await fetchJSON("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      scenario: name,
      keep_state: keepState,
    }),
  });
  renderLedger(data.ledger);
  els.stdout.textContent = data.stdout || "无输出";
  els.scenario.value = name;
  state.currentScenario = name;
  renderScenarioMeta(state.scenarios.find((item) => item.name === state.currentScenario));
  return data;
}

async function autoplayDemo() {
  if (autoplayRunning) return;
  autoplayRunning = true;
  els.autoplayButton.disabled = true;
  els.runButton.disabled = true;
  try {
    setStatus("自动播放中", "running");
    els.stdout.textContent = "自动播放启动：先演示盈利，再演示风险回收。";
    await runScenarioByName("profit_lock", false);
    setStatus("自动播放：盈利场景", "running");
    await wait(1400);
    await runScenarioByName("loss_recall", false);
    setStatus("自动播放完成", "success");
  } catch (error) {
    els.stdout.textContent = `自动播放失败：${String(error)}`;
    setStatus("自动播放失败", "error");
  } finally {
    autoplayRunning = false;
    els.autoplayButton.disabled = false;
    els.runButton.disabled = false;
  }
}

function togglePitchMode() {
  state.pitchMode = !state.pitchMode;
  document.body.classList.toggle("pitch-mode", state.pitchMode);
  els.pitchButton.textContent = state.pitchMode ? "退出路演模式" : "路演模式";
  renderScenarioMeta(state.scenarios.find((item) => item.name === state.currentScenario));
  if (state.pitchMode) {
    setStatus("路演模式", "success");
  }
}

async function toggleFullscreen() {
  const root = document.documentElement;
  if (!document.fullscreenElement) {
    await root.requestFullscreen();
    document.body.classList.add("fullscreen-mode");
    els.fullscreenButton.textContent = "退出全屏";
    return;
  }
  await document.exitFullscreen();
  document.body.classList.remove("fullscreen-mode");
  els.fullscreenButton.textContent = "全屏展示版";
}

els.scenario.addEventListener("change", (event) => {
  state.currentScenario = event.target.value;
  renderScenarioMeta(state.scenarios.find((item) => item.name === state.currentScenario));
});

els.runButton.addEventListener("click", runScenario);
els.autoplayButton.addEventListener("click", autoplayDemo);
els.pitchButton.addEventListener("click", togglePitchMode);
els.refreshButton.addEventListener("click", loadState);
els.fullscreenButton.addEventListener("click", toggleFullscreen);

document.addEventListener("fullscreenchange", () => {
  const active = Boolean(document.fullscreenElement);
  document.body.classList.toggle("fullscreen-mode", active);
  els.fullscreenButton.textContent = active ? "退出全屏" : "全屏展示版";
});

async function boot() {
  setStatus("加载中", "running");
  await loadScenarios();
  await loadState();
  renderSpotlight([]);
  setStatus("准备就绪", "success");
}

boot().catch((error) => {
  els.stdout.textContent = String(error);
  setStatus("加载失败", "error");
});
