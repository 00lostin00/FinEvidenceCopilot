from decimal import Decimal
from html import escape

from .models import ChartSpec


def render_svg(spec: ChartSpec) -> str:
    values = [Decimal(value) for value in spec.values]
    maximum = max([abs(value) for value in values] + [Decimal(1)])
    signed = any(value < 0 for value in values)
    axis = 310 if signed else 28
    bar_width = 260 if signed else 564
    height = 45 + len(values) * 85
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="620" height="{height}" '
        f'viewBox="0 0 620 {height}" role="img" aria-labelledby="title description">',
        '<rect width="100%" height="100%" fill="#fbfcff"/>',
        f'<title id="title">{escape(spec.title)}</title>',
        '<desc id="description">全部数据为虚构教学样本，数值与来源在工作台明细中列出。</desc>',
        '<g font-family="system-ui, -apple-system, Segoe UI, Microsoft YaHei, sans-serif">',
    ]
    if signed:
        lines.append(
            f'<line x1="{axis}" y1="45" x2="{axis}" y2="{height - 40}" '
            'stroke="#9aabc1" stroke-width="1.5"/>'
        )
    for index, (label, value) in enumerate(zip(spec.labels, values, strict=True)):
        y = 31 + index * 85
        width = float(abs(value) / maximum * bar_width)
        x = axis - width if value < 0 else axis
        color = "#a52c37" if value < 0 else ["#a7bdea", "#628ade", "#245bda"][index % 3]
        lines.extend(
            [
                f'<text x="28" y="{y}" font-size="18" fill="#30465f">'
                f'{escape(label)}</text>',
                f'<text x="592" y="{y}" text-anchor="end" font-size="20" '
                f'font-weight="650" fill="#152840">{value}</text>',
                f'<rect x="28" y="{y + 15}" width="564" height="20" '
                'rx="4" fill="#edf2f9"/>',
                f'<rect x="{x:.2f}" y="{y + 15}" width="{width:.2f}" height="20" '
                f'rx="4" fill="{color}"/>',
            ]
        )
    lines.extend(
        [
            f'<text x="28" y="{height - 13}" font-size="12" fill="#52667e">'
            f'单位：{escape(spec.unit)}；虚构教学数据'
            f'{"；零轴左负右正" if signed else ""}</text>',
            "</g>",
            "</svg>",
        ]
    )
    return "\n".join(lines)
