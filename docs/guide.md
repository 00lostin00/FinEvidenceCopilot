# FinEvidence技术指南

运行、数据契约、模块设计与验证说明。

## 1. 第一次运行：从输入到结果

### 1.1 环境和目录

本地验证使用 Windows、Python 3.12.7、uv。Python要求为3.11及以上。依赖版本以 `uv.lock` 为准，当前版本实际安装包括 FastAPI 0.143.0、Pydantic 2.14.1、langchain-openai 1.7.0、langchain-core 1.6.9、pytest 9.1.1。不要把教程页面的示例版本当成该工作区锁定版本。

```text
FinEvidenceCopilot/
  pyproject.toml                 项目依赖与命令行入口
  uv.lock                        当前版本解析并锁定的依赖
  start.ps1                      启动本地API
  fixtures/
    financials.json              两家公司、三个年度的6条记录
    documents.json               7份教学材料，按空行分成片段
  src/finevidence/
    models.py                    输入、计划、事实、证据、图表和响应模型
    planning.py                  规则意图与参数解析
    llm.py                       可选LangChain结构化规划器
    retrieval.py                 字符/二元组切分与BM25
    finance.py                   指标计算与图表规格生成
    service.py                   请求总流程
    tracing.py                   同一run_id下的事件记录
    charts.py                    受约束的SVG渲染
    api.py                       FastAPI入口
    cli.py                       命令行演示
  tests/                         单元、接口、范围与适配器测试
  evals/cases.jsonl               24条固定回归样本
  tools/evaluate.py              回归、逐例报告和本地耗时
  docs/                          本手册和验证产物
  data/                          本地运行时轨迹与演示图表
```

执行以下命令。`--all-extras` 会把 dev 与 llm 的可选依赖一起保留；`--frozen` 要求沿用锁文件，不自动更新解析结果。

```powershell
cd FinEvidenceCopilot
uv sync --frozen --all-extras
uv run --frozen --all-extras finevidence "青禾科技2025年营业收入同比"
```

检查输出中的 `status` 为 `answered`，`provider` 为 `offline`，`facts[0].value` 为字符串 `25.00`，单位为 `%`。来源同时包含2025和2024年度记录，公式为 `(本年营业收入 - 上年营业收入) / 上年营业收入 * 100`。

### 1.2 六个最小演示

| 输入 | 预期关键结果 | 学习目标 |
| --- | --- | --- |
| 青禾科技2025年营业收入 | 15000.00万元 | 结构化事实查询 |
| 青禾科技2025年净利率 | 10.00% | 派生指标与单位 |
| 比较青禾科技和澄海制造2025年净利率 | 10.00%、4.00% | 跨公司同口径比较 |
| 青禾科技2023至2025年收入画图 | 三个点：10000、12000、15000 | 年度范围展开与图表规格 |
| 青禾科技2026年收入 | no_evidence，没有数字事实 | 缺失不能替换成0或最新已知值 |
| 青禾科技最新股价 | clarify | 固定样本不能充当实时数据 |

再执行：

```powershell
uv run --frozen --all-extras finevidence "利润为什么和现金流不同"
uv run --frozen --all-extras finevidence "青禾科技2023至2025年收入画图" --svg data\revenue.svg
uv run --frozen --all-extras finevidence "青禾科技2025年扣非净利润"
```

第一个命令返回教学资料原文及片段ID；第二个命令导出 SVG；第三个应要求澄清，因为扣非净利润不等于样本中的净利润。所有金额都来自虚构数据，演示时应保留这个标记。

### 1.3 启动API

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

访问 `http://127.0.0.1:8012/docs`，选择 `POST /v1/ask`，提交：

```json
{"question":"青禾科技2025年净利率"}
```

接口要求问题长度1至500个字符，未知字段会拒绝。例如附加 `"sql":"DROP TABLE"` 会得到422，本系统不会执行这段字符串。请求合法但没有证据时，HTTP仍返回200，业务状态为 `no_evidence`；业务状态和协议错误分开，方便客户端展示。

`POST /v1/chart.svg` 使用同一请求结构，问题需含“图”或“可视化”并指定支持的指标。结果是 `image/svg+xml`。概念问答或无图表意图返回422。`GET /health` 返回离线/模型模式和数据版本。

### 1.4 第一轮验证

```powershell
uv run --frozen --all-extras pytest
uv run --frozen --all-extras ruff check .
uv run --frozen --all-extras python tools\evaluate.py
```

2026-10-12当前提交的结果为56项测试通过、24/24条固定回归通过、Ruff通过。将测试总数与回归样本数分开：56项检查覆盖计算、模式、接口、图表及异常；24条回归覆盖业务输入。二者不能相加成“80道模型问答准确率”。


## 2. 数据契约与财务口径

### 2.1 原始数据的确定范围

