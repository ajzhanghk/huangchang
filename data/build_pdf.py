#!/usr/bin/env python3
"""Build a XeLaTeX PDF of the 黄裳行旅散文集 editorial plan.

IMPORTANT — copyright boundary:
  黄裳 (容鼎昌, 1919–2012) is in copyright (until 2062). This document
  deliberately contains NO protected full texts. It compiles only the
  project's own copyright-safe editorial materials: the anthology
  structure, the 篇目 index with ORIGINAL <=200-char summaries, the
  travel timeline, source bibliography, editorial principles, preface
  draft, section introductions, and the verification/gap lists.

Pipeline:
  - Reads data/huangshang_essays.json for the data-driven sections
    (essay index + summaries, collections, needs_verification, gaps).
  - Reads the Markdown editorial docs (outline/, notes/) and converts
    them with a light Markdown->LaTeX converter.
  - Emits build/huangshang_anthology_plan.tex and runs xelatex twice
    (for the table of contents).

Usage:
  python data/build_pdf.py
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "huangshang_essays.json"
BUILD_DIR = ROOT / "build"
TEX_NAME = "huangshang_anthology_plan"

SECTION_LABELS = {
    0: "附录 / 序跋",
    1: "蜀道与战时中国",
    2: "美国兵与异国战争经验",
    3: "金陵旧梦",
    4: "江南行旅",
    5: "北平与旧都余韵",
    6: "山川、古迹与历史残影",
    7: "书肆、旧书与纸上行旅",
    8: "人物途中",
}

# Chinese ordinal for the section heading so the generated 篇目总表 matches
# the outline (outline/new_anthology_outline.md uses 第一辑…第八辑, not 第1辑).
CN_NUM = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八"}

INCLUSION_MARK = {"必收": "★必收", "可选": "○可选", "资料库": "·资料库"}

# Glyphs that xeCJK routes to the body font (which lacks them) before
# newunicodechar can act -> normalize to forms the body font renders.
SYMBOL_FIX = {
    "⚠": "",            # drop; bold 「重要更正」 carries the emphasis
    "–": "—",           # en dash -> em dash (body font has U+2014)
    "Ⅰ": "I", "Ⅱ": "II", "Ⅲ": "III", "Ⅳ": "IV", "Ⅴ": "V",
    "Ⅵ": "VI", "Ⅶ": "VII", "Ⅷ": "VIII", "Ⅸ": "IX", "Ⅹ": "X",
    "①": "（1）", "②": "（2）", "③": "（3）", "④": "（4）", "⑤": "（5）",
    "⑥": "（6）", "⑦": "（7）", "⑧": "（8）", "⑨": "（9）",
}


# --------------------------------------------------------------------------- #
# LaTeX escaping + inline Markdown
# --------------------------------------------------------------------------- #
def esc(s: str) -> str:
    for bad, good in SYMBOL_FIX.items():
        s = s.replace(bad, good)
    out = []
    for ch in s:
        if ch == "\\":
            out.append(r"\textbackslash{}")
        elif ch in "&%$#_{}":
            out.append("\\" + ch)
        elif ch == "~":
            out.append(r"\textasciitilde{}")
        elif ch == "^":
            out.append(r"\textasciicircum{}")
        else:
            out.append(ch)
    return "".join(out)


_INLINE = re.compile(
    r"\^\[([^\]]*)\]"         # group(1): ^[inline footnote]
    r"|`([^`]*)`"              # group(2): `code`
    r"|\*\*([^*]+?)\*\*"       # group(3): **bold**
    r"|\*([^*\n]+?)\*"         # group(4): *italic*
)


def inline(s: str) -> str:
    """Convert `code`, **bold**, *italic*, ^[footnote], escaping everything else."""
    out, pos = [], 0
    for m in _INLINE.finditer(s):
        if m.start() > pos:
            out.append(esc(s[pos:m.start()]))
        if m.group(1) is not None:
            out.append(r"\footnote{" + esc(m.group(1)) + "}")
        elif m.group(2) is not None:
            out.append(r"\texttt{" + esc(m.group(2)) + "}")
        elif m.group(3) is not None:
            out.append(r"\textbf{" + esc(m.group(3)) + "}")
        else:
            out.append(r"\textit{" + esc(m.group(4)) + "}")
        pos = m.end()
    if pos < len(s):
        out.append(esc(s[pos:]))
    return "".join(out)


# --------------------------------------------------------------------------- #
# Markdown -> LaTeX (block level)
# --------------------------------------------------------------------------- #
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
LIST_ITEM = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")


def _is_table_sep(line: str) -> bool:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{1,}:?", c or "") for c in cells)


def _heading_cmd(level: int, text: str) -> str:
    level = max(1, level)
    cmd = {1: "section", 2: "subsection", 3: "subsubsection"}.get(level, "paragraph")
    return f"\\{cmd}{{{inline(text)}}}\n"


def _render_table(rows: list[str]) -> str:
    parsed = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    if len(parsed) >= 2 and _is_table_sep(rows[1]):
        header, body = parsed[0], parsed[2:]
    else:
        header, body = parsed[0], parsed[1:]
    ncol = len(header)
    size = r"\footnotesize" if ncol <= 3 else (r"\scriptsize" if ncol == 4 else r"\tiny")
    colspec = "@{}" + "X" * ncol + "@{}"
    out = ["\\begin{center}", size,
           f"\\begin{{tabularx}}{{\\linewidth}}{{{colspec}}}", "\\toprule"]
    out.append(" & ".join(r"\textbf{" + inline(c) + "}" for c in header) + r" \\")
    out.append("\\midrule")
    for row in body:
        row = (row + [""] * ncol)[:ncol]
        out.append(" & ".join(inline(c) for c in row) + r" \\")
    out += ["\\bottomrule", "\\end{tabularx}", "\\end{center}", ""]
    return "\n".join(out)


def _render_list(items: list[tuple[int, str, str]]) -> str:
    """items: list of (indent_level, marker_type 'ul'|'ol', text)."""
    out, stack = [], []  # stack of env names

    def close_to(depth):
        while len(stack) > depth:
            out.append("\\end{" + stack.pop() + "}")

    for level, kind, text in items:
        env = "itemize" if kind == "ul" else "enumerate"
        while len(stack) > level + 1:
            out.append("\\end{" + stack.pop() + "}")
        if len(stack) == level + 1 and stack[-1] != env:
            out.append("\\end{" + stack.pop() + "}")
        while len(stack) < level + 1:
            out.append("\\begin{" + env + "}")
            stack.append(env)
        out.append("\\item " + inline(text))
    close_to(0)
    return "\n".join(out) + "\n"


def md_to_latex(md: str, drop_first_h1: bool = False, heading_shift: int = 0) -> str:
    """Convert Markdown to LaTeX.

    heading_shift adjusts every heading's level (e.g. -1 promotes ## to
    \\section), for documents whose body starts at ## because # is the title.
    """
    lines = md.splitlines()
    out, i, dropped = [], 0, False
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            out.append("")
            i += 1
            continue
        # horizontal rule
        if line.strip() == "---":
            out.append("\\medskip\\hrule\\medskip")
            i += 1
            continue
        # heading
        m = HEADING.match(line)
        if m:
            level = len(m.group(1))
            if drop_first_h1 and level == 1 and not dropped:
                dropped = True
                i += 1
                continue
            out.append(_heading_cmd(level + heading_shift, m.group(2).strip()))
            i += 1
            continue
        # table
        if TABLE_ROW.match(line):
            block = []
            while i < len(lines) and TABLE_ROW.match(lines[i]):
                block.append(lines[i])
                i += 1
            out.append(_render_table(block))
            continue
        # blockquote
        if line.lstrip().startswith(">"):
            quote = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                quote.append(lines[i].lstrip()[1:].lstrip())
                i += 1
            out.append("\\begin{quote}\\small\\itshape")
            out.append(inline(" ".join(q for q in quote if q)))
            out.append("\\end{quote}")
            continue
        # list
        if LIST_ITEM.match(line):
            items = []
            while i < len(lines) and LIST_ITEM.match(lines[i]):
                mm = LIST_ITEM.match(lines[i])
                indent = len(mm.group(1).replace("\t", "  "))
                level = indent // 2
                kind = "ol" if mm.group(2)[0].isdigit() else "ul"
                items.append((level, kind, mm.group(3).strip()))
                i += 1
            out.append(_render_list(items))
            continue
        # paragraph
        para = []
        while i < len(lines) and lines[i].strip() and not (
            HEADING.match(lines[i]) or TABLE_ROW.match(lines[i])
            or LIST_ITEM.match(lines[i]) or lines[i].lstrip().startswith(">")
            or lines[i].strip() == "---"
        ):
            para.append(lines[i].strip())
            i += 1
        out.append(inline(" ".join(para)) + "\n")
    return "\n".join(out)


def read_md(rel: str, drop_first_h1: bool = False) -> str:
    """Each Markdown doc keeps its top H1 -> becomes its own \\section."""
    return md_to_latex((ROOT / rel).read_text(encoding="utf-8"),
                       drop_first_h1=drop_first_h1)


# --------------------------------------------------------------------------- #
# Data-driven sections (from JSON)
# --------------------------------------------------------------------------- #
def build_essay_index(data: dict) -> str:
    essays = data["essays"]
    out = [r"\section{篇目总表（含原创内容摘要）}",
           r"""\noindent\small 全表 %d 篇，按拟定辑次排列。每篇标注〔编号｜取舍｜置信〕。
