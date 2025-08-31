# utils/pdf_compat.py
# -*- coding: utf-8 -*-
"""
PDF 相容性小工具：
提供 table_compat(...)，自動以 A/B 兩種常見介面呼叫 utils.pdf_utils.table，
確保在不同版本的 pdf_utils 下都能輸出正式的表格。
用法（頁面中）：
    from utils.pdf_compat import table_compat
    flow.append(table_compat(headers, rows, widths=[0.12, 0.29, 0.29, 0.30]))
"""
from typing import Sequence, Optional
from utils.pdf_utils import table  # 你專案既有的 table 元件

__all__ = ["table_compat"]

def table_compat(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    widths: Optional[Sequence[float]] = None,
):
    """
    嘗試兩種呼叫方式：
    A) table(data=[headers] + rows, widths=widths)
    B) table(headers, rows, widths=widths)
    兩者皆失敗則拋出例外，交由呼叫端自行備援。
    """
    # 方案 A：data + widths（多數新版本）
    try:
        data = [list(headers)] + [list(r) for r in rows]
        if widths is not None:
            return table(data=data, widths=list(widths))
        return table(data=data)
    except Exception as e_a:
        # 方案 B：位置參數（部分舊版本）
        try:
            rows_list = [list(r) for r in rows]
            if widths is not None:
                return table(list(headers), rows_list, widths=list(widths))
            return table(list(headers), rows_list)
        except Exception as e_b:
            # 讓呼叫端決定備援（例如退回文字表格）
            raise RuntimeError(f"pdf table incompatible: {e_a} | {e_b}")
