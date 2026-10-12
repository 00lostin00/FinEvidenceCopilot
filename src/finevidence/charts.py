from decimal import Decimal
from html import escape

from .models import ChartSpec


def render_svg(spec: ChartSpec) -> str:
    values = [Decimal(value) for value in spec.values]
    maximum = max([abs(value) for value in values] + [Decimal(1)])
    height = 105 + len(values) * 52
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" '
        f'viewBox="0 0 900 {height}" role="img">',
        '<rect width="100%" height="100%" fill="#f7f9fc"/>',
        f"<title>{escape(spec.title)}</title>",
        f'<text x="20" y="30" font-size="19">{escape(spec.title)} / {escape(spec.unit)}</text>',
    ]
    for index, (label, value) in enumerate(zip(spec.labels, values, strict=True)):
        y = 65 + index * 52
        width = float(abs(value) / maximum * 200)
        x = 530 - width if value < 0 else 530
        color = "#bc4b51" if value < 0 else "#3563a9"
        lines.extend(
            [
                f'<text x="20" y="{y + 18}" font-size="14">{escape(label)}</text>',
                f'<rect x="{x:.2f}" y="{y}" width="{width:.2f}" height="24" fill="{color}"/>',
                f'<text x="760" y="{y + 18}" font-size="14">{value}</text>',
            ]
        )
    lines.extend(
        [
            f'<line x1="530" y1="55" x2="530" y2="{height - 35}" stroke="#888"/>',
            f'<text x="20" y="{height - 12}" font-size="12">'
            "全部数据为虚构教学样本；负值向左，正值向右。</text>",
            "</svg>",
        ]
    )
    return "\n".join(lines)
