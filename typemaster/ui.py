"""Reusable Streamlit UI helpers: HTML cards, empty/error states and compat shims."""
from __future__ import annotations

import html
import inspect
from typing import Any, Callable, Sequence

import streamlit as st


# --------------------------------------------------------------------- compat
def _has_param(func: Callable, name: str) -> bool:
    try:
        return name in inspect.signature(func).parameters
    except (TypeError, ValueError):
        return False


def call_stretch(func: Callable, *args: Any, **kwargs: Any) -> Any:
    """Call a Streamlit element so it fills its container on any Streamlit 1.3x+."""
    if _has_param(func, "width"):
        try:
            return func(*args, width="stretch", **kwargs)
        except Exception:  # older releases used ``width`` for pixels only
            pass
    if _has_param(func, "use_container_width"):
        return func(*args, use_container_width=True, **kwargs)
    return func(*args, **kwargs)


def show_chart(fig: Any) -> None:
    call_stretch(st.plotly_chart, fig, config={"displayModeBar": False})


def show_table(data: Any, **kwargs: Any) -> None:
    call_stretch(st.dataframe, data, hide_index=True, **kwargs)


# ------------------------------------------------------------------- html bits
def html_block(markup: str) -> None:
    """Render raw HTML. Lines are flattened because Markdown treats 4-space indents as code."""
    flat = " ".join(line.strip() for line in markup.splitlines())
    st.markdown(flat, unsafe_allow_html=True)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def card(label: str, value: str, sub: str = "", tone: str = "") -> str:
    sub_html = f'<div class="tm-sub">{esc(sub)}</div>' if sub else ""
    return (
        f'<div class="tm-card {tone}"><div class="tm-label">{esc(label)}</div>'
        f'<div class="tm-value">{esc(value)}</div>{sub_html}</div>'
    )


def card_grid(cards: Sequence[str], cols: int = 4) -> None:
    html_block(f'<div class="tm-grid cols-{cols}">{"".join(cards)}</div>')


def badge(text: str, tone: str = "") -> str:
    return f'<span class="tm-badge {tone}">{esc(text)}</span>'


def section_title(title: str, hint: str = "") -> None:
    hint_html = f'<span class="tm-hint">{esc(hint)}</span>' if hint else ""
    html_block(f'<div class="tm-section"><h3>{esc(title)}</h3>{hint_html}</div>')


def empty_state(title: str, body: str, icon: str = "") -> None:
    """``icon`` is accepted for backwards compatibility and ignored (clean, icon-free look)."""
    html_block(
        f'<div class="tm-empty"><div class="tm-empty-title">{esc(title)}</div>'
        f'<div class="tm-empty-body">{esc(body)}</div></div>'
    )


def go(page: str) -> None:
    """Callback helper: switch the top navigation to ``page``."""
    st.session_state["nav"] = page


def page_header(title: str, subtitle: str = "") -> None:
    sub = f'<p class="tm-page-sub">{esc(subtitle)}</p>' if subtitle else ""
    html_block(f'<div class="tm-page-head"><h2>{esc(title)}</h2>{sub}</div>')


_KEY_ROWS = (("1234567890-", 0), ("qwertyuiop", 0.5), ("asdfghjkl;'", 0.8), ("zxcvbnm,./", 1.2))


def keyboard_html(stats: dict) -> str:
    """Keyboard heat-map: keys shade from green (clean) to red (error-prone). ``stats`` = {key: [attempts, errors]}."""
    def tint(key: str) -> tuple[str, str]:
        att, err = stats.get(key, [0, 0])
        if att == 0:
            return "", "Not typed yet"
        rate = err / att
        r = int(94 + (255 - 94) * min(rate * 3, 1))      # mint -> coral
        g = int(227 + (107 - 227) * min(rate * 3, 1))
        b = int(161 + (107 - 161) * min(rate * 3, 1))
        return f"background:rgba({r},{g},{b},0.26);border-color:rgba({r},{g},{b},0.7);", f"{err} of {att} missed ({rate:.0%})"

    rows = []
    for keys, offset in _KEY_ROWS:
        cells = "".join(
            f'<div class="tm-key" style="{tint(k)[0]}" title="{esc(tint(k)[1])}">{esc(k.upper())}</div>' for k in keys
        )
        rows.append(f'<div class="tm-key-row" style="margin-left:calc({offset} * var(--key))">{cells}</div>')
    space_style, space_tip = tint("space")
    rows.append(f'<div class="tm-key-row" style="margin-left:calc(3.2 * var(--key))">'
                f'<div class="tm-key space" style="{space_style}" title="{esc(space_tip)}">SPACE</div></div>')
    return f'<div class="tm-keyboard">{"".join(rows)}</div>'



def error_state(title: str, body: str) -> None:
    html_block(
        f'<div class="tm-error"><div class="tm-empty-title">{esc(title)}</div>'
        f'<div class="tm-empty-body">{esc(body)}</div></div>'
    )


def choice(label: str, options: Sequence[Any], *, key: str, default: Any, format_func: Callable = str) -> Any:
    """A horizontal radio whose value survives the widget being un-rendered between phases."""
    store = f"{key}_value"
    current = st.session_state.get(store, default)
    if current not in options:
        current = default
    picked = st.radio(
        label, list(options), index=list(options).index(current), horizontal=True,
        format_func=format_func, key=f"{key}_widget",
    )
    st.session_state[store] = picked
    return picked
