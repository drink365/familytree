
from typing import Dict, List, Tuple
ESTATE_BRACKETS = [(56_210_000, 0.10, 0),(112_420_000, 0.15, 2_810_000),(10**15, 0.20, 8_430_000)]
GIFT_BRACKETS   = [(28_110_000, 0.10, 0),(56_210_000, 0.15, 1_405_000),(10**15, 0.20, 5_621_000)]
def apply_brackets(amount: int, brackets: List[tuple]) -> Dict[str, int]:
    for ceiling, rate, quick in brackets:
        if amount <= ceiling:
            tax = max(int(amount * rate - quick), 0)
            return {"rate": int(rate * 100), "quick": quick, "tax": tax}
    return {"rate": 0, "quick": 0, "tax": 0}
def determine_heirs_and_shares(spouse_alive: bool, child_count: int, parent_count: int, sibling_count: int, grandparent_count: int) -> Tuple[str, Dict[str, float]]:
    shares: Dict[str, float] = {}
    if child_count > 0:
        order = "第一順序（子女）"
        if spouse_alive:
            unit = 1 / (child_count + 1); shares["配偶"] = unit
            for i in range(child_count): shares[f"子女{i+1}"] = unit
        else:
            unit = 1 / child_count
            for i in range(child_count): shares[f"子女{i+1}"] = unit
    elif parent_count > 0:
        order = "第二順序（父母）"
        if spouse_alive:
            shares["配偶"] = 0.5; unit = 0.5 / parent_count
            for i in range(parent_count): shares[f"父母{i+1}"] = unit
        else:
            unit = 1 / parent_count
            for i in range(parent_count): shares[f"父母{i+1}"] = unit
    elif sibling_count > 0:
        order = "第三順序（兄弟姊妹）"
        if spouse_alive:
            shares["配偶"] = 0.5; unit = 0.5 / sibling_count
            for i in range(sibling_count): shares[f"兄弟姊妹{i+1}"] = unit
        else:
            unit = 1 / sibling_count
            for i in range(sibling_count): shares[f"兄弟姊妹{i+1}"] = unit
    elif grandparent_count > 0:
        order = "第四順序（祖父母）"
        if spouse_alive:
            shares["配偶"] = 0.5; unit = 0.5 / grandparent_count
            for i in range(grandparent_count): shares[f"祖父母{i+1}"] = unit
        else:
            unit = 1 / grandparent_count
            for i in range(grandparent_count): shares[f"祖父母{i+1}"] = unit
    else:
        order = "（無繼承人，視為國庫）"
        if spouse_alive: shares["配偶"] = 1.0
    return order, shares
def eligible_deduction_counts_by_heirs(spouse_alive: bool, shares: Dict[str, float]) -> Dict[str, int]:
    cnt_children = sum(1 for k in shares if k.startswith("子女"))
    cnt_asc = sum(1 for k in shares if k.startswith("父母") or k.startswith("祖父母"))
    return {"spouse": 1 if spouse_alive and ("配偶" in shares) else 0, "children": cnt_children, "ascendants": min(cnt_asc, 2)}
