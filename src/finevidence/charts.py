from decimal import Decimal
from html import escape

from .models import ChartSpec


def render_svg(spec: ChartSpec) -> str:
    values = [Decimal(value) for value in spec.values]
    maximum = max([abs(value) for value in values] + [Decimal(1)])
    signed = any(value < 0 for value in values)
    axis = 550 if signed else 390
    bar_width = 220 if signed else 360
    height = 141 + len(values) * 63
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" '
        f'viewBox="0 0 900 {height}" role="img" aria-labelledby="title description">',
        '<rect width="100%" height="100%" rx="12" fill="#f8fafc"/>',
        f"<title>{escape(spec.title)}</title>",
        '<desc id="description">全部数据为虚构教学样本，数值与来源在工作台明细中列出。</desc>',
        '<g font-family="system-ui, -apple-system, Segoe UI, Microsoft YaHei, sans-serif">',
        f'<text id="title" x="28" y="36" font-size="17" font-weight="600" '
        f'fill="#334155">{escape(spec.title)}</text>',
        f'<text x="28" y="59" font-size="11" fill="#94a3b8">'
        f'同一指标口径 · 单位：{escape(spec.unit)}</text>',
        '<text x="858" y="59" text-anchor="end" font-size="10" '
        'letter-spacing="1" fill="#94a3b8">FINEVIDENCE / DATA VIEW</text>',
        f'<line x1="{axis}" y1="78" x2="{axis}" y2="{height - 62}" '
        'stroke="#d3dce9"/>',
    ]
    for index, (label, value) in enumerate(zip(spec.labels, values, strict=True)):
        y = 87 + index * 63
        width = float(abs(value) / maximum * bar_width)
        x = axis - width if value < 0 else axis
        color = "#c68a57" if value < 0 else ["#a8bef2", "#7298ed", "#2358e8"][index % 3]
        lines.extend(
            [
                f'<text x="28" y="{y + 21}" font-size="13" fill="#64748b">'
                f'{escape(label)}</text>',
                f'<rect x="{x:.2f}" y="{y}" width="{width:.2f}" height="30" '
                f'rx="5" fill="{color}"/>',
                f'<text x="858" y="{y + 21}" text-anchor="end" font-size="14" '
                f'font-weight="600" fill="#334155">{value}</text>',
            ]
        )
    lines.extend(
        [
            f'<line x1="28" y1="{height - 43}" x2="872" y2="{height - 43}" '
            'stroke="#e2e8f0"/>',
            f'<text x="28" y="{height - 21}" font-size="10" fill="#94a3b8">'
            "全部数据为虚构教学样本；负值向左，正值向右。</text>",
            "</g>",
            "</svg>",
        ]
    )
    return "\n".join(lines)
