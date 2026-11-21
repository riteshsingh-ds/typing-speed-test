"""Badge and certificate images (PNG / PDF) plus signed, verifiable certificate IDs.

Every image carries TypeMaster branding, the founder's signature and an "Approved" seal.
Rendering uses Pillow with 2x supersampling for smooth edges and bundled fonts, so the output
looks identical on Windows, macOS and Linux.
"""
from __future__ import annotations

import hashlib
import hmac
import io
import math
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from . import config
from .progress import BY_ID, Achievement, earned_dates

FONT_FILES = {
    "bold": "Poppins-Bold.ttf", "med": "Poppins-Medium.ttf", "reg": "Poppins-Regular.ttf",
    "script": "Lora-Italic-Variable.ttf", "mono": "DejaVuSansMono-Bold.ttf",
}
INK, PANEL, AMBER, MUTED, TEXT = (13, 16, 22), (20, 25, 34), (255, 180, 84), (128, 137, 160), (233, 230, 222)
TIERS = {   # main, light, dark
    "bronze": ((205, 127, 50), (240, 190, 140), (120, 66, 20)),
    "silver": ((190, 202, 216), (238, 243, 249), (95, 108, 124)),
    "gold": ((242, 193, 78), (255, 229, 150), (150, 105, 14)),
    "platinum": ((130, 214, 245), (226, 249, 255), (50, 120, 150)),
}


@lru_cache(maxsize=64)
def _font(key: str, px: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(config.ASSETS_DIR / "fonts" / FONT_FILES[key]), px)
    except OSError:  # font files missing: fall back to Pillow's built-in scalable font
        return ImageFont.load_default(size=px)