摘要均为原创转述（≤200 字），\textbf{非原文复制}；篇名、年代、出处凡未坐实者标「待核 / 推测」。\normalsize
\medskip""" % len(essays)]
    order = [n for n in range(1, 9)] + [0]
    for sec in order:
        items = sorted((e for e in essays if e.get("proposed_section") == sec),
                       key=lambda e: e["id"])
        # Section 1–8 always appear so the 篇目总表 mirrors the full 8-辑
        # outline; an empty 辑 is shown as 〔待补〕. The appendix (0) is only
        # emitted when it actually has entries.
        if not items and sec == 0:
            continue
        label = SECTION_LABELS.get(sec, f"辑{sec}")
        head = f"第{CN_NUM[sec]}辑　{label}" if sec else f"附录　{label}"
        count = f"（{len(items)} 篇）" if items else "（待补，暂无已录入篇目）"
        out.append(f"\\subsection{{{esc(head)}{count}}}")
        if not items:
            out.append(r"\noindent{\small\itshape 本辑篇目尚待逐书录入，"
                       r"参见目录方案与「已知缺口」。}\par\vspace{5pt}")
            continue
        for e in items:
            mark = INCLUSION_MARK.get(e.get("inclusion", ""), e.get("inclusion", ""))
            meta = f"［{e['id']}｜{mark}｜{e.get('confidence','')}］"
            line1 = (r"\noindent\textbf{《" + esc(e["title"]) + "》}"
                     + r"\,{\small " + esc(meta) + r"}\\")
            sub = (f"原收入：{e.get('original_collection','—')}"
                   f"　｜　年代：{e.get('approximate_year') or '待核'}"
                   f"　｜　地点：{e.get('place','—')}（{e.get('region','—')}）")
            line2 = r"{\small\itshape " + esc(sub) + r"}\\"
            line3 = inline(e.get("summary", ""))
            out.append(line1)
            out.append(line2)
            out.append(line3)
            out.append(r"\par\vspace{5pt}")
    return "\n".join(out)


def build_collections(data: dict) -> str:
    out = [r"\section{收录书目（书锚）与版本}",
           r"\noindent\small 本项目据以采辑的原始结集与全集本；版权均未失效，"
           r"仅作版本核校之用。\normalsize\medskip"]
    for c in data.get("collections", []):
        title = esc(c.get("title", ""))
        bits = []
        if c.get("publisher"):
            bits.append(c["publisher"])
        if c.get("year"):
            bits.append(str(c["year"]))
        if c.get("series"):
            bits.append(c["series"])
        meta = "，".join(bits)
        out.append(r"\noindent\textbf{《" + title + "》}"
                   + (r"\,{\small（" + esc(meta) + "）}" if meta else "") + r"\\")
        if c.get("note"):
            out.append(inline(c["note"]))
        if c.get("source_reference"):
            out.append(r"\\{\small\itshape 来源：" + esc(c["source_reference"]) + "}")
        out.append(r"\par\vspace{5pt}")
    return "\n".join(out)


def build_verification(data: dict) -> str:
    out = [r"\section{待核清单与已知缺口}"]
    nv = data.get("needs_verification", [])
    if nv:
        out.append(r"\subsection{待核清单（needs\_verification）}")
        out.append(r"\begin{itemize}")
        for item in nv:
            out.append(r"\item " + inline(item))
        out.append(r"\end{itemize}")
    gaps = data.get("gaps", [])
    if gaps:
        out.append(r"\subsection{已知缺口（gaps）}")
        out.append(r"\begin{itemize}")
        for item in gaps:
            out.append(r"\item " + inline(item))
        out.append(r"\end{itemize}")
    nr = data.get("not_recommended", [])
    if nr:
        out.append(r"\subsection{不宜收判例（not\_recommended）}")
        out.append(r"\begin{itemize}")
        for item in nr:
            t = item.get("title_or_type", "")
            r_ = item.get("reason", "")
            out.append(r"\item \textbf{" + esc(t) + "}　" + inline(r_))
        out.append(r"\end{itemize}")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Document assembly
# --------------------------------------------------------------------------- #
PREAMBLE = r"""\documentclass[UTF8,fontset=none,zihao=-4,a4paper]{ctexart}
\usepackage{geometry}
\geometry{margin=2.4cm}
\usepackage{xeCJK}
\usepackage{fontspec}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage[most]{tcolorbox}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=black,urlcolor=black,
  pdftitle={黄裳行旅散文集 重编方案},pdfauthor={重编项目}}

