import React, { useEffect, useMemo, useRef, useState } from "react";
import ELK from "elkjs/lib/elk.bundled.js";

/**
 * Quick Family Tree — React + ELK (MVP)
 * - Persons + Unions (marriages/partnerships)
 * - Children connect ONLY from union → child (stable layout for multi-marriage)
 * - Layered layout with ELK; clean orthogonal edges
 * - Demo data preloaded via "Load Demo" button
 * - Basic CRUD: add person / union / child; select & delete
 * - Export/Import JSON; Download SVG
 *
 * Notes:
 * - This is a single-file demo. In production, split into modules & add persistence (IndexedDB).
 */

// ---------- Types ----------
type PersonID = string;
type UnionID = string;

type Person = {
  id: PersonID;
  name: string;
  gender?: "M" | "F" | "O";
  birth?: string;
  death?: string;
  note?: string;
};

type Union = {
  id: UnionID;
  partners: [PersonID, PersonID];
  status?: "married" | "cohabiting" | "divorced" | "separated" | "widowed";
};

type ChildLink = {
  unionId: UnionID;
  childId: PersonID;
  relation?: "biological" | "adopted" | "step" | "foster";
  order?: number;
};

type TreeDoc = {
  persons: Record<PersonID, Person>;
  unions: Record<UnionID, Union>;
  children: ChildLink[];
};

// ---------- Utils ----------
const elk = new ELK();
const NODE_W = 140;
const NODE_H = 56;
const MARGIN = 48;

const theme = {
  bg: "#0b3d4f",
  fg: "#ffffff",
  border: "#114b5f",
  line: "#0f3c4d",
};

function uid(prefix: string) {
  return `${prefix}_${Math.random().toString(36).slice(2, 9)}`;
}

function demoDoc(): TreeDoc {
  const p: Record<string, Person> = {};
  const u: Record<string, Union> = {};
  const persons = (
    ["陳一郎", "陳前妻", "陳妻", "陳大", "陳二", "陳三", "王子", "王子妻", "王孫"] as const
  ).map((name) => ({ id: uid("P"), name }));
  persons.forEach((pp) => (p[pp.id] = pp));
  const id = (name: string) => persons.find((x) => x.name === name)!.id;

  const m1: Union = { id: uid("U"), partners: [id("陳一郎"), id("陳前妻")], status: "divorced" };
  const m2: Union = { id: uid("U"), partners: [id("陳一郎"), id("陳妻")], status: "married" };
  const m3: Union = { id: uid("U"), partners: [id("王子"), id("王子妻")], status: "married" };
  u[m1.id] = m1; u[m2.id] = m2; u[m3.id] = m3;

  const children: ChildLink[] = [
    { unionId: m1.id, childId: id("王子"), relation: "biological" },
    { unionId: m2.id, childId: id("陳大"), relation: "biological" },
    { unionId: m2.id, childId: id("陳二"), relation: "biological" },
    { unionId: m2.id, childId: id("陳三"), relation: "biological" },
    { unionId: m3.id, childId: id("王孫"), relation: "biological" },
  ];

  return { persons: p, unions: u, children };
}

// Build ELK graph from our model
function buildElkGraph(doc: TreeDoc) {
  const nodes: any[] = [];
  const edges: any[] = [];

  // Person nodes
  Object.values(doc.persons).forEach((p) => {
    nodes.push({ id: p.id, width: NODE_W, height: NODE_H, labels: [{ text: p.name }] });
  });

  // Union nodes (tiny diamond)
  Object.values(doc.unions).forEach((u) => {
    const id = u.id;
    nodes.push({ id, width: 10, height: 10, labels: [{ text: "" }] });
    const [a, b] = u.partners;
    edges.push({ id: uid("E"), sources: [a], targets: [id] });
    edges.push({ id: uid("E"), sources: [b], targets: [id] });
  });

  // Children edges
  doc.children.forEach((cl) => {
    edges.push({ id: uid("E"), sources: [cl.unionId], targets: [cl.childId] });
  });

  const graph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "DOWN",
      "elk.layered.spacing.nodeNodeBetweenLayers": "64",
      "elk.spacing.nodeNode": "46",
      "elk.edgeRouting": "ORTHOGONAL",
      "elk.layered.nodePlacement.bk.fixedAlignment": "BALANCED",
      "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
    },
    children: nodes,
    edges,
  } as const;

  return graph as any;
}

