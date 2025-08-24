def draw_tree():
    data = st.session_state.data
    dot = Digraph(comment="Family", format="svg", engine="dot")

    # 更強的版面約束：同層距離與輸出順序
    dot.graph_attr.update(
        rankdir="TB",         # 上下分層
        splines="ortho",      # 直角線，較少與節點穿插
        nodesep="0.55",
        ranksep="0.8",
        ordering="out"        # 盡量依我們提供的相鄰邊順序輸出
    )
    dot.edge_attr.update(color=LINE_COLOR)

    # 1) 先畫所有人（含男女/過世的樣式）
    for pid, p in data["persons"].items():
        dot.node(pid, person_label(pid), **node_style_by_person(p))

    # 2) 畫每段婚姻的 junction + 可見邊
    marriage_ids = set()
    for m in data["marriages"]:
        marriage_ids.add(m["id"])
        jid = f"J_{m['id']}"
        dot.node(jid, "", shape="point", width="0.02", color=LINE_COLOR)
        style = "dashed" if m.get("divorced") else "solid"
        dot.edge(m["a"], jid, dir="none", style=style)
        dot.edge(m["b"], jid, dir="none", style=style)

        # 讓該段婚姻的兩位配偶同層
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(m["a"])
            s.node(m["b"])

    # 2.1 為「每個人」建立不可見的水平鏈：
    #     [所有前任...] -> 本人 -> [所有現任...]
    #     這會強制「前任永遠在左、現任永遠在右」，避免前任被擠到中間
    spouses_left  = {pid: [] for pid in data["persons"]}
    spouses_right = {pid: [] for pid in data["persons"]}

    for m in data["marriages"]:
        a, b = m["a"], m["b"]
        if m.get("divorced"):     # 視為「前任」
            spouses_left[a].append(b)
            spouses_left[b].append(a)
        else:                     # 視為「現任」
            spouses_right[a].append(b)
            spouses_right[b].append(a)

    for pid in data["persons"].keys():
        chain = spouses_left[pid] + [pid] + spouses_right[pid]
        if len(chain) > 1:
            # 同層 + 高權重不可見邊，形成嚴格的左右順序
            with dot.subgraph() as s:
                s.attr(rank="same")
                for x in chain:
                    s.node(x)
            for u, v in zip(chain, chain[1:]):
                dot.edge(u, v, style="invis", weight="200", minlen="1")

    # 3) 子女連線：為每段婚姻建立一個「children spine」（不可見點）在子女那一層
    #    由 junction 先連到 spine（不可見、高權重），再由 spine 垂直分支到各子女；
    #    並用不可見水平邊強制手足的左右順序（出生序），可明顯減少交錯。
    for row in data["children"]:
        kids = [k for k in row.get("children", []) if k in data["persons"]]
        if not kids:
            continue

        mid = row["marriage_id"]
        if mid in marriage_ids:
            jid = f"J_{mid}"
        else:
            # 沒有父母/婚姻的兄弟姊妹群組，也給一個群組 junction
            jid = f"SIB_{mid}"
            dot.node(jid, "", shape="point", width="0.02", color=LINE_COLOR)

        # 這個婚姻/群組的 children spine
        spine = f"S_{mid}"
        dot.node(spine, "", shape="point", width="0.02", color=LINE_COLOR)

        # spine 與所有子女在同一層
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(spine)
            for k in kids:
                s.node(k)

        # junction → spine：不可見、高權重，讓分支從同一水平點出發
        dot.edge(jid, spine, style="invis", weight="150", minlen="1")

        # 用不可見水平邊固定兄弟姊妹的左右順序（依資料排列）
        for u, v in zip(kids, kids[1:]):
            dot.edge(u, v, style="invis", weight="80", minlen="1")

        # 最後才畫出 spine → 每個孩子（可見）
        for k in kids:
            dot.edge(spine, k)

    st.graphviz_chart(dot, use_container_width=True)
