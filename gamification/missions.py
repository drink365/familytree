# -*- coding: utf-8 -*-
"""
Missions & Events definition with Octalysis core drives mapping.

Core Drives (CD):
CD1 Epic Meaning & Calling
CD2 Development & Accomplishment
CD3 Empowerment of Creativity & Feedback
CD4 Ownership & Possession
CD5 Social Influence & Relatedness
CD6 Scarcity & Impatience
CD7 Unpredictability & Curiosity
CD8 Loss & Avoidance
"""
from typing import Dict, Any, List

# Event points mapping (can be reused directly without missions)
EVENT_POINTS: Dict[str, int] = {
    "completed_readiness_assessment": 50,
    "built_legacy_map": 80,
    "uploaded_policies": 60,
    "booked_consultation": 150,
    "completed_values_module": 70,
    "invited_family_member": 40,
    "finished_tax_simulation": 90,
    "submitted_pre_meeting_form": 30,
    "watched_video_module": 20,
}

# Missions (can bundle multiple events or a single event)
# Each mission should have:
# - id (str)
# - title (str)
# - description (str)
# - suggested_event (str) -> default event logged when user taps "完成"
# - points (int) -> fallback if not using EVENT_POINTS
# - drives (List[str]) -> list of core drive tags, eg. ["CD1", "CD2"]
# - tip (str) -> why it matters (user-friendly)
MISSIONS: Dict[str, Dict[str, Any]] = {
    "mission_readiness": {
        "id": "mission_readiness",
        "title": "完成《傳承準備度》評測",
        "description": "用 3 分鐘快速檢視家族傳承的起跑線，取得建議清單。",
        "suggested_event": "completed_readiness_assessment",
        "points": 50,
        "drives": ["CD1", "CD2", "CD8"],
        "tip": "先知道差距，才好安排下一步（避免延誤造成的成本）。",
    },
    "mission_legacy_map": {
        "id": "mission_legacy_map",
        "title": "建立《家族資產地圖》",
        "description": "把公司股權、不動產、金融資產、保單、海外資產與其他資產，集中成一張圖。",
        "suggested_event": "built_legacy_map",
        "points": 80,
        "drives": ["CD3", "CD4"],
        "tip": "看見全貌，決策更有把握；也方便顧問迅速理解與提案。",
    },
    "mission_upload_policies": {
        "id": "mission_upload_policies",
        "title": "上傳現有保單",
        "description": "匯入或拍照上傳既有保單，平台自動生成缺口建議。",
        "suggested_event": "uploaded_policies",
        "points": 60,
        "drives": ["CD4", "CD2"],
        "tip": "擁有感＋成就感：整理完，才知道如何補強。",
    },
    "mission_values": {
        "id": "mission_values",
        "title": "完成《價值觀探索》",
        "description": "透過卡片與情境，釐清家族的優先順序（教育、公益、保障、股權）。",
        "suggested_event": "completed_values_module",
        "points": 70,
        "drives": ["CD1", "CD3", "CD5"],
        "tip": "價值觀→策略→商品，從心出發，方案才會長久。",
    },
    "mission_tax_sim": {
        "id": "mission_tax_sim",
        "title": "跑一次《遺產／贈與稅試算》",
        "description": "用情境輸入快速試算未來稅務衝擊，避免高成本錯配。",
        "suggested_event": "finished_tax_simulation",
        "points": 90,
        "drives": ["CD8", "CD2"],
        "tip": "先算過，就能避免代價高昂的錯誤與延誤。",
    },
    "mission_invite": {
        "id": "mission_invite",
        "title": "邀請家人共編傳承地圖",
        "description": "邀請配偶或孩子加入，共同參與與確認資料。",
        "suggested_event": "invited_family_member",
        "points": 40,
        "drives": ["CD5", "CD4"],
        "tip": "彼此看見，才能同心。共編會加速共識。",
    },
    "mission_book": {
        "id": "mission_book",
        "title": "預約顧問 30 分鐘導覽",
        "description": "與顧問進行一次 1:1 導覽與需求釐清（可線上）。",
        "suggested_event": "booked_consultation",
        "points": 150,
        "drives": ["CD6", "CD1", "CD5"],
        "tip": "限量名額＋個人化導引，幫你把重要事安排下來。",
    },
    "mission_prefill": {
        "id": "mission_prefill",
        "title": "送出《預約前問卷》",
        "description": "填寫基本情況，顧問可事先準備重點與案例。",
        "suggested_event": "submitted_pre_meeting_form",
        "points": 30,
        "drives": ["CD2", "CD5"],
        "tip": "準備充分，會談效率高一倍。",
    },
    "mission_video": {
        "id": "mission_video",
        "title": "完成一部 5 分鐘快速影片",
        "description": "觀看並回答 3 題小測驗（傳承三把鑰匙）。",
        "suggested_event": "watched_video_module",
        "points": 20,
        "drives": ["CD7", "CD2"],
        "tip": "小步快跑，降低學習門檻，帶著走也能完成。",
    },
}
