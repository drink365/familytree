
# -*- coding: utf-8 -*-
from typing import Dict, Tuple, List

# 稅率級距（依使用者提供習慣）
# 0～56,210,000：10%；56,210,001～112,420,000：15%；112,420,001 以上：20%
BRACKETS = [
    (56_210_000, 0.10, 0),
    (112_420_000, 0.15, 2_810_000),
    (10**15, 0.20, 8_430_000),  # 上界給一個超大值
]

def taiwan_estate_tax(taxable_amount: int) -> int:
    """依分段速算表計稅。"""
    x = int(max(0, taxable_amount))
    if x <= BRACKETS[0][0]:
        return int(x * 0.10)
    elif x <= BRACKETS[1][0]:
        return int(x * 0.15 - 2_810_000)
    else:
        return int(x * 0.20 - 8_430_000)

def liquidity_need_estimate(tax: int, fees_ratio: float = 0.01) -> int:
    """流動性需求 ≈ 稅 + 雜費（估比）"""
    tax = int(max(0, tax))
    fees = int(tax * max(0.0, fees_ratio))
    return tax + fees

def plan_with_insurance(need: int, available: int, cover: int, pay_years: int, premium_ratio: float):
    """回傳保單規劃的關鍵數據。annual_premium 以 cover/premium_ratio/年期 粗估。"""
    need = int(max(0, need))
    available = int(max(0, available))
    cover = int(max(0, cover))
    premium_ratio = max(1.0, float(premium_ratio))
    pay_years = int(max(1, pay_years))

    annual_premium = int(cover / premium_ratio / pay_years)
    surplus_after_cover = int(available + cover - need)
    return dict(annual_premium=annual_premium, surplus_after_cover=surplus_after_cover)

def quick_preparedness_score(scan: Dict) -> Tuple[int, List[str]]:
    """簡易打分：100滿分，以缺口風險與治理狀態加權。"""
    score = 100
    flags = []

    # 流動性比例
    estate = max(1, int(scan.get("estate_total", 0)))
    liquid = int(scan.get("liquid", 0))
    liquid_ratio = liquid / estate
    if liquid_ratio < 0.10:
        score -= 20; flags.append("流動性比例偏低（<10%），遇遺產稅可能需賣資產。")
    elif liquid_ratio < 0.20:
        score -= 10; flags.append("流動性比例較低（<20%）。")

    # 跨境
    if scan.get("cross_border") == "是":
        score -= 10; flags.append("存在跨境資產/家人，需另行檢視法稅合規與受益人居住地。")

    # 婚姻與繼承關係複雜度
    marital = scan.get("marital")
    if marital in ["離婚/分居", "再婚/有前任"]:
        score -= 10; flags.append("婚姻結構較複雜，建議儘早訂定遺囑/信託避免爭議。")

    # 治理工具
    if scan.get("has_will") in ["沒有", "有（但未更新）"]:
        score -= 10; flags.append("沒有有效遺囑或未更新。")
    if scan.get("has_trust") in ["沒有", "規劃中"]:
        score -= 10; flags.append("尚未建立信託/保單信託。")

    # 現有保額占缺口的粗估（若缺乏就降分）
    existing_ins = int(scan.get("existing_insurance", 0))
    if existing_ins < estate * 0.05:
        score -= 10; flags.append("既有保額偏低，恐不足以應付稅務與現金流衝擊。")

    score = max(0, min(100, score))
    return score, flags

def format_currency(x: int) -> str:
    return f"NT$ {int(x):,}"
