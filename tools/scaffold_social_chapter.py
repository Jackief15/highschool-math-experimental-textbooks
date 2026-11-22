#!/usr/bin/env python3
"""Scaffold a Social Track chapter from one or more Natural Track .tex file(s) (or line slices).

Automatically:
  1. Copies/merges Natural Track .tex (preserving all polished TikZ, tables, equations).
  2. Rewrites ASCII label namespaces (e.g., b4- -> b4s-, b4_ -> b4s_) in \\label, \\ref, \\eqref, \\hyperref, \\cref.
  3. Updates % !TeX root and header comments to 社會組.
  4. Generates standardized Chapter{Y}_main.tex with \\setcounter{section}{Y-1} and \\label{sec:current_errata}.

Examples:
  # Copy entire Chapter 1 of B4 into B4_社會組 Chapter 1:
  python3 tools/scaffold_social_chapter.py --src chapters/B4/Chapter1.tex \\
      --book 4 --chapter 1 --title "座標變換與線性映射" --edition "民國六十五年（1976）三版"

  # Merge slices from multiple Natural Track chapters:
  python3 tools/scaffold_social_chapter.py --src chapters/B3/Chapter2.tex:1-420 chapters/B3/Chapter3.tex:1-300 \\
      --book 3 --chapter 2 --title "直觀幾何與向量"
"""
import argparse
import os
import re


