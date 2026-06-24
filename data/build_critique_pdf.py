#!/usr/bin/env python3
"""Build a publishable XeLaTeX PDF of the literary-criticism essay
《易代之眼：论黄裳文史游记的历史品味、文章趣味与风土人情》 (author: ajzhanghk).

IMPORTANT — copyright boundary:
  黄裳 (容鼎昌, 1919–2012) is in copyright (until 2062). This essay is an
  ORIGINAL piece of literary criticism. It quotes only short public-domain
  classical phrases and essay titles; it contains NO protected full text by
  黄裳. All characterizations of his prose are the critic's own paraphrase.

Pipeline:
  - Reads criticism/huangshang_wenshi_youji_lun.md
  - Reuses the Markdown->LaTeX converter and CJK font setup from build_pdf.py
  - Emits build/huangshang_wenshi_youji_lun.tex and runs xelatex twice
    (for the table of contents).

Usage:
  python data/build_critique_pdf.py
"""

import subprocess
import sys
from pathlib import Path

# Reuse the tested Markdown->LaTeX machinery from the plan builder.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_pdf import md_to_latex  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MD_FILE = ROOT / "criticism" / "huangshang_wenshi_youji_lun.md"
BUILD_DIR = ROOT / "build"
TEX_NAME = "huangshang_wenshi_youji_lun"

PREAMBLE = r"""\documentclass[UTF8,fontset=none,zihao=-4,a4paper]{ctexart}
\usepackage{geometry}
\geometry{margin=2.6cm}
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
  pdftitle={易代之眼——论黄裳文史游记},pdfauthor={ajzhanghk}}

% --- CJK fonts (Linux: AR PL + WenQuanYi) ---
\setCJKmainfont{AR PL SungtiL GB}
\setCJKsansfont{WenQuanYi Zen Hei}
\setCJKmonofont{WenQuanYi Zen Hei Mono}
\setCJKfamilyfont{zhkai}{AR PL KaitiM GB}
\newcommand{\kai}{\CJKfamily{zhkai}}
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

% --- rare CJK names (李昪/李璟) absent from the Sung body font.
%     newunicodechar cannot catch them (xeCJK claims CJK codepoints first),
%     so they are wrapped with \fb (WenQuanYi) by a post-pass in the builder. ---
\setCJKfamilyfont{zhfb}{WenQuanYi Zen Hei}
\newcommand{\fb}{\CJKfamily{zhfb}}

\linespread{1.32}
\setlength{\parindent}{2em}
\setlist{itemsep=2pt,topsep=3pt,parsep=0pt}

% headings in sans (黑体)
\titleformat*{\section}{\Large\sffamily\bfseries}
\titleformat*{\subsection}{\large\sffamily\bfseries}
\titleformat*{\subsubsection}{\normalsize\sffamily\bfseries}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\sffamily 易代之眼 · 论黄裳文史游记}
\fancyhead[R]{\small\thepage}
\renewcommand{\headrulewidth}{0.3pt}

\begin{document}
\sloppy
"""

TITLE_PAGE = r"""
\begin{titlepage}
\centering
\vspace*{3.2cm}
{\sffamily\bfseries\fontsize{28}{34}\selectfont 易代之眼}\\[10pt]
{\kai\Large 论黄裳文史游记的历史品味、文章趣味与风土人情}\\[2.6cm]
{\large 一篇关于黄裳「地点触发的文史随笔」的文艺评论}\\[3cm]
{\large 作者：ajzhanghk}\\[0.4cm]
{\normalsize 2026 年 6 月}\\
\vfill
\begin{tcolorbox}[colback=gray!6,colframe=gray!55,boxrule=0.6pt,
  arc=2pt,left=10pt,right=10pt,top=8pt,bottom=8pt,width=0.92\linewidth]
\small
\textbf{版权与引用说明}\quad 本文系\textbf{原创文艺评论}。黄裳（容鼎昌，1919--2012）
作品仍在版权保护期内（存续至 2062 年）；本文\textbf{不收录其受保护的作品全文}，
引述以公有领域的古人成句与篇名为主，凡涉黄裳本人文字者只取短句并归于评论性引用。
文中史实凡一时未据原书坐实者，以「据其文／疑／约」提示，严格标注见本项目数据库
\texttt{data/huangshang\_essays.json}。
\end{tcolorbox}
\end{titlepage}
"""


def main() -> int:
    if not MD_FILE.exists():
        print(f"Missing essay: {MD_FILE}", file=sys.stderr)
        return 1
    BUILD_DIR.mkdir(exist_ok=True)

    body = md_to_latex(MD_FILE.read_text(encoding="utf-8"), drop_first_h1=True)
    # Route rare glyphs missing from the Sung body font through WenQuanYi.
    for ch in ("昪", "璟"):
        body = body.replace(ch, r"{\fb " + ch + "}")

    parts = [
        PREAMBLE,
        TITLE_PAGE,
        r"\tableofcontents",
        r"\clearpage",
        body,
        r"\end{document}",
        "",
    ]
    tex = "\n\n".join(parts)
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