class Canvas:
    """Tiny drawing wrapper that works in 1x coordinates but renders at ``ss``x."""

    def __init__(self, w: int, h: int, bg, ss: int = 2) -> None:
        self.w, self.h, self.ss = w, h, ss
        self.img = Image.new("RGBA", (w * ss, h * ss), bg + (255,))
        self.d = ImageDraw.Draw(self.img)

    def _s(self, pts):
        return [(x * self.ss, y * self.ss) for x, y in pts]

    def rect(self, box, fill=None, outline=None, width=1, radius=0):
        x0, y0, x1, y1 = [v * self.ss for v in box]
        if radius:
            self.d.rounded_rectangle((x0, y0, x1, y1), radius * self.ss, fill, outline, width * self.ss)
        else:
            self.d.rectangle((x0, y0, x1, y1), fill, outline, width * self.ss)

    def circle(self, cx, cy, r, fill=None, outline=None, width=1):
        s = self.ss
        self.d.ellipse(((cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s), fill, outline, width * s)

    def poly(self, pts, fill):
        self.d.polygon(self._s(pts), fill=fill)

    def line(self, pts, fill, width):
        self.d.line(self._s(pts), fill=fill, width=int(width * self.ss), joint="curve")

    def glow(self, cx, cy, r, color, strength=60):
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        steps = 40
        for i in range(steps):
            rr = r * (1 - i / steps)
            ld.ellipse(((cx - rr) * self.ss, (cy - rr) * self.ss, (cx + rr) * self.ss, (cy + rr) * self.ss),
                       fill=color + (int(strength * (i + 1) / steps),))
        self.img = Image.alpha_composite(self.img, layer)
        self.d = ImageDraw.Draw(self.img)

    def tw(self, s: str, key: str, size: int) -> float:
        return self.d.textlength(s, font=_font(key, size * self.ss)) / self.ss

    def text(self, x, y, s, key, size, fill, anchor="la"):
        self.d.text((x * self.ss, y * self.ss), s, font=_font(key, size * self.ss), fill=fill, anchor=anchor)

    def fit(self, s: str, key: str, size: int, max_w: float, min_size: int = 24) -> int:
        while size > min_size and self.tw(s, key, size) > max_w:
            size -= 2
        return size

    def wrap(self, s: str, key: str, size: int, max_w: float) -> list[str]:
        lines, cur = [], ""
        for word in s.split():
            trial = f"{cur} {word}".strip()
            if self.tw(trial, key, size) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        return lines + ([cur] if cur else [])

    def spaced(self, cx, y, s, key, size, fill, spacing):
        total = sum(self.tw(ch, key, size) for ch in s) + spacing * (len(s) - 1)
        x = cx - total / 2
        for ch in s:
            self.text(x, y, ch, key, size, fill)
            x += self.tw(ch, key, size) + spacing

    def png(self) -> bytes:
        out = io.BytesIO()
        self.img.convert("RGB").resize((self.w, self.h), Image.LANCZOS).save(out, "PNG", optimize=True)
        return out.getvalue()

    def pdf(self) -> bytes:
        out = io.BytesIO()
        self.img.convert("RGB").resize((self.w, self.h), Image.LANCZOS).save(out, "PDF", resolution=150.0)
        return out.getvalue()


# ----------------------------------------------------------------------- shapes
def _star(cx, cy, big, small, n=5):
    pts = []
    for i in range(n * 2):
        r = big if i % 2 == 0 else small
        a = -math.pi / 2 + i * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _icon(c: Canvas, name: str, cx: float, cy: float, color, light) -> None:
    if name == "target":
        c.circle(cx, cy, 72, outline=color, width=12)
        c.circle(cx, cy, 42, outline=color, width=12)
        c.circle(cx, cy, 14, fill=color)
    elif name == "crown":
        c.poly([(cx - 74, cy + 46), (cx - 74, cy - 34), (cx - 36, cy + 2), (cx, cy - 58), (cx + 36, cy + 2),
                (cx + 74, cy - 34), (cx + 74, cy + 46)], color)
        c.rect((cx - 74, cy + 52, cx + 74, cy + 70), fill=color, radius=6)
    elif name == "diamond":
        c.poly([(cx, cy - 78), (cx + 68, cy - 14), (cx, cy + 78), (cx - 68, cy - 14)], color)
        c.line([(cx - 68, cy - 14), (cx + 68, cy - 14)], light, 6)
        c.line([(cx - 22, cy - 14), (cx, cy - 78), (cx + 22, cy - 14)], light, 5)
        c.line([(cx - 22, cy - 14), (cx, cy + 78), (cx + 22, cy - 14)], light, 5)
    elif name == "check":
        c.line([(cx - 56, cy + 4), (cx - 18, cy + 44), (cx + 58, cy - 46)], color, 24)
        for px, py in [(cx - 56, cy + 4), (cx + 58, cy - 46)]:
            c.circle(px, py, 12, fill=color)
    else:
        c.poly(_star(cx, cy + 4, 82, 34), color)


def _seal(c: Canvas, cx: float, cy: float, r: float, label: bool = True) -> None:
    """Scalloped founder's-approval seal."""
    dark, main = (150, 100, 20), AMBER
    for i in range(28):
        a = i * 2 * math.pi / 28
        c.circle(cx + (r - r * 0.08) * math.cos(a), cy + (r - r * 0.08) * math.sin(a), r * 0.13, fill=main)
    c.circle(cx, cy, r * 0.92, fill=main)
    c.circle(cx, cy, r * 0.76, outline=dark, width=max(2, int(r * 0.035)))
    c.circle(cx, cy, r * 0.66, fill=(255, 214, 140))
    if label:
        c.text(cx, cy - r * 0.40, "TYPEMASTER", "bold", max(10, int(r * 0.12)), dark, "mm")
        c.text(cx, cy - r * 0.02, "APPROVED", "bold", max(12, int(r * 0.20)), (60, 36, 4), "mm")
        c.poly(_star(cx, cy + r * 0.38, r * 0.17, r * 0.07), dark)
    else:
        c.text(cx, cy, "TM", "mono", int(r * 0.52), (60, 36, 4), "mm")


def _logo(c: Canvas, x: float, y: float, size: float) -> None:
    c.rect((x, y + size * 0.06, x + size, y + size * 1.06), fill=(184, 122, 31), radius=size * 0.26)
    c.rect((x, y, x + size, y + size), fill=AMBER, radius=size * 0.26)
    c.text(x + size / 2, y + size / 2 + 1, "TM", "mono", int(size * 0.4), (26, 18, 5), "mm")


def _nice_date(d: date) -> str:
    return d.strftime("%B %d, %Y").replace(" 0", " ")


# ----------------------------------------------------------------------- badge
def badge_png(ach: Achievement, player: str, earned: date) -> bytes:
    main, light, dark = TIERS[ach.tier]
    c = Canvas(1080, 1350, INK)
    c.glow(540, 700, 560, main, 70)
    _logo(c, 70, 62, 72)
    c.text(162, 98, "TypeMaster", "bold", 40, TEXT, "lm")
    c.text(1010, 98, f"{ach.tier.title()} badge", "med", 28, light, "rm")

    c.text(540, 235, "Congratulations! You earned", "reg", 36, MUTED, "mm")
    size = c.fit(ach.name, "bold", 84, 900)
    c.text(540, 310, ach.name, "bold", size, light, "mm")
    for i, line in enumerate(c.wrap(ach.description, "reg", 32, 860)[:2]):
        c.text(540, 386 + i * 44, line, "reg", 32, MUTED, "mm")

    cx, cy = 540, 700
    for sign in (-1, 1):                                   # ribbon tails
        c.poly([(cx + sign * 40, cy + 150), (cx + sign * 150, cy + 190), (cx + sign * 110, cy + 330),
                (cx + sign * 70, cy + 285), (cx + sign * 28, cy + 330)], dark)
    c.circle(cx, cy, 232, fill=dark)
    c.circle(cx, cy, 218, fill=main)
    c.circle(cx, cy, 190, fill=light)
    c.circle(cx, cy, 168, fill=main)
    c.circle(cx, cy, 168, outline=dark, width=4)
    _icon(c, ach.icon, cx, cy, dark, light)
    for dx, dy, r in [(-262, -150, 10), (270, -120, 8), (-240, 180, 7), (250, 190, 11)]:
        c.circle(cx + dx, cy + dy, r, fill=light)

    c.text(540, 1085, "Awarded to", "reg", 28, MUTED, "mm")
    size = c.fit(player, "bold", 58, 860)
    c.text(540, 1140, player, "bold", size, TEXT, "mm")
    c.text(540, 1196, f"Earned {_nice_date(earned)}", "med", 28, light, "mm")

    c.line([(70, 1236), (1010, 1236)], (37, 44, 58), 2)
    _seal(c, 118, 1292, 40, label=False)
    c.text(176, 1280, f"Approved by {config.FOUNDER_NAME}", "med", 28, TEXT, "lm")
    c.text(176, 1314, f"{config.FOUNDER_TITLE}, {config.APP_NAME}", "reg", 24, MUTED, "lm")
    return c.png()


# ------------------------------------------------------------------ certificates
def certificate_body(ach: Achievement, detail: str = "") -> str:
    bodies = {
        "first": f"for completing their first typing test on {config.APP_NAME}{detail}. Every great typist starts with a first keystroke.",
        "streak5": "for practicing typing five days in a row, showing outstanding consistency and discipline.",
        "wpm40": "for reaching a typing speed of 40 words per minute.",
        "wpm60": "for reaching a typing speed of 60 words per minute.",
        "wpm80": "for reaching a typing speed of 80 words per minute.",
        "wpm100": "for reaching a typing speed of 100 words per minute, an elite level of speed.",
        "sharp": "for typing 150 or more characters with at least 98 percent accuracy.",
    }
    return bodies.get(ach.id, f"for earning the {ach.name} badge: {ach.description.lower()}.")


def _certificate_canvas(ach: Achievement, player: str, earned: date, code: str, body: str) -> Canvas:
    W, H = 1754, 1240
    gold, deep = (200, 144, 47), (26, 18, 5)
    c = Canvas(W, H, (251, 248, 241))
    c.rect((40, 40, W - 40, H - 40), outline=gold, width=10)
    c.rect((66, 66, W - 66, H - 66), outline=deep, width=2)
    for x, y in [(66, 66), (W - 66, 66), (66, H - 66), (W - 66, H - 66)]:
        c.circle(x, y, 16, fill=gold)

    brand_w = 64 + 22 + c.tw("TypeMaster", "bold", 44)
    left = W / 2 - brand_w / 2
    _logo(c, left, 104, 64)
    c.text(left + 86, 138, "TypeMaster", "bold", 44, deep, "lm")
    c.text(W / 2, 196, "Typing Speed Challenge", "reg", 24, (110, 100, 80), "mm")

    c.spaced(W / 2, 250, ach.certificate.upper(), "bold", 62, deep, 4)
    c.line([(W / 2 - 150, 340), (W / 2 + 150, 340)], gold, 5)
    c.text(W / 2, 400, "This certificate is proudly presented to", "script", 38, (90, 80, 62), "mm")
    size = c.fit(player, "bold", 116, 1250, 56)
    c.text(W / 2, 505, player, "bold", size, deep, "mm")
    c.line([(W / 2 - 520, 580), (W / 2 + 520, 580)], gold, 3)
    for i, line in enumerate(c.wrap(body, "reg", 34, 1160)[:3]):
        c.text(W / 2, 650 + i * 52, line, "reg", 34, (60, 52, 38), "mm")

    base = 1000
    c.line([(170, base), (560, base)], deep, 2)
    c.text(365, base - 30, _nice_date(earned), "med", 32, deep, "mm")
    c.text(365, base + 34, "Date of award", "reg", 26, (110, 100, 80), "mm")

    c.line([(W - 560, base), (W - 170, base)], deep, 2)
    c.text(W - 365, base - 50, config.FOUNDER_NAME, "script", 58, deep, "mm")
    c.text(W - 365, base + 34, f"{config.FOUNDER_NAME}", "med", 26, deep, "mm")
    c.text(W - 365, base + 68, f"{config.FOUNDER_TITLE}, {config.APP_NAME}", "reg", 24, (110, 100, 80), "mm")

    _seal(c, W / 2, base - 30, 118)
    c.text(W / 2, H - 112, f"Certificate ID  {code}", "mono", 24, (90, 80, 62), "mm")
    c.text(W / 2, H - 80, f"Verify this certificate in the {config.APP_NAME} app under Rewards", "reg", 22, (130, 120, 100), "mm")
    return c


def certificate_png(ach: Achievement, player: str, earned: date, code: str, body: str) -> bytes:
    return _certificate_canvas(ach, player, earned, code, body).png()


def certificate_pdf(ach: Achievement, player: str, earned: date, code: str, body: str) -> bytes:
    return _certificate_canvas(ach, player, earned, code, body).pdf()


# --------------------------------------------------------- signed certificate IDs
_CODE_RE = re.compile(r"^TM-(\d{4,})-([A-Z0-9]+)-(\d{6})-([0-9A-F]{6})$")


def _signature(player_id: int, ach_id: str, earned: date) -> str:
    msg = f"{player_id}:{ach_id}:{earned.isoformat()}".encode()
    return hmac.new(config.CERT_SECRET.encode(), msg, hashlib.sha256).hexdigest()[:6].upper()


def certificate_code(player_id: int, ach_id: str, earned: date) -> str:
    return f"TM-{player_id:04d}-{ach_id.upper()}-{earned:%y%m%d}-{_signature(player_id, ach_id, earned)}"


@dataclass(frozen=True)
class Verified:
    player: str
    certificate: str
    badge: str
    earned: date
    code: str


def verify_certificate(db, code: str) -> Optional[Verified]:
    """Return the certificate details if the ID is genuine, otherwise ``None``."""
    match = _CODE_RE.match((code or "").strip().upper())
    if not match:
        return None
    pid, ach_upper, ymd, sig = int(match[1]), match[2], match[3], match[4]
    ach = next((a for a in BY_ID.values() if a.id.upper() == ach_upper and a.certificate), None)
    if ach is None:
        return None
    try:
        earned = date(2000 + int(ymd[:2]), int(ymd[2:4]), int(ymd[4:]))
    except ValueError:
        return None
    if not hmac.compare_digest(sig, _signature(pid, ach.id, earned)):
        return None
    player = db.get_player(pid)
    if player is None or earned_dates(db.history(pid)).get(ach.id) != earned:
        return None
    return Verified(player.name, ach.certificate, ach.name, earned, match.group(0))