CN_NUM = {1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八'}


def read_slice(spec: str) -> tuple:
    if ':' in spec and re.search(r':\d+-\d+$', spec):
        path, rng = spec.rsplit(':', 1)
        s, e = map(int, rng.split('-'))
        with open(path, encoding='utf-8') as f:
            lines = f.readlines()
        return path, ''.join(lines[s - 1:e])
    with open(spec, encoding='utf-8') as f:
        return spec, f.read()


def rewrite_labels(text: str, dst_book: int) -> str:
    """Rewrite b{N}- / b{N}_ label prefixes inside label/ref/eqref/hyperref/cref to b{dst_book}s-."""
    dst_prefix = f'b{dst_book}s'

    def repl_cmd(m):
        cmd, open_b, body, close_b = m.groups()
        # Rewrite patterns like sec:b4-ch1, eq:b3_2_1, note:b4-ch1-p12-foo
        new_body = re.sub(r'\bb([1-6])([-_])', rf'{dst_prefix}\2', body)
        return f'{cmd}{open_b}{new_body}{close_b}'

    pattern = re.compile(r'(\\(?:label|ref|eqref|cref|Cref|pageref))(\{)([^}]+)(\})')
    text = pattern.sub(repl_cmd, text)
    href_pattern = re.compile(r'(\\hyperref)(\[)([^\]]+)(\])')
    text = href_pattern.sub(repl_cmd, text)
    # Normalize any legacy errata back-links to \errataref or sec:current_errata
    text = re.sub(r'\\hyperref\[sec:(?:master_)?errata_notes(?:_b\d+)?\]\{目錄前勘誤表\}', r'\\errataref', text)
    return text


def build_chapter_main(book: int, ch: int, title: str, edition: str, tex_basename: str) -> str:
    b_cn = CN_NUM.get(book, str(book))
    c_cn = CN_NUM.get(ch, str(ch))
    return rf"""\documentclass[a4paper,12pt,twoside]{{article}}
\usepackage[left=1in,right=1in,top=1in,bottom=1in]{{geometry}}

\input{{../../styles/preamble.tex}}
\input{{../../styles/Chinese_math_style.tex}}
\input{{../../styles/math_style.tex}}

\fancypagestyle{{firstpage}}{{
  \fancyhf{{}}
  \fancyhead[R]{{\small《高中數學實驗教材》第 {book} 冊（社會組）}}
  \fancyhead[L]{{\small 第 {ch} 章\quad {title}}}
  \fancyfoot[C]{{\thepage}}
}}

\pagestyle{{fancy}}
\setlength{{\headheight}}{{14pt}}
\renewcommand{{\headrulewidth}}{{0.5pt}}
\renewcommand{{\footrulewidth}}{{0pt}}
\fancyhead{{}}
\fancyhead[LE]{{\small 《高中數學實驗教材》第{b_cn}冊（社會組）}}
\fancyhead[RO]{{\small 第{c_cn}章\quad {title}}}
\fancyfoot[C]{{\thepage}}

\title{{\LARGE\textbf{{《高中數學實驗教材》第{b_cn}冊（社會組）}}\\[0.5em] \Large\textbf{{第{c_cn}章\quad {title}}}}}
\author{{\textbf{{高中數學實驗教材編輯小組}}\quad 編著}}
\date{{{edition}}}

\begin{{document}}

\maketitle
\thispagestyle{{firstpage}}

% =========================================================================
% 掃描檔勘誤、文字校訂與疑難處說明（整理於目錄之前）
% =========================================================================
\section*{{【說明】第{c_cn}章掃描檔勘誤、疑難處與文義校訂表}}
\addcontentsline{{toc}}{{section}}{{【說明】第{c_cn}章掃描檔勘誤、疑難處與文義校訂表}}
\label{{sec:errata_notes_b{book}s_ch{ch}}}
\label{{sec:current_errata}}

% 使用 python3 tools/build_errata.py 自動產生並填入此處表格。

\newpage
\tableofcontents
\newpage

\setcounter{{section}}{{{ch - 1}}}
\include{{{tex_basename}}}

\end{{document}}
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', nargs='+', required=True, help='Source .tex path(s), optional :start-end line slice')
    parser.add_argument('--book', type=int, required=True, help='Target Social Track book number (3..6)')
    parser.add_argument('--chapter', type=int, required=True, help='Target chapter number (1..N)')
    parser.add_argument('--title', required=True, help='Target chapter title')
    parser.add_argument('--edition', default='民國六十四年（1975）版', help='Edition string for title page')
    parser.add_argument('--no-main', action='store_true', help='Skip creating ChapterY_main.tex')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing target files')
    args = parser.parse_args()

    out_dir = os.path.join('chapters', f'B{args.book}_社會組')
    os.makedirs(out_dir, exist_ok=True)
    tex_base = f'Chapter{args.chapter}'
    out_tex = os.path.join(out_dir, f'{tex_base}.tex')
    out_main = os.path.join(out_dir, f'{tex_base}_main.tex')

    if os.path.exists(out_tex) and not args.overwrite:
        raise SystemExit(f'Refusing to overwrite existing file: {out_tex} (pass --overwrite to force)')

    chunks = []
    for spec in args.src:
        _, content = read_slice(spec)
        # Strip leading comment header from source
        content = re.sub(r'^(?:\s*%.*\n)+', '', content)
        chunks.append(content.strip())

    merged = '\n\n'.join(chunks) + '\n'
    merged = rewrite_labels(merged, args.book)

    b_cn = CN_NUM.get(args.book, str(args.book))
    c_cn = CN_NUM.get(args.chapter, str(args.chapter))
    header = (
        f"% !TeX root = {tex_base}_main.tex\n"
        f"% =========================================================================\n"
        f"% 《高中數學實驗教材》第{b_cn}冊（社會組）\n"
        f"% 第{c_cn}章 {args.title}\n"
        f"% 底稿來源：{', '.join(args.src)}\n"
        f"% =========================================================================\n"
    )

    with open(out_tex, 'w', encoding='utf-8') as f:
        f.write(header + merged)
    print(f'Scaffolded chapter -> {out_tex}')

    if not args.no_main:
        main_content = build_chapter_main(args.book, args.chapter, args.title, args.edition, tex_base)
        with open(out_main, 'w', encoding='utf-8') as f:
            f.write(main_content)
        print(f'Scaffolded standalone main -> {out_main}')


if __name__ == '__main__':
    main()
