# 本地验证记录

日期：2026-10-14。环境：Windows、Python3.12.7，依赖按uv.lock。

| 验证 | 命令 | 结果 |
| --- | --- | --- |
| 代码与接口测试 | `uv run --frozen --all-extras pytest` | 64项通过 |
| 静态检查 | `uv run --frozen --all-extras ruff check .` | 通过 |
| 浏览器脚本语法 | `node --check src/finevidence/web/app.js` | 通过 |
| 固定离线业务回归 | `uv run --frozen --all-extras python tools/evaluate.py` | 24/24通过 |
| 实际HTTP | `uv run --frozen --all-extras python tools/smoke_http.py` | health、ask、图表SVG解析、422、缺失年度均通过 |
| 模型适配器组装 | 测试中的真实LangChain对象构造 | 无网络组装通过 |
| 模型流程桩 | 测试中的StubStructured/FakePlanner | 计划返回、范围一致性及失败状态通过 |

真实HTTP验证使用独立临时端口并在结束时停止测试服务，不占用日常8012端口。`demo-response.json`为三年度收入查询结果，`demo-revenue.svg`为同一查询导出的图表，`http-smoke.json`为验证摘要，`eval-results.json`为逐例固定回归。

未验证：真实模型API效果、真实财报数据、生产部署、多用户鉴权、线上运营、向量召回/rerank/SFT/LoRA。示例中的公司、数据和文档均为教学虚构样本。

回归报告的p50/p95是24条离线顺序请求的本机耗时，含本地日志写入，不代表真实模型延迟、并发性能或生产SLA。
