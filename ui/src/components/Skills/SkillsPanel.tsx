/**
 * SkillsPanel.tsx
 *
 * Browse, read, add, and remove Aloha's skills from the box's own web app.
 * Built-in skills ship with Aloha; skills you add are saved to the box and the
 * agent uses them immediately (they land in {data_dir}/skills/).
 */

import React, { useEffect, useMemo, useState } from "react";
import {
  getSkills, getSkillMarkdown, addSkill, deleteSkill, SkillInfo,
} from "../../api/client";

// Tiny markdown → HTML (headings, bold, inline code, lists, paragraphs).
function mdToHtml(md: string): string {
  const esc = (s: string) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c] as string));
  const inline = (t: string) =>
    esc(t).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  const lines = md.replace(/^---[\s\S]*?---\s*/, "").split("\n");
  let html = "", list: string | null = null;
  const flush = () => { if (list) { html += `</${list}>`; list = null; } };
  for (const raw of lines) {
    const line = raw.trimEnd();
    let m: RegExpMatchArray | null;
    if ((m = line.match(/^(#{1,3})\s+(.*)/))) { flush(); const n = m[1].length; html += `<h${n}>${inline(m[2])}</h${n}>`; }
    else if ((m = line.match(/^\s*\d+\.\s+(.*)/))) { if (list !== "ol") { flush(); list = "ol"; html += "<ol>"; } html += `<li>${inline(m[1])}</li>`; }
    else if ((m = line.match(/^\s*[-*]\s+(.*)/))) { if (list !== "ul") { flush(); list = "ul"; html += "<ul>"; } html += `<li>${inline(m[1])}</li>`; }
    else if (line === "") { flush(); }
    else { flush(); html += `<p>${inline(line)}</p>`; }
  }
  flush();
  return html;
}

type Mode = { kind: "list" } | { kind: "view"; skill: SkillInfo } | { kind: "new" };

export function SkillsPanel({ onClose }: { onClose: () => void }): React.ReactElement {
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [q, setQ] = useState("");
  const [mode, setMode] = useState<Mode>({ kind: "list" });
  const [md, setMd] = useState<string>("");
  const [err, setErr] = useState("");

  // new-skill editor
  const [newName, setNewName] = useState("");
  const [newBody, setNewBody] = useState("");
  const [saving, setSaving] = useState(false);

  async function refresh() {
    try { setSkills(await getSkills()); } catch { setErr("Couldn't load skills."); }
  }
  useEffect(() => { refresh(); }, []);

  const filtered = useMemo(() => {
    const f = q.toLowerCase();
    return skills.filter((s) => !f || (s.name + s.description + s.category).toLowerCase().includes(f));
  }, [skills, q]);

  async function open(skill: SkillInfo) {
    setMode({ kind: "view", skill });
    setMd("");
    try { setMd(await getSkillMarkdown(skill.name)); } catch { setMd("Could not load this skill."); }
  }

  async function save() {
    setErr(""); setSaving(true);
    try {
      await addSkill(newName, newBody);
      setNewName(""); setNewBody("");
      await refresh();
      setMode({ kind: "list" });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not save skill.");
    } finally { setSaving(false); }
  }

  async function remove(skill: SkillInfo) {
    if (!confirm(`Delete skill "${skill.name}"? This can't be undone.`)) return;
    try { await deleteSkill(skill.name); await refresh(); setMode({ kind: "list" }); }
    catch (e) { setErr(e instanceof Error ? e.message : "Could not delete."); }
  }

  const field = "w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500";

  return (
    <div className="fixed inset-0 z-40 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm"
         onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="w-full sm:max-w-3xl h-[86vh] sm:h-[80vh] flex flex-col bg-slate-900 border border-slate-700 rounded-t-2xl sm:rounded-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-2">
            {mode.kind !== "list" && (
              <button onClick={() => { setMode({ kind: "list" }); setErr(""); }}
                      className="text-slate-400 hover:text-slate-200 text-sm">← back</button>
            )}
            <h2 className="text-lg font-semibold text-slate-100">
              {mode.kind === "view" ? mode.skill.name : mode.kind === "new" ? "New skill" : "📚 Skills"}
            </h2>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 text-xl leading-none">✕</button>
        </div>

        {err && <div className="mx-5 mt-3 rounded-lg bg-red-900/30 border border-red-700/40 px-4 py-2 text-sm text-red-300">{err}</div>}

        {/* LIST */}
        {mode.kind === "list" && (
          <>
            <div className="flex items-center gap-3 px-5 py-3 shrink-0">
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search skills…"
                     className={`${field} max-w-xs`} />
              <span className="text-xs text-slate-500">{filtered.length} skill{filtered.length === 1 ? "" : "s"}</span>
              <span className="flex-1" />
              <button onClick={() => { setErr(""); setMode({ kind: "new" }); }}
                      className="text-sm bg-sky-500 hover:bg-sky-400 text-white font-medium rounded-lg px-4 py-2">
                + New skill
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-5 pb-5 grid grid-cols-1 sm:grid-cols-2 gap-3 content-start">
              {filtered.map((s) => (
                <button key={s.name} onClick={() => open(s)}
                        className="text-left p-4 rounded-xl bg-slate-800 border border-slate-700 hover:border-sky-500 transition-colors">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] uppercase tracking-wide text-amber-400">{s.category}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${s.editable ? "bg-sky-500/20 text-sky-300" : "bg-slate-700 text-slate-400"}`}>
                      {s.editable ? "yours" : "built-in"}
                    </span>
                  </div>
                  <div className="mt-1.5 text-sm font-semibold text-slate-100">{s.name}</div>
                  <p className="text-xs text-slate-400 mt-0.5">{s.description}</p>
                </button>
              ))}
            </div>
          </>
        )}

        {/* VIEW */}
        {mode.kind === "view" && (
          <div className="flex-1 overflow-y-auto px-6 py-5">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-[11px] uppercase tracking-wide text-amber-400">{mode.skill.category}</span>
              {mode.skill.editable && (
                <button onClick={() => remove(mode.skill)}
                        className="ml-auto text-xs text-red-400 hover:text-red-300">delete</button>
              )}
            </div>
            <div className="skill-md text-sm text-slate-300 leading-relaxed"
                 dangerouslySetInnerHTML={{ __html: mdToHtml(md) }} />
          </div>
        )}

        {/* NEW */}
        {mode.kind === "new" && (
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
            <p className="text-sm text-slate-400">
              A skill is a short markdown playbook. Save it and the agent can use it right away
              (it's stored on this box).
            </p>
            <input value={newName} onChange={(e) => setNewName(e.target.value)}
                   placeholder="Skill name (e.g. set-up-vacation-mode)" className={field} />
            <textarea value={newBody} onChange={(e) => setNewBody(e.target.value)} rows={14}
                      placeholder={"---\nname: set-up-vacation-mode\ndescription: ...\ncategory: operate\n---\n\n1. First, ...\n2. Then, ..."}
                      className={`${field} font-mono text-[13px]`} />
            <div className="flex justify-end gap-2">
              <button onClick={() => setMode({ kind: "list" })} className="text-sm text-slate-400 hover:text-slate-200 px-4 py-2">Cancel</button>
              <button onClick={save} disabled={saving || !newName.trim() || !newBody.trim()}
                      className="text-sm bg-sky-500 hover:bg-sky-400 disabled:opacity-40 text-white font-medium rounded-lg px-5 py-2">
                {saving ? "Saving…" : "Save skill"}
              </button>
            </div>
          </div>
        )}
      </div>
      <style>{`
        .skill-md h1,.skill-md h2,.skill-md h3{color:#f1f5f9;font-weight:600;margin:14px 0 6px}
        .skill-md h1{font-size:19px}.skill-md h2{font-size:17px}.skill-md h3{font-size:15px}
        .skill-md p{margin:7px 0}
        .skill-md ol,.skill-md ul{margin:7px 0 7px 20px}.skill-md ol{list-style:decimal}.skill-md ul{list-style:disc}
        .skill-md li{margin:3px 0}
        .skill-md code{background:#0b1220;color:#7dd3fc;padding:1px 5px;border-radius:5px;font-size:12px}
        .skill-md strong{color:#f1f5f9}
      `}</style>
    </div>
  );
}
