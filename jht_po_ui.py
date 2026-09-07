#!/usr/bin/env python3
"""Simple Gradio UI for jht_po_styles."""

from __future__ import annotations

import gradio as gr

from jht_po_styles import (
    apply_filters,
    extract_styles,
    format_output,
    parse_suffix_list,
    po_id_from_url,
)


def run_extract(
    url: str,
    until: str,
    inclusive: bool,
    skip: str,
    strike: str,
    fmt: str,
    headed: bool,
) -> tuple[str, str]:
    url = (url or "").strip()
    if not url:
        return "请粘贴采购单完整 URL。", ""
    if "#" not in url:
        return "链接里通常包含 #/pages/...，请确认复制的是完整分享链接。", ""

    until_val = (until or "").strip() or None
    skip_set = parse_suffix_list(skip)
    strike_set = parse_suffix_list(strike)

    try:
        styles = extract_styles(url, headed=bool(headed))
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "Chromium" in msg or "chromium" in msg:
            msg = (
                "首次运行需要下载 Chromium 浏览器组件（约 150MB），请保持联网后重试。\n"
                + msg
            )
        return f"提取失败：{msg}", ""

    result = apply_filters(
        styles,
        until=until_val,
        inclusive=bool(inclusive),
        skip=skip_set,
        strike=strike_set,
    )

    md = fmt == "Markdown 复选框"
    unicode_mode = fmt == "Unicode 删除线（备忘录）"
    body = format_output(
        result.styles,
        strike=strike_set,
        check=set(),
        md=md,
        unicode_strike_mode=unicode_mode,
    )

    po_id = po_id_from_url(url) or "?"
    summary = f"采购单 {po_id} · 共 {len(result.styles)} 个款号"
    if result.struck:
        summary += f" · 删除线 {len(result.struck)}"
    if result.skipped:
        summary += f" · 已跳过 {len(result.skipped)}"
    if result.unmatched_strike:
        summary += " · 未命中删除线：" + ",".join(result.unmatched_strike)
    if result.unmatched_skip:
        summary += " · 未命中跳过：" + ",".join(result.unmatched_skip)
    plus = [s for s in result.styles if "+" in s]
    if plus:
        summary += " · +组合：" + "、".join(plus)
    summary += "\n复制下方结果 → 粘贴到备忘录 → 全选 → 点「核对清单」"
    return summary, body


CSS = """
.gradio-container { max-width: 880px !important; }
footer { display: none !important; }
"""


def build() -> gr.Blocks:
    with gr.Blocks(title="聚水潭采购单 · 款号提取", css=CSS) as demo:
        gr.Markdown(
            """
# 聚水潭采购单款号提取
粘贴完整分享链接（含 `#`）。支持截止号、跳过、删除线。

首次提取若尚未安装浏览器组件，会自动下载 Chromium（约 150MB，需联网）。
"""
        )
        url = gr.Textbox(
            label="采购单链接",
            placeholder="https://jhtwechat.erp321.com/jht/h5/wx/#/pages/wx/purchaseorder/detail/index?po_id=...",
            lines=2,
        )
        with gr.Row():
            until = gr.Textbox(label="截止号（如 6047）", scale=1)
            inclusive = gr.Checkbox(label="含本号码", value=True, scale=1)
            headed = gr.Checkbox(label="显示浏览器（排查登录）", value=False, scale=1)
        skip = gr.Textbox(
            label="跳过尾号",
            placeholder="2780,2763 或 2780.2763",
        )
        strike = gr.Textbox(
            label="删除线尾号",
            placeholder="2234,2275,5507",
        )
        fmt = gr.Radio(
            choices=["备忘录纯文本", "Markdown 复选框", "Unicode 删除线（备忘录）"],
            value="备忘录纯文本",
            label="输出格式",
        )
        run = gr.Button("开始提取", variant="primary")
        summary = gr.Textbox(label="摘要", lines=2)
        result = gr.Textbox(label="结果（可全选复制）", lines=24)

        run.click(
            run_extract,
            inputs=[url, until, inclusive, skip, strike, fmt, headed],
            outputs=[summary, result],
        )
    return demo


def main() -> None:
    demo = build()
    demo.launch(inbrowser=True, show_error=True)


if __name__ == "__main__":
    main()
