# -*- coding: utf-8 -*-
"""把本机所有 DSH 会话并成一份"对话流水"——会话只是嘴，工作区才是本体。

做的事：
  1. 扫 ~/.dsh/sessions 下每个会话的落盘文件（v3 的 session.jsonl.zstd 和 v4 的 session.v4.jsonl.zstd 都认）；
  2. 只取 user/message 和 assistant/message 两种事件；注入的系统提示、压缩存档、模型切换通知一律丢掉；
  3. 按天追加到 <out_dir>/流水/YYYY-MM-DD.jsonl，同一条（谁+分钟+前 120 字）只写一次；
  4. 每个文件读到哪儿记在 <out_dir>/_state.json，下次只接新的。

第一次见到的会话从「现在 - bootstrap_hours 小时」开始接，不把几个月前的旧账全翻出来。

用法：
    python merge_flow.py            # 正常并入
    python merge_flow.py --dry-run  # 只报数，不写文件
"""
import argparse
import glob
import io
import json
import os
import sys
import time

try:
    import zstandard as zstd
except ImportError:
    sys.exit("缺 zstandard：pip install zstandard")

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "config.json")


def load_cfg():
    with io.open(CFG, encoding="utf-8") as f:
        c = json.load(f)
    c["sessions_dir"] = os.path.expanduser(c.get("sessions_dir") or r"~/.dsh/sessions")
    c["out_dir"] = os.path.expanduser(c.get("out_dir") or "~/dsh-body")
    return c


def load_state(p):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return {}


def save_state(p, st):
    io.open(p, "w", encoding="utf-8").write(json.dumps(st, ensure_ascii=False, indent=1))


def text_of(content):
    """只取真正说出口的文字；reasoning（内心推演）和工具调用都不进流水。"""
    if isinstance(content, str):
        return content.strip()
    out = []
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            kind = part.get("type")
            if kind == "text" and part.get("text"):
                out.append(str(part["text"]))
            elif kind is None and part.get("text"):
                out.append(str(part["text"]))
    return "\n".join(out).strip()


def is_noise(txt):
    head = txt[:120]
    if head.startswith("<system-reminder>"):
        return True
    if head.startswith("Current runtime context.") and len(txt) > 200:
        return True
    if head.startswith("[model changed:"):
        return True
    if "automatically generated checkpoint" in txt[:400]:
        return True
    if head.startswith("<environment_context>"):
        return True
    if head.startswith("Time sampled while preparing turn"):
        return True
    if "Browser time zone for this request" in txt[:200]:
        return True
    return False


def read_events(path):
    with io.open(path, "rb") as fh:
        data = io.TextIOWrapper(zstd.ZstdDecompressor().stream_reader(fh),
                                encoding="utf-8", errors="ignore").read()
    rows = []
    title = ""
    for line in data.splitlines():
        if not line.strip():
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        t = o.get("type")
        if t == "session/title":
            title = ((o.get("data") or {}).get("title") or "")[:60]
        if t not in ("user/message", "assistant/message"):
            continue
        ts = float(o.get("time") or 0) / 1000.0
        if ts <= 0:
            continue
        d = o.get("data") or {}
        if t == "user/message":
            who, txt = "user", text_of(d.get("content"))
        else:
            msg = d.get("message") or {}
            who, txt = "assistant", text_of(msg.get("content"))
        if len(txt) < 2 or is_noise(txt):
            continue
        rows.append({"ts": ts, "who": who, "text": txt, "title": title})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    cfg = load_cfg()
    sess, out = cfg["sessions_dir"], cfg["out_dir"]
    if not os.path.isdir(sess):
        sys.exit(f"没找到会话目录：{sess}（打开过一次 DSH 才会生成）")
    flow_dir = os.path.join(out, "流水")
    state_p = os.path.join(out, "_state.json")
    os.makedirs(flow_dir, exist_ok=True)
    st = load_state(state_p)

    files = glob.glob(os.path.join(sess, "**", "session.jsonl.zstd"), recursive=True)
    files += glob.glob(os.path.join(sess, "**", "session.v4.jsonl.zstd"), recursive=True)
    boot = time.time() - float(cfg.get("bootstrap_hours", 3)) * 3600

    added = 0
    for path in files:
        sid = os.path.basename(os.path.dirname(path))
        if path not in st:
            st[path] = boot
        last = float(st[path])
        try:
            rows = read_events(path)
        except Exception as e:
            print(f"  解不开 {sid}: {e!r}"[:120])
            continue
        rows = [r for r in rows if r["ts"] > last]
        if not rows:
            continue
        rows.sort(key=lambda r: r["ts"])
        by_day = {}
        for r in rows:
            day = time.strftime("%Y-%m-%d", time.localtime(r["ts"]))
            by_day.setdefault(day, []).append({
                "at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["ts"])),
                "session": sid[-8:],
                "title": r["title"],
                "who": r["who"],
                "text": r["text"][:1500],
            })
        for day, items in by_day.items():
            p = os.path.join(flow_dir, day + ".jsonl")
            key = lambda r: (r["who"], r["at"][:16], r["text"][:120])
            seen = set()
            if os.path.exists(p):
                for line in io.open(p, encoding="utf-8"):
                    try:
                        seen.add(key(json.loads(line)))
                    except Exception:
                        pass
            if a.dry_run:
                added += sum(1 for it in items if key(it) not in seen)
            else:
                with io.open(p, "a", encoding="utf-8") as out:
                    for it in items:
                        if key(it) in seen:
                            continue
                        seen.add(key(it))
                        out.write(json.dumps(it, ensure_ascii=False) + "\n")
                        added += 1
        st[path] = max(r["ts"] for r in rows)

    if not a.dry_run:
        save_state(state_p, st)
    print(f"{'[dry-run] 会并入' if a.dry_run else '并入'} {added} 条 → {flow_dir}")


if __name__ == "__main__":
    main()