function pathFromSections(sections: any[]): string {
  const d: string[] = [];
  sections.forEach((s) => {
    if (!s.startPoint || !s.endPoint) return;
    const p = s.startPoint; d.push(`M ${p.x} ${p.y}`);
    (s.bendPoints || []).forEach((b: any) => d.push(`L ${b.x} ${b.y}`));
    const q = s.endPoint; d.push(`L ${q.x} ${q.y}`);
  });
  return d.join(" ");
}

// ---------- React App ----------
export default function FamilyTreeApp() {
  const [doc, setDoc] = useState<TreeDoc>(() => demoDoc());
  const [layout, setLayout] = useState<any | null>(null);
  const [selected, setSelected] = useState<{ type: "person" | "union" | null; id: string | null }>({ type: null, id: null });
  const svgRef = useRef<SVGSVGElement | null>(null);

  // Layout recompute
  useEffect(() => {
    (async () => {
      const g = buildElkGraph(doc);
      const res = await elk.layout(g);
      setLayout(res);
    })();
  }, [doc]);

  // Handlers
  function addPerson(name?: string) {
    const id = uid("P");
    const p: Person = { id, name: name || `新成員 ${Object.keys(doc.persons).length + 1}` };
    setDoc((d) => ({ ...d, persons: { ...d.persons, [id]: p } }));
  }

  function addUnion(a?: PersonID, b?: PersonID) {
    const ids = Object.keys(doc.persons);
    if (!a) a = ids[0];
    if (!b) b = ids.find((x) => x !== a) || ids[0];
    const id = uid("U");
    setDoc((d) => ({ ...d, unions: { ...d.unions, [id]: { id, partners: [a!, b!], status: "married" } } }));
  }

  function addChild(unionId?: UnionID, existingChildId?: PersonID, newChildName?: string) {
    const mids = Object.keys(doc.unions);
    if (!mids.length) return;
    const u = unionId || mids[0];
    let childId = existingChildId;
    if (!childId) {
      const id = uid("P");
      childId = id;
      const p: Person = { id, name: newChildName || `新子女 ${doc.children.length + 1}` };
      setDoc((d) => ({ ...d, persons: { ...d.persons, [id]: p } }));
    }
    setDoc((d) => ({ ...d, children: [...d.children, { unionId: u!, childId: childId! }] }));
  }

  function removeSelected() {
    const sel = selected;
    if (!sel.type || !sel.id) return;
    if (sel.type === "person") {
      // Remove person, detach from unions & children
      setDoc((d) => {
        const persons = { ...d.persons }; delete persons[sel.id!];
        const unions = Object.fromEntries(Object.entries(d.unions).filter(([_, u]) => !u.partners.includes(sel.id!)));
        const children = d.children.filter((cl) => cl.childId !== sel.id! && (unions as any)[cl.unionId]);
        return { persons, unions, children } as TreeDoc;
      });
    } else if (sel.type === "union") {
      setDoc((d) => {
        const unions = { ...d.unions }; delete unions[sel.id!];
        const children = d.children.filter((cl) => cl.unionId !== sel.id!);
        return { ...d, unions, children } as TreeDoc;
      });
    }
    setSelected({ type: null, id: null });
  }

  function loadDemo() {
    setDoc(demoDoc());
    setSelected({ type: null, id: null });
  }

  function clearAll() {
    setDoc({ persons: {}, unions: {}, children: [] });
    setSelected({ type: null, id: null });
  }

  function downloadSVG() {
    const svg = svgRef.current;
    if (!svg) return;
    const serializer = new XMLSerializer();
    const src = serializer.serializeToString(svg);
    const blob = new Blob([src], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "family-tree.svg"; a.click();
    URL.revokeObjectURL(url);
  }

  function exportJSON() {
    const blob = new Blob([JSON.stringify(doc, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "family-tree.json"; a.click();
    URL.revokeObjectURL(url);
  }

  function importJSON(file: File) {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const t = JSON.parse(String(e.target?.result || "{}")) as TreeDoc;
        if (t && t.persons && t.unions && t.children) setDoc(t);
      } catch (err) {
        console.error(err);
      }
    };
    reader.readAsText(file);
  }

  // -- Derived lists for forms --
  const persons = Object.values(doc.persons);
  const unions = Object.values(doc.unions);

  // UI helpers
  const isSelected = (id: string, type: "person" | "union") => selected.type === type && selected.id === id;

  return (
    <div className="w-full h-full flex flex-col gap-3 p-4">
      <header className="flex flex-wrap items-center gap-2 justify-between">
        <h1 className="text-2xl font-semibold">Quick Family Tree — MVP</h1>
        <div className="flex flex-wrap gap-2">
          <button className="px-3 py-2 rounded-xl bg-slate-800 text-white" onClick={loadDemo}>載入示範</button>
          <button className="px-3 py-2 rounded-xl bg-slate-700 text-white" onClick={clearAll}>清空</button>
          <button className="px-3 py-2 rounded-xl bg-teal-700 text-white" onClick={() => addPerson()}>新增人物</button>
          <button className="px-3 py-2 rounded-xl bg-teal-700 text-white" onClick={() => addUnion()}>新增配偶/婚姻</button>
          <button className="px-3 py-2 rounded-xl bg-teal-700 text-white" onClick={() => addChild()}>新增子女</button>
          <button className="px-3 py-2 rounded-xl bg-rose-700 text-white" onClick={removeSelected}>刪除選取</button>
          <button className="px-3 py-2 rounded-xl bg-indigo-700 text-white" onClick={downloadSVG}>下載 SVG</button>
          <button className="px-3 py-2 rounded-xl bg-indigo-700 text-white" onClick={exportJSON}>匯出 JSON</button>
          <label className="px-3 py-2 rounded-xl bg-indigo-700 text-white cursor-pointer">
            匯入 JSON
            <input type="file" accept="application/json" className="hidden" onChange={(e) => {
              const f = e.target.files?.[0]; if (f) importJSON(f);
            }}/>
          </label>
        </div>
      </header>

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-9 rounded-2xl border border-slate-200 overflow-hidden bg-white">
          {/* Canvas */}
          <div className="w-full h-[720px] overflow-auto">
            {layout ? (
              <svg
                ref={svgRef}
                width={layout.width + MARGIN * 2}
                height={layout.height + MARGIN * 2}
                viewBox={`0 0 ${layout.width + MARGIN * 2} ${layout.height + MARGIN * 2}`}
              >
                <g transform={`translate(${MARGIN},${MARGIN})`}>
                  {/* Edges */}
                  {(layout.edges || []).map((e: any) => (
                    <path
                      key={e.id}
                      d={pathFromSections(e.sections || [])}
                      fill="none"
                      stroke={theme.line}
                      strokeWidth={2}
                    />
                  ))}

                  {/* Nodes */}
                  {(layout.children || []).map((n: any) => {
                    const selPerson = isSelected(n.id, "person");
                    const selUnion = isSelected(n.id, "union");

                    // Is union node?
                    const isUnion = !!doc.unions[n.id as UnionID];

                    if (isUnion) {
                      const r = 5;
                      return (
                        <g key={n.id} transform={`translate(${n.x},${n.y})`}>
                          <rect
                            x={-r}
                            y={-r}
                            width={10}
                            height={10}
                            fill={theme.bg}
                            stroke={selUnion ? "#f97316" : theme.border}
                            strokeWidth={selUnion ? 3 : 2}
                            className="cursor-pointer"
                            onClick={() => setSelected({ type: "union", id: n.id })}
                          />
                        </g>
                      );
                    }

                    // Person node
                    const label = doc.persons[n.id]?.name ?? "?";
                    return (
                      <g key={n.id} transform={`translate(${n.x},${n.y})`}>
                        <rect
                          rx={16}
                          width={NODE_W}
                          height={NODE_H}
                          fill={theme.bg}
                          stroke={selPerson ? "#f97316" : theme.border}
                          strokeWidth={selPerson ? 3 : 2}
                          className="cursor-pointer shadow"
                          onClick={() => setSelected({ type: "person", id: n.id })}
                        />
                        <text
                          x={NODE_W / 2}
                          y={NODE_H / 2 + 5}
                          textAnchor="middle"
                          fontFamily="ui-sans-serif, system-ui, -apple-system"
                          fontSize={14}
                          fill={theme.fg}
                          className="select-none"
                        >
                          {label}
                        </text>
                      </g>
                    );
                  })}
                </g>
              </svg>
            ) : (
              <div className="p-8 text-slate-500">佈局計算中…</div>
            )}
          </div>
        </div>

        {/* Inspector / Forms */}
        <div className="col-span-3 space-y-4">
          <div className="rounded-2xl border p-4">
            <h2 className="font-semibold mb-2">快速新增</h2>
            <QuickForms doc={doc} onAddPerson={addPerson} onAddUnion={addUnion} onAddChild={addChild} />
          </div>

          <div className="rounded-2xl border p-4">
            <h2 className="font-semibold mb-2">選取資訊</h2>
            {!selected.type ? (
              <div className="text-slate-500">未選取任何節點</div>
            ) : selected.type === "person" ? (
              <PersonInspector doc={doc} setDoc={setDoc} pid={selected.id!} />
            ) : (
              <UnionInspector doc={doc} setDoc={setDoc} uid={selected.id!} />
            )}
            <div className="mt-3">
              <button className="px-3 py-2 rounded-xl bg-rose-600 text-white" onClick={removeSelected}>
                刪除此節點
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function QuickForms({
  doc,
  onAddPerson,
  onAddUnion,
  onAddChild,
}: {
  doc: TreeDoc;
  onAddPerson: (name?: string) => void;
  onAddUnion: (a?: PersonID, b?: PersonID) => void;
  onAddChild: (unionId?: UnionID, existingChildId?: PersonID, newChildName?: string) => void;
}) {
  const [name, setName] = useState("");
  const [a, setA] = useState<string>("");
  const [b, setB] = useState<string>("");
  const [mid, setMid] = useState<string>("");
  const [childName, setChildName] = useState("");

  const persons = Object.values(doc.persons);
  const unions = Object.values(doc.unions);

  useEffect(() => {
    if (!a && persons[0]) setA(persons[0].id);
    if (!b && persons[1]) setB(persons[1].id);
    if (!mid && unions[0]) setMid(unions[0].id);
  }, [doc]);

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input className="border rounded-xl px-3 py-2 w-full" placeholder="新人物姓名"
               value={name} onChange={(e) => setName(e.target.value)} />
        <button className="px-3 py-2 rounded-xl bg-teal-700 text-white" onClick={() => { onAddPerson(name || undefined); setName(""); }}>新增</button>
      </div>

      <div className="flex gap-2 items-center">
        <select className="border rounded-xl px-3 py-2 w-full" value={a} onChange={(e) => setA(e.target.value)}>
          {persons.map((p) => (<option key={p.id} value={p.id}>{p.name}</option>))}
        </select>
        <span>×</span>
        <select className="border rounded-xl px-3 py-2 w-full" value={b} onChange={(e) => setB(e.target.value)}>
          {persons.filter((p) => p.id !== a).map((p) => (<option key={p.id} value={p.id}>{p.name}</option>))}
        </select>
        <button className="px-3 py-2 rounded-xl bg-teal-700 text-white" onClick={() => onAddUnion(a as PersonID, b as PersonID)}>成婚</button>
      </div>

      <div className="flex gap-2 items-center">
        <select className="border rounded-xl px-3 py-2 w-full" value={mid} onChange={(e) => setMid(e.target.value)}>
          {unions.map((u) => {
            const [pa, pb] = u.partners; return (
              <option key={u.id} value={u.id}>{doc.persons[pa]?.name} ↔ {doc.persons[pb]?.name}</option>
            );
          })}
        </select>
        <input className="border rounded-xl px-3 py-2 w-full" placeholder="新子女姓名"
               value={childName} onChange={(e) => setChildName(e.target.value)} />
        <button className="px-3 py-2 rounded-xl bg-teal-700 text-white" onClick={() => { onAddChild(mid as UnionID, undefined, childName || undefined); setChildName(""); }}>加子女</button>
      </div>
    </div>
  );
}

function PersonInspector({ doc, setDoc, pid }: { doc: TreeDoc; setDoc: any; pid: string }) {
  const p = doc.persons[pid];
  if (!p) return <div className="text-slate-500">人物不存在</div>;
  return (
    <div className="space-y-2">
      <div className="text-sm text-slate-500">人物 ID：{pid}</div>
      <label className="block text-sm">姓名</label>
      <input className="border rounded-xl px-3 py-2 w-full" value={p.name}
             onChange={(e) => setDoc((d: TreeDoc) => ({ ...d, persons: { ...d.persons, [pid]: { ...p, name: e.target.value } } }))} />
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-sm">出生</label>
          <input className="border rounded-xl px-3 py-2 w-full" value={p.birth || ""}
                 onChange={(e) => setDoc((d: TreeDoc) => ({ ...d, persons: { ...d.persons, [pid]: { ...p, birth: e.target.value } } }))} />
        </div>
        <div>
          <label className="block text-sm">逝世</label>
          <input className="border rounded-xl px-3 py-2 w-full" value={p.death || ""}
                 onChange={(e) => setDoc((d: TreeDoc) => ({ ...d, persons: { ...d.persons, [pid]: { ...p, death: e.target.value } } }))} />
        </div>
      </div>
      <label className="block text-sm">備註</label>
      <textarea className="border rounded-xl px-3 py-2 w-full" rows={3} value={p.note || ""}
                onChange={(e) => setDoc((d: TreeDoc) => ({ ...d, persons: { ...d.persons, [pid]: { ...p, note: e.target.value } } }))} />
    </div>
  );
}

function UnionInspector({ doc, setDoc, uid }: { doc: TreeDoc; setDoc: any; uid: string }) {
  const u = doc.unions[uid];
  if (!u) return <div className="text-slate-500">婚姻不存在</div>;
  const [a, b] = u.partners;
  const nameA = doc.persons[a]?.name || "?";
  const nameB = doc.persons[b]?.name || "?";
  return (
    <div className="space-y-2">
      <div className="text-sm text-slate-500">婚姻 ID：{uid}</div>
      <div className="text-slate-700">{nameA} ↔ {nameB}</div>
      <label className="block text-sm">狀態</label>
      <select className="border rounded-xl px-3 py-2" value={u.status || "married"}
              onChange={(e) => setDoc((d: TreeDoc) => ({ ...d, unions: { ...d.unions, [uid]: { ...u, status: e.target.value as any } } }))}>
        <option value="married">已婚</option>
        <option value="cohabiting">同居</option>
        <option value="divorced">離婚</option>
        <option value="separated">分居</option>
        <option value="widowed">喪偶</option>
      </select>

      <div>
        <label className="block text-sm mb-1">在此婚姻下新增子女</label>
        <button className="px-3 py-2 rounded-xl bg-teal-700 text-white"
                onClick={() => {
                  const id = uid("P");
                  setDoc((d: TreeDoc) => {
                    const child: Person = { id, name: `新子女 ${d.children.length + 1}` };
                    return {
                      ...d,
                      persons: { ...d.persons, [id]: child },
                      children: [...d.children, { unionId: uid, childId: id }],
                    };
                  });
                }}>
          新增子女
        </button>
      </div>
    </div>
  );
}
