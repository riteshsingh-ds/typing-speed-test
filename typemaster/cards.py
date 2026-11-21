"""Shareable result card (SVG) - downloadable and ready to post."""
from __future__ import annotations

import html

from . import config


def result_card_svg(player: str, wpm: float, accuracy: float, tier: str, setup: str, when: str) -> str:
    e = lambda v: html.escape(str(v), quote=True)  # noqa: E731
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<defs><radialGradient id="g" cx="15%" cy="0%" r="80%"><stop offset="0" stop-color="#ffb454" stop-opacity="0.22"/><stop offset="1" stop-color="#0d1016" stop-opacity="0"/></radialGradient></defs>
<rect width="1200" height="630" fill="#0d1016"/><rect width="1200" height="630" fill="url(#g)"/>
<rect x="40" y="40" width="1120" height="550" rx="32" fill="#141922" stroke="#252c3a" stroke-width="2"/>
<rect x="80" y="80" width="64" height="64" rx="16" fill="#ffb454"/>
<text x="112" y="124" text-anchor="middle" font-family="monospace" font-size="26" font-weight="700" fill="#1a1205">TM</text>
<text x="164" y="124" font-family="Segoe UI, Arial, sans-serif" font-size="38" font-weight="800" fill="#e9e6de">{e(config.APP_NAME)}</text>
<text x="1120" y="122" text-anchor="end" font-family="Segoe UI, Arial, sans-serif" font-size="26" fill="#8089a0">{e(when)}</text>
<text x="80" y="330" font-family="monospace" font-size="190" font-weight="700" fill="#ffb454">{wpm:.0f}</text>
<text x="80" y="388" font-family="Segoe UI, Arial, sans-serif" font-size="36" fill="#8089a0">words per minute</text>
<text x="80" y="470" font-family="Segoe UI, Arial, sans-serif" font-size="46" font-weight="800" fill="#e9e6de">{e(tier)}</text>
<text x="80" y="515" font-family="Segoe UI, Arial, sans-serif" font-size="28" fill="#8089a0">{e(setup)}</text>
<text x="1120" y="300" text-anchor="end" font-family="monospace" font-size="96" font-weight="700" fill="#5ee3a1">{accuracy:.1f}%</text>
<text x="1120" y="344" text-anchor="end" font-family="Segoe UI, Arial, sans-serif" font-size="30" fill="#8089a0">accuracy</text>
<text x="1120" y="470" text-anchor="end" font-family="Segoe UI, Arial, sans-serif" font-size="36" font-weight="700" fill="#e9e6de">{e(player)}</text>
<text x="1120" y="552" text-anchor="end" font-family="Segoe UI, Arial, sans-serif" font-size="22" fill="#8089a0">typemaster by {e(config.FOUNDER_NAME)}</text>
</svg>"""