% --- CJK fonts (Linux: AR PL + WenQuanYi) ---
\setCJKmainfont{AR PL SungtiL GB}
\setCJKsansfont{WenQuanYi Zen Hei}
\setCJKmonofont{WenQuanYi Zen Hei Mono}
\setCJKfamilyfont{zhkai}{AR PL KaitiM GB}
\newcommand{\kai}{\CJKfamily{zhkai}}
% fallback family for rare CJK glyphs absent from the Sung body font
\setCJKfamilyfont{zhfb}{WenQuanYi Zen Hei}
\newcommand{\fb}{\CJKfamily{zhfb}}
\setmonofont{DejaVu Sans Mono}[Scale=0.9]

% --- route symbols missing from the Latin font through WenQuanYi ---
\usepackage{newunicodechar}
\newfontfamily\symbolfont{WenQuanYi Zen Hei}
\newunicodechar{★}{{\symbolfont\char"2605}}
\newunicodechar{○}{{\symbolfont\char"25CB}}
\newunicodechar{●}{{\symbolfont\char"25CF}}
\newunicodechar{·}{{\symbolfont\char"00B7}}
\newunicodechar{↔}{{\symbolfont\char"2194}}
\newunicodechar{→}{{\symbolfont\char"2192}}
\newunicodechar{←}{{\symbolfont\char"2190}}
\newunicodechar{≤}{{\symbolfont\char"2264}}
\newunicodechar{≥}{{\symbolfont\char"2265}}
\newunicodechar{–}{{\symbolfont\char"2013}}
\newunicodechar{※}{{\symbolfont\char"203B}}

\linespread{1.25}
\setlength{\parindent}{2em}
\setlist{itemsep=2pt,topsep=3pt,parsep=0pt}

% headings in sans (黑体)
\titleformat*{\section}{\Large\sffamily\bfseries}
\titleformat*{\subsection}{\large\sffamily\bfseries}
\titleformat*{\subsubsection}{\normalsize\sffamily\bfseries}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\sffamily 黄裳行旅散文集 · 重编方案}
\fancyhead[R]{\small\thepage}
\renewcommand{\headrulewidth}{0.3pt}

\begin{document}
\sloppy
"""

def title_page() -> str:
    return r"""
\begin{titlepage}
\centering
\vspace*{3cm}
{\sffamily\bfseries\fontsize{30}{36}\selectfont 黄裳行旅散文集}\\[6pt]
{\kai\Large 重编方案 · 篇目索引与编辑框架}\\[2.2cm]
{\large 一部新选本的结构、选目、导读与注释设计}\\[0.4cm]
{\large（编选研究工作稿）}\\[3cm]
{\large 黄裳（容鼎昌，1919--2012）行旅散文}\\[0.3cm]
{\large 以文史脉络重构 · 八辑结构}\\[2.5cm]
{\normalsize 2026 年 6 月}\\
\vfill
\begin{tcolorbox}[colback=gray!6,colframe=gray!55,boxrule=0.6pt,
  arc=2pt,left=10pt,right=10pt,top=8pt,bottom=8pt,width=0.92\linewidth]
\small
\textbf{版权与编例说明}\quad 黄裳作品仍在版权保护期内（作者 2012 年逝世，
存续至 2062 年）。本文档为\textbf{编选研究工作稿}，依法\textbf{不收录受版权保护的作品全文}；
所录为篇目索引、\textbf{原创内容摘要（≤200 字，非原文复制）}、版本来源、主题与地点标签、
行旅年表、辑目结构、导读与注释框架。必要引用只取短句并注出处；网络流传节选不作可靠底本。
正式出版前须取得版权方授权，并以原书或《黄裳集》核校全部篇目、年份与文字。
\end{tcolorbox}
\end{titlepage}
"""


def main() -> int:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    BUILD_DIR.mkdir(exist_ok=True)

    parts = [PREAMBLE, title_page(),
             r"\tableofcontents", r"\clearpage",
             r"\part{编选方案}",
             read_md("outline/volume_preface_draft.md"),
             read_md("notes/editorial_principles.md"),
             read_md("outline/new_anthology_outline.md"),
             read_md("outline/section_introductions.md"),
             r"\part{篇目、年表与资料}",
             build_essay_index(data),
             read_md("notes/timeline_draft.md"),
             read_md("notes/source_bibliography.md"),
             build_collections(data),
             build_verification(data),
             r"\end{document}", ""]

    tex = "\n\n".join(parts)
    # Route rare CJK glyphs missing from the Sung body font (e.g. 李昪/李璟 in
    # the 南唐二陵 summary) through the WenQuanYi fallback family.
    for ch in ("昪", "璟"):
        tex = tex.replace(ch, r"{\fb " + ch + "}")
    tex_path = BUILD_DIR / f"{TEX_NAME}.tex"
    tex_path.write_text(tex, encoding="utf-8")
    print(f"Wrote {tex_path}")

    for run in (1, 2):
        proc = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error",
             f"{TEX_NAME}.tex"],
            cwd=BUILD_DIR, capture_output=True, text=True,
        )
        if proc.returncode != 0:
            tail = proc.stdout[-3000:]
            print(f"xelatex run {run} FAILED:\n{tail}", file=sys.stderr)
            return 1
        print(f"xelatex run {run} OK")

    pdf = BUILD_DIR / f"{TEX_NAME}.pdf"
    print(f"\nPDF: {pdf} ({pdf.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