`financials.json` 包含 `version`、`unit`、`companies`、`rows`。公司使用 `DEMO_A` 和 `DEMO_B`，避免看起来像真实证券代码。金额均为字符串，单位均为万元，数据仅有年度，没有季度、半年或滚动十二个月口径。

| 公司 | 年度 | 营业收入 | 净利润 | 经营现金流 |
| --- | ---: | ---: | ---: | ---: |
| 青禾科技DEMO_A | 2023 | 10000 | 800 | 1100 |
| 青禾科技DEMO_A | 2024 | 12000 | 1080 | 1350 |
| 青禾科技DEMO_A | 2025 | 15000 | 1500 | 1750 |
| 澄海制造DEMO_B | 2023 | 18000 | 1080 | 900 |
| 澄海制造DEMO_B | 2024 | 20000 | 1000 | 1200 |
| 澄海制造DEMO_B | 2025 | 21000 | 840 | 1050 |

资料文件包含4份概念材料和3份公司年度简报。其中公司简报有两段，概念资料也有一份两段，因此目前7份资料生成11个片段。结构化表有2023年记录，文档简报没有2023年全文；数字问题仍可用表记录回答，附加文档证据可以为空。数字来源 `fixture:DEMO_A:2023` 与文本来源 `fixture:DEMO_A:2025:note` 的用途不同。

### 2.2 五个指标

| metric字段 | 展示名称 | 数据/公式 | 单位 |
| --- | --- | --- | --- |
| revenue | 营业收入 | 原始年度字段 | 万元 |
| net_profit | 净利润 | 原始年度字段 | 万元 |
| operating_cashflow | 经营活动现金流量净额 | 原始年度字段 | 万元 |
| net_margin | 净利率 | 净利润/营业收入×100 | % |
| revenue_yoy | 营业收入同比 | (本年收入-上年收入)/上年收入×100 | % |

这些是教学项目的固定口径，不构成真实公司财务分析。真实项目需要确认归母/合并、扣非/非扣非、币种、重述版本、累计/单季、会计准则和报告发布日期。不要将“利润”自动视作“净利润”，也不要将“投资现金流”替换成“经营现金流”。当前规则明确拒绝已识别的这些口径混淆。

### 2.3 为什么使用Decimal

