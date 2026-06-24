#!/usr/bin/env python3
"""Assemble a FULL-LENGTH personal reading edition of 黄裳行旅散文集.

COPYRIGHT / SCOPE
-----------------
黄裳 (容鼎昌, 1919–2012) is in copyright (until 2062). This script ships
with NO 黄裳 text and never fetches any. It only typesets plain-text files
that YOU place in `texts/<essay-id>.txt` — i.e. text you digitize (OCR or
typing) from books you personally own, for personal use. Do not redistribute
the resulting PDF.

How it works
------------
  - Reads data/huangshang_essays.json for the running order and per-essay
    metadata (title, collection, year, place, section).
  - For each essay, looks for texts/<id>.txt (UTF-8).
      * present -> typesets the full text you provided.
      * absent  -> inserts a 「正文待录入」 placeholder + the editorial summary,
                   so the book builds at any stage of completion.
  - Emits build/huangshang_anthology_full.tex and runs xelatex twice.

Text file conventions (texts/<id>.txt)
  - UTF-8, plain text.
  - Blank line separates paragraphs. Single line breaks inside a paragraph
    are joined (so hard-wrapped OCR output is fine).
  - A line that is exactly  ## 小标题  becomes a sub-heading within the essay
    (useful for multi-part pieces like 金陵杂记 / 印度小夜曲 / 昆明杂记).

Usage
  python data/build_book.py
"""

import json
import subprocess
import sys
from pathlib import Path

import build_pdf as bp  # reuse esc/inline/PREAMBLE/SECTION_LABELS/paths

TEXTS_DIR = bp.ROOT / "texts"
OUT = "huangshang_anthology_full"


def text_to_latex(raw: str) -> str:
    """Convert a user-supplied plain-text essay to LaTeX body."""
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    blocks = raw.split("\n\n")
    out = []
    for block in blocks:
        block = block.strip("\n")
        if not block.strip():
            continue
        lines = block.split("\n")
        # a lone "## heading" line -> sub-heading
        if len(lines) == 1 and lines[0].lstrip().startswith("## "):
            out.append(r"\subsection*{" + bp.esc(lines[0].lstrip()[3:].strip()) + "}")
            continue
        joined = " ".join(ln.strip() for ln in lines if ln.strip())
        out.append(bp.esc(joined) + r"\par")
    return "\n\n".join(out)


def title_page() -> str:
    return r"""
\begin{titlepage}
\centering
\vspace*{3cm}
{\sffamily\bfseries\fontsize{30}{36}\selectfont 黄裳行旅散文集}\\[6pt]
{\kai\Large 全本 · 个人阅读版}\\[2.2cm]
{\large 以文史脉络重构 · 八辑结构}\\[3cm]
{\large 黄裳（容鼎昌，1919--2012）著}\\[0.3cm]
{\large 据自藏原书录入 · 仅供个人阅读}\\[2.5cm]
{\normalsize 自用排印本}\\
\vfill
\begin{tcolorbox}[colback=gray!6,colframe=gray!55,boxrule=0.6pt,
  arc=2pt,left=10pt,right=10pt,top=8pt,bottom=8pt,width=0.92\linewidth]
\small
\textbf{个人使用声明}\quad 黄裳作品仍在版权保护期内（存续至 2062 年）。
本册正文系\textbf{使用者据本人自藏原书录入}，仅供\textbf{个人学习与阅读}，
\textbf{不得复制、传播或公开发行}。篇目编次、辑目与摘要为本重编项目所拟。
凡正文尚未录入者，以「正文待录入」占位并附编辑摘要。
\end{tcolorbox}
\end{titlepage}
"""


def main() -> int:
    data = json.loads(bp.DATA_FILE.read_text(encoding="utf-8"))
    bp.BUILD_DIR.mkdir(exist_ok=True)
    TEXTS_DIR.mkdir(exist_ok=True)

    essays = data["essays"]
    order = [n for n in range(1, 9)] + [0]

    parts = [bp.PREAMBLE, title_page(), r"\tableofcontents", r"\clearpage"]

    have = 0
    for sec in order:
        items = sorted((e for e in essays if e.get("proposed_section") == sec),
                       key=lambda e: e["id"])
        if not items:
            continue
        label = bp.SECTION_LABELS.get(sec, f"辑{sec}")
        head = f"第{sec}辑　{label}" if sec else f"附录　{label}"
        parts.append(r"\part{" + bp.esc(head) + "}")
        for e in items:
            parts.append(r"\section{《" + bp.esc(e["title"]) + "》}")
            sub = (f"原收入：{e.get('original_collection','—')}"
                   f"　｜　年代：{e.get('approximate_year') or '待核'}"
                   f"　｜　地点：{e.get('place','—')}")
            parts.append(r"{\small\itshape " + bp.esc(sub) + r"}\par\medskip")

            txt_file = TEXTS_DIR / f"{e['id']}.txt"
            if txt_file.exists() and txt_file.read_text(encoding="utf-8").strip():
                have += 1
                parts.append(text_to_latex(txt_file.read_text(encoding="utf-8")))
            else:
                parts.append(
                    r"\begin{quote}\small\itshape 〔正文待录入：请将你自藏原书中本篇文字"
                    r"保存为 \texttt{texts/" + e["id"] + r".txt}（UTF-8），"
                    r"重跑 \texttt{python data/build\_book.py} 即并入此版。"
                    r"以下为编辑摘要：〕\end{quote}")
                parts.append(bp.inline(e.get("summary", "")) + r"\par")
            parts.append(r"\bigskip")

    parts += [r"\end{document}", ""]
    tex_path = bp.BUILD_DIR / f"{OUT}.tex"
    tex_path.write_text("\n\n".join(parts), encoding="utf-8")
    print(f"Wrote {tex_path}")
    print(f"Essays with supplied full text: {have}/{len(essays)}")

    for run in (1, 2):
        proc = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"{OUT}.tex"],
            cwd=bp.BUILD_DIR, capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"xelatex run {run} FAILED:\n{proc.stdout[-3000:]}", file=sys.stderr)
            return 1
        print(f"xelatex run {run} OK")

    pdf = bp.BUILD_DIR / f"{OUT}.pdf"
    print(f"\nPDF: {pdf} ({pdf.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
