# -*- coding: utf-8 -*-
"""由流水写一份「我现在是什么样」的开场简报，给新会话第一眼看。

不调任何模型：把最近两天的对话、最近的记忆按时间铺开，就是一个够用的开场。
想要"更有人的口气"，可以自己接一个模型改写它——但那份是可选件，不接也能用。

产出：<out_dir>/状态.md
"""
import glob
import io
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def cfg():
    with io.open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
        c = json.load(f)
    c["out_dir"] = os.path.expanduser(c.get("out_dir") or "~/dsh-body")
    c["sessions_dir"] = os.path.expanduser(c.get("sessions_dir") or "~/.dsh/sessions")
    return c


def recent_flow(out_dir, days=2, limit=40):
    rows = []
    for i in range(days):
        day = time.strftime("%Y-%m-%d", time.localtime(time.time() - i * 86400))
        p = os.path.join(out_dir, "流水", day + ".jsonl")
        if not os.path.exists(p):
            continue
        for line in io.open(p, encoding="utf-8"):
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    rows.sort(key=lambda r: r.get("at", ""))
    return rows[-limit:]


def recent_memory(home, limit=15):
    """有 fish-memory（记忆插件）就顺一批出来；没有就跳过。"""
    texts = []
    for p in glob.glob(os.path.join(home, ".dsh", "fish-memory", "*.json")):
        try:
            data = json.load(io.open(p, encoding="utf-8"))
        except Exception:
            continue
        items = data if isinstance(data, list) else data.get("memories") or data.get("items") or []
        for it in items if isinstance(items, list) else []:
            if isinstance(it, dict) and it.get("text"):
                texts.append((it.get("at") or "", str(it["text"])))
    texts.sort()
    return [t for _, t in texts[-limit:]]


def main():
    c = cfg()
    out = c["out_dir"]
    os.makedirs(out, exist_ok=True)
    rows = recent_flow(out)
    mems = recent_memory(os.path.expanduser("~"))
    lines = ["# 我现在是什么样", "", f"更新时间：{time.strftime('%Y-%m-%d %H:%M')}", ""]
    if not rows and not mems:
        lines.append("（还没有流水。先在任意会话里说几句话，五分钟后再来看。）")
    if rows:
        lines.append("## 最近的对话（所有会话并在一起）")
        lines.append("")
        for r in rows:
            lines.append(f"- [{r.get('at','')[5:16]}] [{r.get('session','')}] {r.get('who','')}：{r.get('text','')[:160]}")
        lines.append("")
    if mems:
        lines.append("## 最近的记忆")
        lines.append("")
        for t in mems:
            lines.append(f"- {t[:160]}")
        lines.append("")
    path = os.path.join(out, "状态.md")
    io.open(path, "w", encoding="utf-8").write("\n".join(lines))
    print(f"写了 {path}（{len(rows)} 条对话 / {len(mems)} 条记忆）")


if __name__ == "__main__":
    main()
