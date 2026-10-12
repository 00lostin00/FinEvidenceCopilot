from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/guide.md"
TARGET = SOURCE.with_suffix(".html")


def main() -> None:
    processor = markdown.Markdown(
        extensions=["fenced_code", "tables", "toc", "sane_lists"],
        extension_configs={"toc": {"toc_depth": "2-3"}},
    )
    body = processor.convert(SOURCE.read_text(encoding="utf-8"))
    style = """
body{margin:0;background:#eef2f7;color:#1b2838;font:16px/1.85 'Microsoft YaHei',sans-serif}
.layout{display:grid;grid-template-columns:300px minmax(0,1000px);max-width:1380px;margin:auto}
nav{position:sticky;top:0;height:100vh;overflow:auto;padding:24px 18px;box-sizing:border-box}
nav ul{padding-left:16px}nav li{margin:7px 0;font-size:13px;line-height:1.5}
main{background:white;margin:20px 10px;padding:40px 48px;border-radius:12px;min-width:0}
h1{font-size:30px;line-height:1.4;color:#163e65}h2{border-top:2px solid #d8e3ef;padding-top:26px}
h3{color:#244e76}a{color:#235d92}code{font:13px/1.7 Consolas,monospace;background:#edf2f7}
pre{background:#172b40;color:#e6edf5;overflow:auto;padding:18px;border-radius:7px}
pre code{background:transparent;color:inherit;white-space:pre}
table{display:block;overflow:auto;border-collapse:collapse;font-size:14px;margin:20px 0}
td,th{border:1px solid #d7e0ea;padding:9px 12px;vertical-align:top}
th{background:#e6eef7;text-align:left}tr:nth-child(even){background:#f6f8fb}
@media(max-width:1000px){.layout{display:block}nav{position:relative;height:auto}
main{padding:22px;margin:0}nav .toc>ul>li>ul{display:none}}
@media print{body{font-size:10pt;background:white}nav{display:none}.layout{display:block}
main{padding:0;margin:0}h2,h3{break-after:avoid}pre{white-space:pre-wrap;overflow:visible}
pre code{white-space:pre-wrap}table{font-size:8pt;display:table;width:100%}tr{break-inside:avoid}}
"""
    html = (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>FinEvidence技术指南</title><style>" + style + "</style></head><body>"
        '<div class="layout"><nav><strong>学习目录 · 技术指南</strong>'
        + processor.toc
        + "</nav><main>"
        + body
        + "</main></div></body></html>"
    )
    TARGET.write_text(html, encoding="utf-8")
    print(f"Rendered: {TARGET}")


if __name__ == "__main__":
    main()
