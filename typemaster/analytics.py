"""Plotly figure builders. Each function takes plain DataFrames / lists."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from . import config
from .utils import to_local

AMBER, SKY, MINT, CORAL = "#ffb454", "#6bc7ff", "#5ee3a1", "#ff6b6b"
TEXT, MUTED, GRID = "#e9e6de", "#8089a0", "rgba(255,255,255,0.06)"
DIFFICULTY_COLORS = {"Easy": MINT, "Medium": AMBER, "Hard": CORAL}


def _style(fig: go.Figure, title: str, height: int = 340) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0.01, xanchor="left", font=dict(size=15, color=TEXT)),
        height=height,
        margin=dict(l=8, r=8, t=52, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=MUTED, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1.0, bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#1a202b", bordercolor="#252c3a", font=dict(color=TEXT)),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    return fig


def wpm_trend_chart(history: pd.DataFrame) -> go.Figure:
    """WPM of every test in chronological order with a 5-test moving average."""
    df = history.sort_values("created_at").reset_index(drop=True).copy()
    df["test_no"] = df.index + 1
    when = to_local(df["created_at"]).dt.strftime("%b %d, %H:%M")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["test_no"], y=df["wpm"], mode="lines+markers", name="WPM",
        line=dict(color=AMBER, width=2.5), marker=dict(size=7, color=AMBER),
        customdata=list(zip(when, df["accuracy"], df["duration_sec"], df["difficulty"])),
        hovertemplate="Test %{x}<br><b>%{y:.1f} WPM</b><br>Accuracy %{customdata[1]:.1f}%"
                      "<br>%{customdata[2]}s, %{customdata[3]}<br>%{customdata[0]}<extra></extra>",
    ))
    if len(df) >= 3:
        fig.add_trace(go.Scatter(
            x=df["test_no"], y=df["wpm"].rolling(5, min_periods=2).mean(), mode="lines",
            name="5-test average", line=dict(color=SKY, width=2, dash="dot"), hoverinfo="skip",
        ))
    best = float(df["wpm"].max())
    fig.add_hline(y=best, line=dict(color=MINT, width=1, dash="dash"),
                  annotation_text=f"Best {best:.0f}", annotation_font_color=MINT, annotation_position="top left")
    fig.update_xaxes(title="Test number", dtick=1 if len(df) <= 12 else None)
    fig.update_yaxes(title="Net WPM", rangemode="tozero")
    return _style(fig, "Speed over time")


def accuracy_vs_wpm_chart(history: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for difficulty in config.DIFFICULTIES:
        part = history[history["difficulty"] == difficulty]
        if part.empty:
            continue
        fig.add_trace(go.Scatter(
            x=part["wpm"], y=part["accuracy"], mode="markers", name=difficulty,
            marker=dict(color=DIFFICULTY_COLORS[difficulty], size=part["duration_sec"] / 6 + 7,
                        opacity=0.85, line=dict(width=1, color="#0d1016")),
            customdata=part["duration_sec"],
            hovertemplate="%{x:.1f} WPM at %{y:.1f}%<br>%{customdata}s test<extra>" + difficulty + "</extra>",
        ))
    fig.update_xaxes(title="Net WPM", rangemode="tozero")
    fig.update_yaxes(title="Accuracy (%)", range=[max(0, float(history["accuracy"].min()) - 5), 100.5])
    return _style(fig, "Speed vs accuracy")


def _grouped_bars(history: pd.DataFrame, column: str, order: list, labels: list[str], title: str) -> go.Figure:
    grouped = history.groupby(column)["wpm"].agg(["mean", "max"]).reindex(order)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=grouped["mean"], name="Average", marker_color=SKY,
                         hovertemplate="%{x}<br>Average %{y:.1f} WPM<extra></extra>"))
    fig.add_trace(go.Bar(x=labels, y=grouped["max"], name="Best", marker_color=AMBER,
                         hovertemplate="%{x}<br>Best %{y:.1f} WPM<extra></extra>"))
    fig.update_layout(barmode="group", bargap=0.35)
    fig.update_yaxes(title="Net WPM", rangemode="tozero")
    return _style(fig, title)


def difficulty_chart(history: pd.DataFrame) -> go.Figure:
    order = list(config.DIFFICULTIES)
    return _grouped_bars(history, "difficulty", order, order, "Speed by difficulty")


def duration_chart(history: pd.DataFrame) -> go.Figure:
    order = list(config.DURATIONS)
    return _grouped_bars(history, "duration_sec", order, [f"{d}s" for d in order], "Speed by test length")


def activity_chart(history: pd.DataFrame) -> go.Figure:
    days = to_local(history["created_at"]).dt.date
    counts = days.value_counts().sort_index()
    fig = go.Figure(go.Bar(
        x=[d.isoformat() for d in counts.index], y=counts.values, marker_color=MINT,
        hovertemplate="%{x}<br>%{y} tests<extra></extra>",
    ))
    fig.update_layout(bargap=0.4)
    fig.update_xaxes(type="category", title="Day")
    fig.update_yaxes(title="Tests", dtick=1, rangemode="tozero")
    return _style(fig, "Practice activity")


def pace_chart(series: list[float], target_best: float | None = None, ghost: list[float] | None = None) -> go.Figure:
    """Net WPM at the end of each second of one test, optionally against the previous best run (ghost)."""
    fig = go.Figure()
    if ghost:
        fig.add_trace(go.Scatter(
            x=list(range(1, len(ghost) + 1)), y=ghost, mode="lines", name="Previous best run",
            line=dict(color=SKY, width=2, dash="dot"), hovertemplate="%{x}s: %{y:.0f} WPM<extra>Previous best</extra>",
        ))
    fig.add_trace(go.Scatter(
        x=list(range(1, len(series) + 1)), y=series, mode="lines", name="This run", fill="tozeroy",
        line=dict(color=AMBER, width=2.5), fillcolor="rgba(255,180,84,0.12)",
        hovertemplate="%{x}s: %{y:.0f} WPM<extra>This run</extra>",
    ))
    if target_best:
        fig.add_hline(y=target_best, line=dict(color=MINT, width=1, dash="dash"),
                      annotation_text=f"Personal best {target_best:.0f}", annotation_font_color=MINT,
                      annotation_position="top left")
    fig.update_xaxes(title="Seconds")
    fig.update_yaxes(title="Net WPM so far", rangemode="tozero")
    return _style(fig, "Your pace" + (" vs your previous best" if ghost else ""), height=290)
