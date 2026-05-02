import streamlit as st


def card(content_html: str, severity: str = "info") -> None:
    palette = {
        "success": ("#3E6B3E", "rgba(62,107,62,0.06)"),
        "warning": ("#A06B1F", "rgba(217,182,107,0.12)"),
        "error":   ("#B6553A", "rgba(182,85,58,0.08)"),
        "info":    ("#5A6655", "rgba(42,51,40,0.04)"),
    }
    bc, bg = palette.get(severity, palette["info"])
    html = (
        f'<div style="border-left:3px solid {bc};background:{bg};'
        f'border-radius:0 14px 14px 0;padding:16px 20px;margin:8px 0;'
        f'border-top:1px solid rgba(42,51,40,0.07);'
        f'border-right:1px solid rgba(42,51,40,0.07);'
        f'border-bottom:1px solid rgba(42,51,40,0.07);'
        f'font-family:Inter,system-ui,sans-serif;color:#2A3328;">'
        f'{content_html}'
        f'</div>'
    )
    try:
        st.html(html)
    except AttributeError:
        st.markdown(html, unsafe_allow_html=True)


def section_header(label: str, badge: str = "") -> None:
    badge_html = ""
    if badge:
        badge_html = (
            f'<span style="font-family:Inter,sans-serif;font-size:0.68rem;'
            f'color:#3E6B3E;background:rgba(62,107,62,0.1);padding:2px 8px;'
            f'border-radius:999px;border:1px solid rgba(62,107,62,0.25);">{badge}</span>'
        )
    html = (
        f'<div style="display:flex;align-items:center;gap:12px;margin:8px 0 20px;">'
        f'<div style="width:3px;height:22px;background:#3E6B3E;border-radius:2px;flex-shrink:0;"></div>'
        f'<span style="font-family:\'Fraunces\',Georgia,serif;font-size:1.05rem;'
        f'font-weight:500;color:#2A3328;letter-spacing:-0.01em;">{label}</span>'
        f'{badge_html}'
        f'</div>'
    )
    try:
        st.html(html)
    except AttributeError:
        st.markdown(html, unsafe_allow_html=True)


def page_hero(eyebrow: str, title: str, title_em: str, lede: str) -> None:
    html = (
        f'<div style="margin:8px 0 28px;">'
        f'<div style="font-family:Inter,sans-serif;font-size:0.68rem;color:#8C9684;'
        f'letter-spacing:0.16em;text-transform:uppercase;margin-bottom:10px;">{eyebrow}</div>'
        f'<div style="font-family:\'Fraunces\',Georgia,serif;font-weight:400;font-size:2.6rem;'
        f'line-height:1.18;letter-spacing:-0.02em;color:#2A3328;margin:0;">'
        f'{title} <em style="font-style:italic;color:#3E6B3E;font-weight:300;">{title_em}</em>'
        f'</div>'
        f'<div style="font-size:0.88rem;color:#5A6655;max-width:520px;margin-top:14px;line-height:1.65;">'
        f'{lede}'
        f'</div>'
        f'</div>'
    )
    try:
        st.html(html)
    except AttributeError:
        st.markdown(html, unsafe_allow_html=True)
