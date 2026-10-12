# FinEvidence Copilot

带来源的财务资料检索与指标可视化原型。问题转换为查询计划，数字由程序计算，概念问题返回资料摘录与出处；图表由受约束规格导出SVG。

## 功能

- 规则规划与可选LangChain结构化规划接口。
- Markdown段落索引、中文字符/二元组分词、BM25排序和公司/年度过滤。
- Decimal营业收入同比、净利率和现金流查询，保存公式与来源。
- 公司对比、单指标图表规格及SVG导出。
- FastAPI参数校验、并发拒绝、请求事件和本地JSONL记录。

## 快速运行

需要Python3.11+与uv。

```bash
git clone https://github.com/00lostin00/FinEvidenceCopilot.git
cd FinEvidenceCopilot
uv sync --frozen --all-extras
uv run --frozen --all-extras finevidence "青禾科技2025年营业收入同比"
uv run --frozen --all-extras finevidence "青禾科技2023至2025年收入画图" --svg data/revenue.svg
uv run --frozen --all-extras uvicorn finevidence.api:app --host 127.0.0.1 --port 8012
```

访问 http://127.0.0.1:8012/docs。POST /v1/ask接受question，POST /v1/chart.svg返回图表。

## 验证

```bash
uv run --frozen --all-extras pytest
uv run --frozen --all-extras ruff check .
uv run --frozen --all-extras python tools/evaluate.py
uv run --frozen --all-extras python tools/smoke_http.py
```

当前验证为56项测试和24条离线固定回归，覆盖指标口径、单位、缺失年度、引用范围、图表和接口。[验证记录](docs/validation/validation.md)与逐例报告位于docs/validation。

## 模型接口

设置OPENAI_API_KEY与FINEVIDENCE_MODEL，CLI加--provider llm；API设置FINEVIDENCE_PROVIDER=llm后重启。项目不自动加载.env。模型负责规划，最终数字与资料摘录由程序组织；当前测试包含无网络组装及桩，不代表真实模型准确率。

## 文档与范围

- [技术指南](docs/guide.md)与[HTML阅读版](docs/guide.html)。
- fixtures包含两家虚构公司、三个年度、6条记录和7份资料。
- 支持收入、净利润、经营现金流、净利率与收入同比，不提供实时行情或交易建议。
- 未实现多用户鉴权、真实数据接入、向量召回或模型训练；JSON加载面向受控fixtures。

MIT License.
