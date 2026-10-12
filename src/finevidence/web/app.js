"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const names = {DEMO_A: "青禾科技", DEMO_B: "澄海制造"};
  const metrics = {revenue: "营业收入", net_profit: "净利润", operating_cashflow: "经营现金流", net_margin: "净利率", revenue_yoy: "收入同比"};
  const intents = {faq: "资料解释", metric: "指标计算", compare: "公司对比", chart: "指标图表", clarify: "待澄清", blocked: "范围提示"};
  const historyKey = "finevidence.history.v1";
  let history = readHistory();
  let busy = false;
  let lastResult = null;
  let chartUrl = null;
  let requestGeneration = 0;
  let toastTimer;

  function node(tag, className, content) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (content !== undefined) element.textContent = content;
    return element;
  }
  function readHistory() {
    try {
      const stored = JSON.parse(localStorage.getItem(historyKey) || "[]");
      return Array.isArray(stored) ? stored.filter((item) => typeof item === "string" && item.length <= 500).slice(0, 8) : [];
    } catch { return []; }
  }
  function saveHistory(question) {
    history = [question, ...history.filter((item) => item !== question)].slice(0, 8);
    try { localStorage.setItem(historyKey, JSON.stringify(history)); } catch { /* Private browsing can disable storage. */ }
    renderHistory();
  }
  function renderHistory() {
    $("history-list").replaceChildren();
    if (!history.length) $("history-list").append(node("p", "aside-empty", "这里会保存最近 8 个研究问题。"));
    for (const question of history) {
      const button = node("button", "history-item");
      button.type = "button";
      button.append(node("span", "", question), node("b", "", "↗"));
      button.disabled = busy;
      button.addEventListener("click", () => research(question));
      $("history-list").append(button);
    }
    $("clear-history").disabled = !history.length || busy;
  }
  function toast(message) {
    clearTimeout(toastTimer);
    $("toast").textContent = message;
    $("toast").hidden = false;
    toastTimer = setTimeout(() => { $("toast").hidden = true; }, 3200);
  }
  function updateCount() { $("char-count").textContent = $("question").value.length; }
  function setBusy(value) {
    busy = value;
    $("submit").disabled = value;
    $("submit").querySelector("span").textContent = value ? "研究中…" : "开始研究";
    $("results").setAttribute("aria-busy", String(value));
    $("loading").hidden = !value;
    $("question").readOnly = value;
    document.querySelectorAll("#examples button").forEach((button) => { button.disabled = value; });
    renderHistory();
  }
  function notice(message, type = "info") {
    $("notice").textContent = message;
    $("notice").className = `notice ${type}`;
    $("notice").hidden = !message;
  }
  async function jsonRequest(path, payload, timeout = 65000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetch(path, {
        method: payload ? "POST" : "GET",
        headers: payload ? {"Content-Type": "application/json"} : {},
        body: payload ? JSON.stringify(payload) : undefined,
        signal: controller.signal
      });
      if (!response.ok) {
        if (response.status === 429) throw new Error("服务正在处理较多请求，请稍后再试。问题已保留。");
        if (response.status === 422) throw new Error("问题格式或图表范围不受支持，请使用一家公司、年度和一个指标重试。");
        throw new Error(`请求未完成（HTTP ${response.status}），请检查服务并重试。`);
      }
      return response;
    } catch (error) {
      if (error.name === "AbortError") throw new Error("请求超时，请稍后重试，或检查模型配置。");
      if (error instanceof TypeError) throw new Error("无法连接本地服务，请确认服务正在运行。问题已保留。");
      throw error;
    } finally { clearTimeout(timer); }
  }
  async function loadCatalog() {
    try {
      const response = await jsonRequest("/v1/catalog", undefined, 10000);
      const catalog = await response.json();
      $("company-count").textContent = catalog.companies.length;
      $("year-span").textContent = `${catalog.years[0]}—${catalog.years.at(-1)}`;
      $("document-count").textContent = catalog.documents.length;
      $("provider-label").textContent = catalog.provider === "llm" ? "模型规划" : "离线规划 · 无需 Key";
      $("service-status").replaceChildren(node("i"), document.createTextNode("本地服务已连接"));
      $("service-status").className = "connection connected";
      $("dataset-version").textContent = `${catalog.dataset_version} · ${catalog.record_count} 条年度记录`;
      $("company-list").replaceChildren();
      for (const company of catalog.companies) {
        names[company.id] = company.name.replace("（虚构）", "");
        const row = node("div", "company-row");
        const detail = node("div");
        detail.append(node("strong", "", company.name), node("small", "", company.id));
        row.append(node("span", "company-avatar", company.name[0]), detail);
        $("company-list").append(row);
      }
      $("document-list").replaceChildren();
      for (const item of catalog.documents) $("document-list").append(node("li", "", item.title));
    } catch (error) {
      $("service-status").className = "connection failed";
      $("service-status").replaceChildren(node("i"), document.createTextNode("服务未连接"));
      $("dataset-version").textContent = "资料库暂不可用，请检查服务。";
      notice(error.message, "error");
    }
  }
  function renderFacts(facts) {
    $("facts").replaceChildren();
    const visible = facts.length <= 3 ? facts : facts.slice(-3);
    for (const fact of visible) {
      const card = node("article", "fact-card");
      const number = Number(fact.value);
      const display = Number.isFinite(number) ? number.toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2}) : fact.value;
      const value = node("p", "fact-value", display);
      value.append(node("small", "", fact.unit));
      card.append(node("p", "fact-label", `${fact.year} · ${metrics[fact.metric] || fact.metric}`), value, node("p", "fact-company", `${names[fact.company] || fact.company} / 虚构样本`));
      $("facts").append(card);
    }
    $("fact-table").replaceChildren();
    for (const fact of facts) {
      const row = node("tr");
      for (const value of [`${names[fact.company] || fact.company} ${fact.year}`, metrics[fact.metric] || fact.metric, `${fact.value} ${fact.unit}`, fact.source]) row.append(node("td", "", value));
      $("fact-table").append(row);
    }
    $("table-wrap").hidden = !facts.length;
  }
  function renderEvidence(result) {
    $("evidence-list").replaceChildren();
    $("evidence-count").textContent = result.evidence.length;
    if (!result.evidence.length) $("evidence-list").append(node("p", "aside-empty", result.facts.length ? "该范围未命中说明材料；指标取数来源列在下方。" : "当前问题没有可引用的资料。试试具体指标或财务概念。"));
    result.evidence.forEach((item, index) => {
      const article = node("article", "evidence-card");
      const detail = node("details");
      const summary = node("summary");
      summary.append(node("span", "evidence-number", `来源 ${String(index + 1).padStart(2, "0")}`), node("h3", "evidence-title", item.title), node("p", "evidence-preview", item.text.length > 75 ? `${item.text.slice(0, 75)}…` : item.text), node("span", "evidence-toggle", "展开原文 ↗"));
      detail.append(summary, node("p", "evidence-full", item.text));
      article.append(detail, node("p", "source-line", `${item.source} · ${item.id}`));
      $("evidence-list").append(article);
    });
    $("fact-sources").replaceChildren();
    const sources = [...new Set(result.facts.flatMap((fact) => fact.source.split(";")))];
    if (sources.length) $("fact-sources").append(node("p", "source-title", "结构化取数来源"));
    sources.forEach((source) => $("fact-sources").append(node("p", "fact-source", source)));
  }
  function renderPlan(result) {
    $("formula-list").replaceChildren();
    const formulas = [...new Set(result.facts.map((fact) => fact.formula))];
    formulas.forEach((formula) => $("formula-list").append(node("p", "formula", formula)));
    $("plan-list").replaceChildren();
    const data = {
      "任务类型": intents[result.plan.intent] || result.plan.intent,
      "公司范围": result.plan.companies.map((company) => names[company] || company).join("、") || "财务概念资料",
      "年度范围": result.plan.years.join("、") || "不限定年度",
      "指标口径": result.facts.length ? metrics[result.plan.metric] : "—",
      "检索问题": result.plan.retrieval_query,
      "规划模式": result.provider === "llm" ? "LLM 结构化规划" : "离线规则规划",
      "补充说明": result.plan.note || "—",
      "样本版本": result.dataset_version
    };
    Object.entries(data).forEach(([key, value]) => $("plan-list").append(node("dt", "", key), node("dd", "", value)));
  }
  function releaseChart() {
    if (chartUrl) URL.revokeObjectURL(chartUrl);
    chartUrl = null;
    $("chart-image").removeAttribute("src");
    $("chart-image").hidden = true;
    $("download-chart").disabled = true;
  }
  async function renderChart(result, question, generation) {
    releaseChart();
    $("chart-panel").hidden = !result.chart;
    if (!result.chart) return;
    $("chart-title").textContent = result.chart.title;
    $("chart-image").alt = `${result.chart.title}，单位${result.chart.unit}。${result.chart.labels.map((label, index) => `${label}：${result.chart.values[index]}`).join("；")}`;
    $("chart-status").hidden = false;
    $("chart-status").textContent = "正在生成可导出的 SVG 图表…";
    try {
      const response = await jsonRequest("/v1/chart.svg", {question});
      if (!(response.headers.get("Content-Type") || "").startsWith("image/svg+xml")) throw new Error("图表响应格式不正确，数值与资料仍可查看。");
      const blob = await response.blob();
      if (generation !== requestGeneration) return;
      chartUrl = URL.createObjectURL(blob);
      $("chart-image").src = chartUrl;
      $("chart-image").hidden = false;
      $("chart-status").hidden = true;
      $("download-chart").disabled = false;
    } catch (error) {
      if (generation === requestGeneration) $("chart-status").textContent = `图表生成失败：${error.message}`;
    }
  }
  async function research(question) {
    if (busy) return;
    question = question.trim();
    if (!question || question.length > 500) { $("question").focus(); toast("请输入 1—500 字的研究问题。"); return; }
    $("question").value = question;
    updateCount();
    const generation = ++requestGeneration;
    lastResult = null;
    notice("");
    setBusy(true);
    $("evidence-count").textContent = "0";
    $("evidence-list").replaceChildren(node("p", "aside-empty", "正在检索当前问题的证据…"));
    $("fact-sources").replaceChildren();
    $("answer-content").hidden = true;
    $("empty-state").hidden = true;
    $("result-meta").className = "result-meta";
    $("result-meta").textContent = "处理中";
    try {
      const response = await jsonRequest("/v1/ask", {question});
      const result = await response.json();
      lastResult = result;
      saveHistory(question);
      renderFacts(result.facts);
      renderEvidence(result);
      renderPlan(result);
      $("steps").replaceChildren();
      const labels = result.status === "answered" ? ["计划已确认", "资料已检索", result.facts.length ? "计算已完成" : "摘录已整理"] : ["范围已检查", "等待补充问题"];
      labels.forEach((label) => { const span = node("span"); span.append(node("i", "", "✓"), document.createTextNode(label)); $("steps").append(span); });
      $("answer-title").textContent = result.plan.intent === "faq" ? "资料摘录" : result.plan.intent === "compare" ? "对比结果" : "结果摘要";
      $("answer-text").textContent = result.answer;
      $("run-id").textContent = `RUN / ${result.run_id.slice(0, 12)}`;
      $("elapsed").textContent = `${result.elapsed_ms} ms · 服务端处理`;
      $("result-meta").textContent = result.status === "answered" ? `${intents[result.plan.intent]} · 已完成` : `${intents[result.plan.intent]} · 需补充`;
      $("result-meta").className = result.status === "answered" ? "result-meta success" : "result-meta";
      $("answer-content").hidden = false;
      if (result.status !== "answered") notice(result.answer, "info");
      await renderChart(result, question, generation);
    } catch (error) {
      lastResult = null;
      releaseChart();
      notice(error.message, "error");
      $("result-meta").textContent = "请求未完成 · 可重试";
      $("evidence-list").replaceChildren(node("p", "aside-empty", "当前查询未完成，没有可展示的证据。请重试。"));
      $("empty-state").hidden = false;
    } finally { setBusy(false); }
  }
  $("ask-form").addEventListener("submit", (event) => { event.preventDefault(); research($("question").value); });
  $("question").addEventListener("input", updateCount);
  $("question").addEventListener("keydown", (event) => { if ((event.ctrlKey || event.metaKey) && event.key === "Enter") { event.preventDefault(); research($("question").value); } });
  document.querySelectorAll("#examples [data-question]").forEach((button) => button.addEventListener("click", () => research(button.dataset.question)));
  $("clear-history").addEventListener("click", () => {
    history = [];
    try { localStorage.removeItem(historyKey); } catch { /* Storage can be unavailable. */ }
    renderHistory();
    toast("查询记录已清空");
  });
  $("copy-answer").addEventListener("click", async () => {
    if (!lastResult) return;
    const result = lastResult;
    const text = [result.answer, ...result.facts.map((fact) => `公式：${fact.formula}\n来源：${fact.source}`), ...result.evidence.map((item) => `[${item.id}] ${item.title}\n${item.text}\n${item.source}`), `样本版本：${result.dataset_version}`, result.disclaimer].join("\n\n");
    try { await navigator.clipboard.writeText(text); toast("结果、公式与引用已复制"); }
    catch { toast("浏览器未允许剪贴板访问，请手动选中结果复制。"); }
  });
  $("download-chart").addEventListener("click", () => {
    if (!chartUrl) return;
    const link = node("a");
    link.href = chartUrl;
    link.download = "finevidence-chart.svg";
    document.body.append(link);
    link.click();
    link.remove();
    toast("图表已导出");
  });
  window.addEventListener("beforeunload", releaseChart);
  updateCount();
  renderHistory();
  loadCatalog();
  research($("question").value);
})();