从JSON字符串构造 `Decimal("15000")`，避免先变成二进制浮点数再转换。最终 `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` 将显示结果保留两位；例如样本净利率为10.00。Decimal支持显式精度和舍入规则，适合本项目的可复算金额展示。[Python Decimal文档](https://docs.python.org/3.12/library/decimal.html)

Decimal也不会自动解决所有问题。除法仍受上下文精度影响；货币数据若非常大或中间步骤多，需要设定并测试精度。先以未舍入的中间值计算，最后在输出层舍入，避免多次截断。图形布局将绝对值比例转换成float，只影响像素长度，不参与事实金额计算。

### 2.4 手算并核对

青禾2025年营业收入同比：`(15000-12000)/12000*100 = 25`，结果25.00%。青禾2025净利率：`1500/15000*100 = 10`，结果10.00%。澄海2025净利率：`840/21000*100 = 4`，结果4.00%。两家公司净利率相差6个百分点；相对增幅是 `(10-4)/4 = 150%`。本版只输出各公司指标，不自动解释“差6%”或“增长150%”，以免混淆百分比和百分点。

### 2.5 缺失、零、负数

缺失年度：返回没有该年度数据，不用前一年顶替。同比缺失上年：返回不能计算，不把上年设为0。上年收入为0或负数：本项目不输出简化同比，要求说明异常口径。营业收入非正：不计算简化净利率。净利润为负但收入为正：允许得到负净利率，图表向左绘制负值。

选择拒绝非正基数是本项目的产品规则，不是说所有统计问题都只能这样处理。真实研究可以提供绝对变化、从亏损到盈利的标签或定义其他度量，但必须写清口径并让客户端知道该值不可直接按一般增长率解释。

### 2.6 接入真实数据时要补的字段

建议记录 `company_id`、`security_code`、`exchange`、`report_period`、`period_type`、`currency`、`unit_scale`、`consolidation_scope`、`metric_code`、`value`、`published_at`、`effective_at`、`revision`、`source_url`、`document_hash`、`page_or_table`。报告期是经济活动所属区间，发布日期是当时用户何时能看到资料，二者必须区分。若做历史评测，用当时可见版本，避免把后续重述或未来披露内容泄漏到过去。

当前JSON加载器面向受控fixtures，不是任意上传文件导入器。未来导入时应增加文件大小、格式、重复键、非有限数值、单位范围和来源许可校验；不要把现有loader直接开放给公网用户上传。


## 3. 沿一次请求阅读源码

### 3.1 主路径

```text
AskRequest(question)
  -> API并发容量检查
  -> Copilot.ask生成run_id
  -> 确定性检查：建议边界、实时/未知/歧义
  -> OfflinePlanner或LangChainPlanner
  -> QueryPlan与显式输入一致性检查
  -> FAQ检索 / 指标计算 / 图表规格
  -> 来源与事件写入JSONL
  -> AskResponse
```

先读 `models.py`，理解各对象，再读 `service.py` 的 `ask()`。阅读时不要一开始就追完整个框架源码；先跟踪“青禾科技2025年净利率”的七个状态。回答被生成前，谁决定公司、谁提供金额、谁计算百分比、谁保存来源，各自都有一个明确入口。

### 3.2 逐对象理解

`AskRequest` 只接受question。`QueryPlan` 只含意图、公司、年份、指标、检索查询和说明。`Fact` 是已经计算的数字事实，value为字符串，并保存source和formula。`Evidence` 是检索到的原文片段，保存公司和年度范围、来源、BM25分数。`ChartSpec` 是展示计划，labels、values、source_refs需要对齐。`AskResponse` 同时保存计划、事实、证据、图表和业务状态。

| 对象 | 谁创建 | 谁消费 | 不应承担的职责 |
| --- | --- | --- | --- |
| QueryPlan | 规则或模型规划器 | service、finance、retrieval | 不能凭空补金额 |
| Fact | FinancialStore | answer、ChartSpec、API | 不能把来源未知数字写成事实 |
| Evidence | BM25Index | FAQ摘录、响应 | 不能成为系统指令 |
| ChartSpec | FinancialStore.chart | SVG渲染器 | 不能执行JS/Python或SQL |
| Trace事件 | service | 开发者、评测脚本 | 不能当作用户授权或财务资料 |

### 3.3 一次数字查询的步骤

输入被识别为metric、DEMO_A、2025、net_margin。存储以 `(company, year)` 查字典，读取净利润1500和收入15000。计算10.00，保存年度来源和公式。附加文本检索只检索同公司同年度简报。最终回答由程序模板拼接，因此不会让模型把1500误写为15000或把万元变成亿元。

这条路径当前是工程上的证据拼装，不是自主多Agent研究系统。它仍然体现了NLU参数化、模型输出约束、工具职责分工和服务契约，而这些能力都与岗位有关。

### 3.4 一次概念问答的步骤

“利润为什么和现金流不同”没有公司，被分类为faq。服务先检查问题中是否出现支持的金融术语，避免泛泛的词重合让无关问题误答。索引只搜索company为空的概念资料，返回最多3段。程序拼接 `[片段ID] 原文`，原文的“不确定”和边界也会一起保留。

FAQ回答目前可能包含多条相关度不同的摘录，未训练重排器，也不做语义蕴含核验。改进时先看排序和查询集合，再增加模型总结，而不是先把所有片段变成一段流畅文字。

### 3.5 两种失败路径

如果数据加载失败、文件损坏或轨迹路径无法写入，当前可能是服务异常，不会被包装成财务资料缺失。上线前要补错误分类、日志告警和HTTP映射；学习原型中保留可见异常比静默吞错更便于排查。

### 3.6 阅读练习

画出一个 `AskResponse`，给每个字段标注来源。手动删除澄海2025记录，执行双公司比较，检查是否残留青禾的部分结果。模拟规划器返回DEMO_B而原问题是DEMO_A，解释一致性校验为什么拒绝。查看trace中同一个run_id，核对事件顺序，并解释为什么系统开始事件只保存长度，但plan.completed仍保留retrieval_query，日志并未自动脱敏。


## 4. NLU、Prompt和结构化输出

### 4.1 NLU在这里做什么

用户说“青禾23到25年的收入画个图”，系统需要识别实体、时间、指标和输出形式。当前规则只匹配四位20xx年度，不能理解“23年”的短写；“2023至2025”则可以展开为2023、2024、2025。规则的能力边界应该有测试，不能只展示支持的句式。

支持的意图为faq、metric、compare、chart、clarify、blocked。compare要求两个公司；数字查询要求公司和年份；单次最多4个年度；多指标或已识别的未支持财务口径要求澄清。默认年度2025会写入note并显示给用户，不将它称为“最新”。

### 4.2 规则基线的价值和局限

优点是成本低、可重现、便于建立预期结果。局限是别名、否定、语境、长问题和指代可能处理不好。例如“不要画图，只告诉我收入”包含“图”，现有规则可能路由到chart；“总利润”需要澄清；“上年”没有当前年的上下文会缺失。将这些句式加进扩展测试集合，可以清楚看到需要语义模型的地方。

模型模式也保留确定性限制和与显式输入的一致性校验。这能避免模型变更已明确的公司或年份，但会限制某些模型理解到而规则不理解的复杂句式。真正产品需要把“不可越界的事实约束”和“可由模型补充的语义理解”分开定义，而不是用全量规则要求模型永远与其一致。

### 4.3 Prompt的六项内容

`llm.py` 中的系统指令明确任务只做规划、支持公司与年度、意图与指标枚举、缺失和歧义处理、交易建议边界、用户输入不改变规则。具体提示词是本项目源码，可修改后用固定数据测变化。

在进阶版里还可以添加少量样例，但样例应覆盖正确、歧义和拒绝，不只堆成功案例。一个有效few-shot集合可以含：单公司数值、双公司比较、两年度图、未知实体、季度请求、多指标请求、外部指令注入。每个样例输出应通过同一QueryPlan校验。

### 4.4 Pydantic能保证什么

`extra="forbid"` 拒绝额外字段，Literal约束公司和指标枚举，严格int年份拒绝布尔值和字符串，model_validator检查重复公司/年份与跨字段规则。数据符合schema表示形状与部分约束正确，并不表示它表达了用户真实意图；后面仍要验证公司、年度和指标与显式问题一致。[Pydantic模型文档](https://docs.pydantic.dev/latest/concepts/models/)

练习：构造一个合法计划，依次把company改为600000、year改为True、metric改为sql、重复DEMO_A。都应被拒绝。再构造DEMO_B/2024/revenue计划回答DEMO_A/2025问题：schema允许，但service一致性检查应拒绝。这样就能区分类型校验和业务校验。

### 4.5 LangChain接口的具体用法

当前适配器使用 `ChatOpenAI(..., timeout=30, max_retries=0)`，调用 `with_structured_output(QueryPlan, method="function_calling")`，再将system/human两条消息送入invoke。显式设置method以避免依赖默认行为。供应商需支持这种工具调用机制，结构化输出并非每个模型或兼容服务都相同。[LangChain结构化输出参考](https://reference.langchain.com/python/langchain-openai/chat_models/base/ChatOpenAI/with_structured_output)

接口组装测试用临时假key和假模型名构造真实LangChain对象，禁止httpx发送网络请求；它只能证明安装版本可以构造该链。桩invoke测试验证适配器消息和返回对象；同样不能证明真实模型可用或规划正确。

### 4.6 接入真实模型时的实验记录

先在本机配置有效key和有权限的模型名，本手册不预设模型。用离线演示过的同一批问题，记录原始问题、模型名、提示版本、输出计划、校验结果、最终业务状态、输入/输出token、延迟、失败类型。不要把一次成功当成模型稳定性；重复运行至少观察格式失败和意图变化。

用PowerShell交互读取key可以避免写进脚本正文：

```powershell
$finKeyInput = Read-Host "输入模型服务API Key" -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $finKeyInput).Password
$env:FINEVIDENCE_MODEL = Read-Host "输入账户可用且支持工具调用的模型名"
uv run --frozen --all-extras finevidence "青禾科技2025年营业收入同比" --provider llm
```

这是待你执行的联网实验，不是已验证步骤结果。KEY变量为当前终端会话设置，项目不自动读取.env，也不会把key作为业务字段记录到JSONL。问题、计划中的查询和来源会记录，应只用可公开内容。若第三方服务扩展了标准协议或结构化机制，需使用它的官方适配器并独立测试，而不是只改base_url就假定兼容。[LangChain ChatOpenAI接口范围](https://docs.langchain.com/oss/python/integrations/chat/openai)


## 5. 文档检索：从分段到BM25

### 5.1 文档分段

当前按空行分段，以 `document_id:paragraph_index` 作为片段ID，完整保存title、text、source、company、year。样本短且已人工组织，所以不做滑动窗口。真实财报可能有目录、页眉、表格、跨页附注和扫描图，必须先评估解析；检索失败可能从解析阶段就开始，而不只是向量模型不好。

按标题/段落/表格保留结构，通常比按固定字符数盲切更易溯源。固定窗口可作为基线，但应记录重叠和跨段引用。若将表格拆成行，要一起保存列名、单位、报告期，不能只保留“15000 1500 1750”三个数。

### 5.2 当前分词的准确含义

英文和数字用正则形成词，连续中文加入单字和相邻二元组。例如“营业收入”加入营、业、收、入、营业、业收、收入。它不是jieba式词典分词，也不是语义embedding。这样做有助于短中文词匹配，但会把“的”“为”等普通字计入，带来噪声。

检索前增加非通用二元组/英文词的重合检查，避免仅凭“定义”就匹配到无关资料；FAQ路径又要求用户问题包含支持的金融术语。这是一个保守工程规则，可能牺牲召回。若问题改成“账面赚的为何没到账”，它可能不被本版识别，应作为改进样例，而不是把规则称为完整语义理解。

### 5.3 BM25如何排序

代码采用正值平滑IDF：`log(1 + (N-df+0.5)/(df+0.5))`，`k1=1.5`、`b=0.75`。每个查询token计一次，文档中词频tf经过饱和处理，文档长度与平均长度参与归一化。这些参数是基线设置，不是已经优化出的最佳值。[Stanford IR：BM25](https://nlp.stanford.edu/IR-book/html/htmledition/okapi-bm25-a-non-binary-model-1.html)

代码中的完整单词得分为：

```text
idf(t) = log(1 + (N - df(t) + 0.5) / (df(t) + 0.5))
score(t,d) = idf(t) * tf(t,d) * (k1 + 1)
             / (tf(t,d) + k1 * (1 - b + b * len(d)/avg_len))
score(q,d) = 对查询中的去重token求和
```

例如在一个假设的3文档集合中，某词只出现在1个文档，idf=log(1+2.5/1.5)约0.981；若tf=2、长度等于平均值，单词贡献约 `0.981*2*2.5/(2+1.5)=1.401`。这是用于理解的手算例，不是当前11个片段的一条真实分数。

### 5.4 元数据过滤

数字相关文本检索先限定company和year，再算候选片段得分；FAQ只检索company为空的概念材料。语料统计df和平均长度仍由全部片段建立，过滤只控制候选范围。不要说本版对每个公司单独重建BM25统计。

如果用户明确DEMO_A/2025，DEMO_B/2025即使文本更相似，也不进入结果。跨公司比较允许两家公司；若某家公司文档不存在，结构化数字仍可有来源，但应明确两种数据渠道。未来权限过滤应发生在召回前或至少候选生成阶段，而不是把不该看到的内容先送进模型再删展示。

### 5.5 检索指标怎样定义

已知每个query的相关文档集合R和Top-k结果T，可以定义Recall@k=`|R∩T|/|R|`。单相关答案样本常用hit@k=`相关文档是否在Top-k`，聚合时求比例。MRR计算首个相关结果排名的倒数；nDCG还需要分级相关标签。它们衡量排序/召回，不等于生成答案正确率。

当前evaluate有4条FAQ引用命中检查，不单独发布大规模Recall/MRR。样本太少，成功也只能说明这些固定查询的期望片段在返回集合里。下一步标注至少覆盖同义问法、低频术语、多段证据、未知问题和相近实体，单列结果，不用整体通过掩盖某类失败。

### 5.6 复杂度和规模

初始化一次tokenize全部片段，建立词频和df；查询扫描全部候选片段，每个查询token查Counter。若候选数N、查询token数Q，排序前约O(NQ)，排序约O(NlogN)，本版量级小可以接受。百万片段时要倒排索引或专业检索引擎，并处理更新和过滤，不适合每次全表扫描。

扩展练习：增加50篇人工准备的资料，记录索引构建耗时和查询耗时；改变k1、b和分段方案，只用开发集选参数；测试集最后比较一次，逐例输出相关文档排名。没有完成该实验前，不写“BM25优化后提升xx%”。


## 6. 工具、事实和图表规格

### 6.1 程序负责可复算的数字

模型规划只选择受支持参数，金额计算留给 `FinancialStore.metric()`。这样既可测试公式，也能直接审查来源。若未来允许模型提取财报表格，提取结果先成为待校验数据，不直接跳到最终Fact。

一次同比查询需要本年和上年，因此source保存两条引用。公式字符串只是说明，计算执行的是Python分支，不是eval公式文本。用户也不能通过metric字段选择任意属性或代码：Literal只允许五个指标，原始读取只在这组枚举内分支。

### 6.2 为什么不让模型直接生成SQL或JS

当前没有数据库查询接口，也没有执行模型SQL、Python或JS。数据从受控JSON进入内存字典，图表通过固定渲染函数构建SVG。这可以让你解释自然语言到受约束产物的路线，同时避免把问题扩大为任意代码执行。

未来NL2SQL用只读账户、表/列/聚合白名单、查询预算、超时和参数化SQL模板；不要用字符串“过滤drop”来宣布安全。未来图表用结构化ChartSpec和受控组件，不把任意模型HTML插进页面。

### 6.3 ChartSpec的职责

`chart_type`目前只有bar，title和unit由服务确定；labels、values、source_refs长度必须相等。公司/年度是维度，单指标是度量。ChartSpec不需要知道svg具体x坐标，渲染器不需要重新查询财务事实，二者分工后更容易替换为图表组件。

同图只允许一个metric和unit。例如收入万元和净利率%不能放到同一条共同量轴，除非产品明确采用双轴并处理解释。目前直接拒绝混合，所以“一张图比较青禾收入和净利率”会要求分别查询。

### 6.4 SVG渲染和负值

画布固定900宽，最大绝对值映射到200像素，中心基线x=530；正值从530向右，负值从 `530-width` 向左。label、title和unit经过HTML escape，避免将 `<script>` 或 `<img>` 变成标签。value来自程序计算；labels数量在正常查询中至多2家公司×4个年度，属于受限规模。

条形图用于比较规模，净利率为负也能显示方向。图上的文本保留两位的数字字符串，像素比例的小数误差不改写实际金额。来源引用在JSON的ChartSpec中保留，目前SVG正文只显示虚构标记，若要交付可独立溯源的图，应补图下注释和来源链接。

### 6.5 图表验收

检查数据点个数和预期一致、顺序按公司和升序年度、单位单一、数值与Fact逐个对应、负值方向正确、0值仍有标签。用XML解析检查SVG可解析，但XML合法不代表图表有可读性。真实业务要增加长名称、极大/极小数值、密集标签、窄屏、色盲和打印场景。


## 7. FastAPI、并发和接口错误

### 7.1 同步端点与耗时操作

当前接口用普通 `def`，由FastAPI的同步端点机制在工作线程运行。模型规划是同步invoke，文件读写也是同步，不直接放进一个async端点里阻塞事件循环。若后续改成 `async def`，应使用供应商的异步调用与异步IO，或明确将同步工作移入线程池。

响应模型限定输出字段并验证形状，不能靠HTTP200认定业务成功；status和facts仍要检查。[FastAPI响应模型文档](https://fastapi.tiangolo.com/tutorial/response-model/)

### 7.2 单进程容量限制

API lifespan创建一个容量4的BoundedSemaphore，请求尝试非阻塞acquire，满了立即429并附 `Retry-After: 2`。finally确保处理失败时release。这里的4是配置上限，不是测得的吞吐，也不是跨进程总并发限制。

若启动多个uvicorn worker，每个进程会有自己的容量，整体最多会按worker数增加；当前start.ps1默认单进程。真正高并发服务需网关限流、共享配额或任务队列。不要把线程信号量写成“分布式限流系统”。

### 7.3 超时与重试

模型适配器指定30秒超时、0次内部重试，便于看到故障而不被隐藏重试拖长。它约束模型HTTP调用，不是整个端到端请求的绝对截止时间。数据读取、排队、日志和客户端也各有耗时。生产设计需统一deadline和取消传播。

网络超时可做有限次数重试，但考虑幂等、速率限制和费用；数据格式失败不应无限重试。重试成功的请求也要标注额外延迟和调用数，否则平均成功率会掩盖成本。不要把每个错误都映射为“模型不够聪明”。

### 7.4 HTTP和业务状态

| 情况 | 协议/业务结果 | 客户端动作 |
| --- | --- | --- |
| 问题为空、太长、额外字段 | 422 | 修正输入 |
| 服务容量已满 | 429 + Retry-After | 退避重试 |
| 样本没有2026年 | 200 + no_evidence | 展示数据缺失 |
| 最新股价、未知实体或口径 | 200 + clarify | 提示补充或选择 |
| 已识别的交易建议请求 | 200 + blocked | 展示支持范围 |
| 规划器失败或与输入冲突 | 200 + clarify + planner.failed事件 | 重述或检查配置 |
| 图表端点没有图表计划 | 422 | 提供支持的图表问题 |
| 程序内部未捕获异常 | 可能500 | 运维排查，不假装没有财报 |

### 7.5 多轮与鉴权扩展

本版请求没有session_id和登录，不能说支持多用户账户。扩展时增加user_id、conversation_id、turn_id和明确授权，保存用户显式确认的实体和年度，允许“换成澄海”引用上一个有效问题。回答中公开继承的上下文，让用户能发现误用。

服务端从身份凭据决定user_id，不接受客户端随意声称他人身份。业务状态、模型上下文和长期记忆分离；模型不能通过一条工具调用获取他人的财务或对话记录。已有VerdictPilot可以作为SQLite持久化与记忆接口的阅读参考，但其中本地学习标识也不等于生产身份鉴权。


## 8. 来源、日志和可观察性

### 8.1 需要哪些事件

一次正常请求有request.started、plan.completed、evidence.completed、request.completed。模型错误增加planner.failed。run_id关联所有事件，UTC时间表示发生时刻，elapsed_ms表示本地服务总耗时。上海时间展示需要按UTC+8转换，不应直接把UTC字符串标成北京时间。

plan.completed保存结构化计划，其中retrieval_query可能包含原问题；本版没有自动脱敏。API key不在事件schema内，也不主动打印异常详情中的供应商返回，但这不等于完整隐私系统。若用户问题出现账户、手机号或其他敏感数据，日志可能包含它，需要增加字段级脱敏和访问控制。

### 8.2 当前JSONL能做什么

逐行JSON便于检索和离线分析，单实例锁防止同一个TraceWriter的并发写入交叉。它不是跨进程锁：多个worker或不同Copilot实例写同一文件时需要统一写入器或数据库。当前没有日志轮转、保留期限、导出审计和统计看板。

读日志时先看status再看plan；plan错误导致的答案问题应该归到规划，不是算术。数字来源为空/丢年度归到数据或事实构建。文档片段不相关归到检索；图形展示与facts不一致归到规格或渲染。这样能让修复指向具体模块。

### 8.3 来源不等于真实性证明

`fixture:`表示本地教学数据的标识，不是官方披露URL。程序能证明结果追溯到哪条输入，但不能证明输入是真实财报。真实资料需要保存URL、采集时间、文档hash和页/表定位，再考虑复核、授权和修订。具有引用的幻觉仍可能是幻觉，引用验证只能检查标识存在，还需要判断证据能否支持结论。

### 8.4 进阶观测字段

建议增加prompt_version、retriever_version、dataset_hash、planner_model、input_tokens、output_tokens、tool_latency_ms、retry_count、error_class、evidence_ids、plan_validation_result。模型成本要按供应商实际账单或已核验的单价和token记录计算，不给本版虚构费用数字。

不要把未返回用量的调用当成0token；存unknown并补原因。p50/p95需要足够样本和明确包含的阶段。当前evaluate单次24条离线顺序请求的p95不代表联网模型、冷启动或并发服务性能。


## 9. 测试与评测怎样形成证据

### 9.1 自动化测试的分层

`test_finance.py`检查公式、单位、同比双来源、缺失与零/负基数。`test_service.py`检查业务路由、引用范围、默认年度、比较部分缺失、SVG转义、trace和模型计划一致性。`test_api.py`检查HTTP返回、422、429和计划schema。`test_llm_adapter.py`检查本地链组装、桩invoke、故障状态。`test_scope.py`检查财务口径与混合未知实体。

接口测试用TestClient，并在上下文管理器里触发生命周期，确保依赖和容量确实被初始化。它验证应用接口行为，但不验证网络部署、TLS、网关或浏览器兼容。[FastAPI测试文档](https://fastapi.tiangolo.com/tutorial/testing/)

### 9.2 固定回归的含义

24条样本包含单指标、同比、净利率、对比、图表、缺失、未知、实时、建议边界、4条概念检索、无关问题、季度、多指标与不支持指标。每条预先写status/intent，数字样本还写values/units，资料样本写期望片段ID，图表样本写点数。

evaluate将实际结果逐项对照，而不是让另一个模型凭“读起来合理”打分。报告包含数据版本、样本数、通过数和逐例状态。本版24/24只是这组人工固定样本的结果，未做独立泛化测试，也未评价真实模型。

### 9.3 如何设计独立测试集

先列任务维度，再生成样本。按实体、年度、指标、表达、风险/歧义和数据缺失做组合。开发集用于调规则和Prompt，测试集冻结后只用于最后检验。样本高度相似时按模板族分组划分，例如“利润为什么不同”和“为什么利润不一样”不能一条训练一条测试就宣称泛化。

真实财报检索按公司和报告时间切分，避免同一报告的不同片段泄漏；训练小模型时也检查引用答案和模板的重复。若测试分布有最新信息问题，必须约束“当时可见资料”，否则答案准确可能来自未来数据。

### 9.4 分别计算不同指标

| 层 | 评测项 | 示例 |
| --- | --- | --- |
| 意图 | intent accuracy、各类precision/recall | chart被误判metric |
| 参数 | entity/year/metric exact match | 2025错成2024 |
| 检索 | hit@k、Recall@k、MRR | 期望资料没进Top3 |
| 数据 | 金额、单位、公式、来源 | 万元错成亿元 |
| 回答 | 证据支持率、引用有效率、缺失处理 | 有引用但结论不受支持 |
| 图表 | 数据对齐、单位、规格合法率 | 标签和数值错位 |
| 服务 | p50/p95、超时、429、每请求成本 | 成功但耗时超预算 |

整体通过定义应要求核心条件共同满足。一条答案即使中文流畅，若公司或单位错了也失败。金融信息类任务中数字正确和时效范围应优先于措辞漂亮。

### 9.5 失败案例复盘模板

```text
case_id:
输入/预期:
实际plan:
实际facts/evidence:
失败层: parsing / planning / retrieval / data / rendering / service
根因证据:
修改点:
新增回归:
是否影响其他样本:
复现命令:
```

### 9.6 下一轮评测建议

建立至少包含口语、否定、缩写、未知实体、最新数据、多指标、跨年同比、多证据和无答案类型的集合。规模根据可人工复核能力决定，先做20个新困难样本比仓促复制500个模板更有价值。报告应该列总数、每类数、独立划分方式、真实模型名和配置，再写结果。

CRAG提供了涉及不同知识复杂度和时效要求的RAG评测思路；可以用来理解评测维度，但本项目不能直接照搬其总体指标当作自己的结果。[CRAG研究论文](https://arxiv.org/abs/2406.04744)


## 10. 常见故障与定位

### 10.1 uv或命令不存在

确认 `Get-Command uv`，并在项目目录执行。若命令行入口finevidence未安装，先 `uv sync --frozen --all-extras`，也可运行 `uv run --frozen --all-extras python -m finevidence.cli "青禾科技2025年净利率"`。不要从不明来源复制依赖包替代安装。

### 10.2 找不到fixtures

项目按源码路径默认寻找仓库根。如果把wheel单独装到其他位置，fixtures没有打包进wheel，需要设置 `FINEVIDENCE_ROOT` 为有fixtures的完整项目目录。本项目主要提供源码仓库运行，不承诺无外部数据目录的独立wheel部署。

### 10.3 端口8012占用

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1 -Port 8013
```

同步改访问端口。不要随意结束陌生进程，先确认占用者。原VerdictPilot通常使用8000，工作台使用8001，本版默认8012。

### 10.4 API仍显示offline

API需在启动前设置 `$env:FINEVIDENCE_PROVIDER='llm'` 并配置key/model，再重启。CLI默认离线，需要 `--provider llm`；只设置API环境变量不会改CLI默认。环境变量保留在终端会话，新开终端需要重新配置。

### 10.5 模型模式返回clarify

先看note和trace有没有planner.failed。可能是缺配置、权限、协议不支持工具调用、超时、返回schema错误或显式实体/年度/指标不一致。记录失败类型，勿输出key或完整认证头。LangChain本地组装通过只能证明对象可构造，不能排除任何网络与模型错误。

### 10.6 数值看起来不对

先看数据版本，再看company/year/metric，再手算公式。检查输入说的是净利润还是扣非、年度还是季度、万元还是亿元。value是字符串形式金额，不要把所有字符串字段都转成float再操作。需要高精度后续计算时使用Decimal而不是展示后的四舍五入值。

### 10.7 检索答非所问

先打印候选的title、id、score和text，检查公司/年度范围及分词。通用字词可能带来偶然匹配，支持的金融术语门槛也可能漏掉口语。添加你实际遇到的问题和预期证据，改分词或排序后跑全组回归。不要只通过提高阈值让所有难问题拒答来“提升正确率”；同时测回答覆盖率和误答率。

### 10.8 图表未生成

检查plan.intent是否chart。问题需要明确一个支持的指标和公司，包含图/可视化提示。数字问题可得到facts但chart为null；此时--svg会报告需要图表问题。未知年度或多指标也不会生成图表，这是当前契约。

### 10.9 测试通过但演示失败

TestClient是进程内接口测试，实际服务还受端口、目录、环境变量与网络影响。先health检查，再同请求通过HTTP调用，再检查图表内容。真实模型、浏览器、真实资料和部署均需独立验证，不能从单元测试推断。


## 11. 官方资料索引与使用边界

下列链接在2026-10-12核对，软件文档可能更新，接口实践以本项目uv.lock和本地运行结果为准。参考资料提供原理与API出处，不意味着本项目已实现资料中的完整系统。

| 资料 | 用途 |
| --- | --- |
| [LangChain ChatOpenAI](https://docs.langchain.com/oss/python/integrations/chat/openai) | 适配器接口、协议范围 |
| [LangChain structured output参考](https://reference.langchain.com/python/langchain-openai/chat_models/base/ChatOpenAI/with_structured_output) | 显式结构化方法 |
| [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/) | 模型与验证配置 |
| [FastAPI response model](https://fastapi.tiangolo.com/tutorial/response-model/) | 输出契约 |
| [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/) | 进程内接口测试 |
| [Python3.12 Decimal](https://docs.python.org/3.12/library/decimal.html) | 数字计算与舍入 |
| [Python3.12 sqlite3](https://docs.python.org/3.12/library/sqlite3.html) | 数据库扩展与参数绑定 |
| [Stanford IR BM25](https://nlp.stanford.edu/IR-book/html/htmledition/okapi-bm25-a-non-binary-model-1.html) | 稀疏检索原理 |
| [RAG论文](https://arxiv.org/abs/2005.11401) | 检索与生成结合 |
| [CRAG论文](https://arxiv.org/abs/2406.04744) | RAG评测维度 |
| [Sentence Transformers retrieve/rerank](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html) | 两阶段检索 |
| [LoRA论文](https://arxiv.org/abs/2106.09685) | 低秩适配 |
| [PEFT quicktour](https://huggingface.co/docs/peft/en/quicktour) | 适配器构造与保存 |
| [TRL SFTTrainer](https://huggingface.co/docs/trl/en/sft_trainer) | 监督训练配置 |
