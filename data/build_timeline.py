#!/usr/bin/env python3
"""Generate a Markdown timeline from huangshang_essays.json.

Outputs to stdout; redirect to notes/timeline_draft.md or similar:
  python data/build_timeline.py > notes/timeline_draft.md

Groups essays by approximate_year, sorted chronologically.
Essays with no year are collected in a 年份待核 section at the end.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

DATA_FILE = Path(__file__).parent / "huangshang_essays.json"


def sort_key(year_str: str) -> tuple:
    """Return a (decade, year) tuple for sorting approximate year strings."""
    # Extract leading 4-digit year if present
    m = re.search(r"(\d{4})", year_str)
    if m:
        return (int(m.group(1)), year_str)
    # Decade strings like "约1944—1946" → use 1944
    m2 = re.search(r"(\d{4})", year_str)
    if m2:
        return (int(m2.group(1)), year_str)
    return (9999, year_str)


def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    essays = data.get("essays", [])

    by_year: dict[str, list] = defaultdict(list)
    unknown: list = []

    for e in essays:
        year = (e.get("approximate_year") or "").strip()
        if not year or year in ("待核", "—"):
            unknown.append(e)
        else:
            by_year[year].append(e)

    lines = [
        "# 黄裳行旅年表",
        "",
        "> 由 `data/build_timeline.py` 自动生成，勿手工修改。",
        "> 仅含 `approximate_year` 有值的篇目；年份均待核，「确定」者另见 `data/huangshang_essays.json`。",
        "> 图例：★ 必收　○ 可选　· 资料库",
        "",
    ]

    for year in sorted(by_year.keys(), key=sort_key):
        items = sorted(by_year[year], key=lambda x: x.get("place", ""))
        lines.append(f"## {year}")
        lines.append("")
        for e in items:
            place = e.get("place", "—")
            title = e["title"]
            sec = e.get("proposed_section", "?")
            incl = e.get("inclusion", "")
            conf = e.get("confidence", "")
            tag = "★" if incl == "必收" else ("○" if incl == "可选" else "·")
            conf_tag = f"（{conf}）" if conf != "确定" else ""
            lines.append(f"- {tag} 【辑{sec}】**{title}** — {place}{conf_tag}")
        lines.append("")

    if unknown:
        lines.append("## 年份待核")
        lines.append("")
        for e in sorted(unknown, key=lambda x: x.get("title", "")):
            place = e.get("place", "—")
            title = e["title"]
            sec = e.get("proposed_section", "?")
            incl = e.get("inclusion", "")
            tag = "★" if incl == "必收" else ("○" if incl == "可选" else "·")
            lines.append(f"- {tag} 【辑{sec}】**{title}** — {place}")
        lines.append("")

    # Summary counts
    total = len(essays)
    by_sec: dict[int, int] = defaultdict(int)
    for e in essays:
        by_sec[e.get("proposed_section", 0)] += 1

    lines += [
        "---",
        "",
        "## 各辑篇目统计",
        "",
        f"总计 {total} 篇",
        "",
    ]
    for sec in sorted(by_sec.keys()):
        label = {
            0: "附录/序跋",
            1: "蜀道与战时中国",
            2: "美国兵与异国战争经验",
            3: "金陵旧梦",
            4: "江南行旅",
            5: "北平与旧都余韵",
            6: "山川、古迹与历史残影",
            7: "书肆、旧书与纸上行旅",
            8: "人物途中",
        }.get(sec, f"辑{sec}")
        lines.append(f"- 第{sec}辑 {label}：{by_sec[sec]} 篇")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
