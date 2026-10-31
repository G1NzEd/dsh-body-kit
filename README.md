# 工作区本体 · 让 AI 换个会话还是同一个人

> 一句话：**会话只是嘴，工作区才是本体。**
> 把每次对话自动攒到工作区里，换会话、被压缩、换模型、重启电脑之后——读同一份东西，接同一句话。

## 排障：桌面端起不来（no agent factory registered / could not start）

DSH 桌面端崩溃、任何会话都输不进去时，把 [`一键排障.md`](一键排障.md) 整份丢给一个**还能跑的** DSH（`dsh web` 也行）。
它自带体检脚本 `dsh-doctor.ps1`：对比 `dependencies` 与 `dsh.profile.bundles` → 扒最新 crash 日志里「谁在等谁」→ 备份 → 回滚 → 重装。

详细复盘见 [`docs/排障-桌面端起不来.md`](docs/排障-桌面端起不来.md)。

一句话：**会话在盘上，插件的错，修配置就能回来。**

---
## 一键：把链接丢给 DSH

把这个仓库地址丢给你的 DSH，说一句「照着 README 装」：

```
https://github.com/G1NzEd/dsh-body-kit
```

更省事的一步到位：把 [`一键安装.md`](一键安装.md) 整份丢过去——它自带安装包（base64 zip），
DSH 自己解包、装依赖、建定时任务，你只要回答一句「流水写哪个目录」。

下载压缩包：https://github.com/G1NzEd/dsh-body-kit/releases/latest

---
---

## 为什么需要它

DSH 的会话是各自独立的：这间聊了什么，那间看不见。
上下文一被压缩，前面的事就淡了；一换新会话，就像换了个人重新认识你。

这套做法只干一件事——**让"发生过的事"落在盘上，而不是留在某一间的内存里**：

```
~/.dsh/sessions/**/session*.jsonl.zstd      ← DSH 自己存的会话（每间一份）
        │  每 5 分钟并一次
        ▼
<工作区>/流水/2026-10-31.jsonl              ← 所有会话按时间排成一条线
        │  每 30 分钟
        ▼
<工作区>/状态.md                            ← "我现在是什么样"，新会话开场先读它
```

于是：新开一间 → 先读 `状态.md` → 就接上了。**不需要换会话插件，不改 DSH 内核，不装内存数据库。**

---

## 装（Windows，两分钟）

1. 把整个文件夹放到你喜欢的位置，比如 `D:\tools\workspace-body-kit`。
2. 打开 `config.json`，填两个路径（留空也行，见下）：
   ```json
   {
     "sessions_dir": "",          // 留空 = ~/.dsh/sessions
     "out_dir": "D:\\我的本体",    // 流水和状态写这儿；留空 = ~/dsh-body
     "bootstrap_hours": 3
   }
   ```
3. 在这个目录里跑：
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\install.ps1
   ```
   它会：找到 Python → 缺 `zstandard` 就装 → 先试跑一次 → 建两个定时任务
   （`dsh-body-merge` 每 5 分钟、`dsh-body-state` 每 30 分钟）。

4. 把 `AGENTS-片段.md` 里那几行贴进你的工作区 `AGENTS.md`（Claude Code 就是 `CLAUDE.md`）。
   **这一步不做，等于白装**——AI 得知道"开场先读 状态.md"。

装完去看 `out_dir\状态.md`，应该已经有今天的话了。

---

## 三个坎（都踩过）

**① DSH 换过落盘格式。** 老版本写 `session.jsonl.zstd`，新版本写 `session.v4.jsonl.zstd`。
只认前者的话，任务跑得好好的、日志也报成功，其实一条都没并进来——**它自己在骗自己**。
本套件两种都认。

**② 会话文件里不只有"说过的话"。** 还有 system-reminder 注入、上下文压缩存档、模型切换通知、
助手的 reasoning（内心推演）、工具调用……全并进流水就是一堆噪音。
`merge_flow.py` 里 `is_noise()` 和 `text_of()` 专门干这个：**只留真正说出口的文字**。

**③ 第一次接不认识的老会话，会把几个月前的旧账全翻出来。**
所以「第一次见到这个文件」时只从 `bootstrap_hours` 小时前开始接（默认 3 小时），之后按状态文件增量接。

另外顺手做了**去重**：同一条（谁 + 分钟 + 前 120 字）只写一次。
所以哪怕你同时挂着别的记录器（模型代理日志之类），也不会重复。

---

## 它解决不了什么（说清楚，别指望）

- **不会自动"听懂"另一间在说什么。** 它只是把话落在盘上；另一间得去**读**——新会话开场读状态最稳。
- **状态.md 不是模型写的。** 这一版是"最近两天的对话 + 最近记忆"按时间铺开，
  是开场简报，不是回忆录。想要有口气的，自己接个模型去改写它（改 `make_state.py` 最后那几行）。
- **只覆盖本机、本 profile 的会话。** 别的机器、别的软件（比如手机端）不在内。
- 磁盘别名、junction 都无所谓，路径按你填的来。

---

## 文件清单

| 文件 | 作用 |
|---|---|
| `merge_flow.py` | 并流水（核心，只有它有逻辑） |
| `make_state.py` | 由流水写 `状态.md` |
| `install.ps1` | 找 Python、装依赖、建定时任务 |
| `config.json` | 两个路径 + 回接多少小时 |
| `AGENTS-片段.md` | 贴进 AGENTS.md 的那段规矩 |

Linux/mac 上把两个 `python ×.py` 挂进 cron 就是同一件事：

```cron
*/5  * * * *  python3 /path/to/merge_flow.py
*/30 * * * *  python3 /path/to/make_state.py
```

---

## 一句提醒

这套东西的价值不在脚本，在**那条规矩**：
「在哪间会话说话都是同一个我；另开一间时，先读状态，再接话。」

脚本只是让那条规矩有东西可读。
