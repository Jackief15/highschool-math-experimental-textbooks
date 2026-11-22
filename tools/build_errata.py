#!/usr/bin/env python3
"""Extract all errata anchors (\\label{note:...}) and footnotes from .tex files to build xltabular errata tables.

Usage:
  python3 tools/build_errata.py --tex chapters/B4/Chapter1.tex chapters/B4/Chapter2.tex \\
      --caption "全冊各章掃描檔勘誤、疑難處與文義校訂彙整表" \\
      --label tab:errata_b4_master \\
      --out scratch/b4_errata.tex
"""
import argparse
import os
import re
from typing import List, Tuple


SECTION_RE = re.compile(r'^\s*\\section\*?(?:\[[^\]]*\])?\{')
SUBSEC_RE = re.compile(r'^\s*\\subsection\*?(?:\[[^\]]*\])?\{')


def extract_braced(text: str, open_idx: int) -> Tuple[str, int]:
    """Given text[open_idx] == '{', return (inner_content, close_idx)."""
    depth = 0
    for i in range(open_idx, len(text)):
        ch = text[i]
        if ch == '\\' and i + 1 < len(text):
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:i], i
    return text[open_idx + 1:], len(text) - 1


def clean_title(s: str) -> str:
    s = re.sub(r'\\texorpdfstring\{[^}]*\}\{([^}]*)\}', r'\1', s)
    s = re.sub(r'\\(?:quad|qquad|textbf)\b', ' ', s)
    s = re.sub(r'[{}]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def extract_errata_from_file(tex_path: str) -> Tuple[str, List[dict]]:
    with open(tex_path, encoding='utf-8') as f:
        text = f.read()

    # Precompute line start offsets and nearest section/subsection titles
    lines = text.splitlines(keepends=True)
    line_offsets = []
    pos = 0
    cur_sec = os.path.splitext(os.path.basename(tex_path))[0]
    cur_subsec = ''
    sec_title = cur_sec
    line_ctx = []

    for ln in lines:
        line_offsets.append(pos)
        pos += len(ln)
        m1 = SECTION_RE.match(ln)
        if m1:
            t1, _ = extract_braced(ln, m1.end() - 1)
            cur_sec = clean_title(t1)
            if sec_title == os.path.splitext(os.path.basename(tex_path))[0]:
                sec_title = cur_sec
        m2 = SUBSEC_RE.match(ln)
        if m2:
            t2, _ = extract_braced(ln, m2.end() - 1)
            cur_subsec = clean_title(t2)
        line_ctx.append((cur_sec, cur_subsec))

    def offset_to_line(off: int) -> int:
        lo, hi = 0, len(line_offsets) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_offsets[mid] <= off:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    entries = []
    for m in re.finditer(r'\\label\{(note:[^}]+)\}', text):
        label = m.group(1)
        end_pos = m.end()
        line_no = offset_to_line(m.start())
        _, subsec = line_ctx[line_no - 1]

        # Look ahead within 600 chars for \footnote{...} or \footnotetext{...}
        window = text[end_pos:end_pos + 1200]
        fm = re.search(r'\\footnote(?:text)?(?:\[\d+\])?\{', window)
        note_body = ''
        if fm:
            brace_pos = end_pos + fm.end() - 1
            note_body, _ = extract_braced(text, brace_pos)
            # Clean redundant back-link to errata table
            note_body = re.sub(r'[，,、]?(?:並詳列於|詳見|見)\\(?:hyperref\[[^\]]+\]\{目錄前勘誤表\}|errataref)[。．.]?', '', note_body)
            note_body = re.sub(r'^【原書(?:註記/校訂|校訂|註記)】[：:]?\s*', '', note_body).strip()

        # Parse page number if present in label (e.g. note:b4-ch5-p286-errata)
        pm = re.search(r'-p(\d+)', label)
        page_str = f'頁 {pm.group(1)}' if pm else f'第 {line_no} 行'
        loc = f'{subsec} {page_str}'.strip() if subsec else page_str

        # Split first clause outside $...$ math spans for concise phenomenon column
        phenomenon = '原書排印訛誤／印損'
        if note_body:
            in_math = False
            cut = len(note_body)
            for idx_c, ch in enumerate(note_body):
                if ch == '$' and (idx_c == 0 or note_body[idx_c - 1] != '\\'):
                    in_math = not in_math
                elif not in_math and ch in '，。；' and idx_c >= 4:
                    cut = idx_c
                    break
            cand = note_body[:cut].strip()
            if cand and cand.count('$') % 2 == 0:
                phenomenon = cand

        entries.append({
            'label': label,
            'line': line_no,
            'loc': loc,
            'phenomenon': phenomenon,
            'explanation': note_body or '（請補述校訂說明）',
        })

    return sec_title, entries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tex', nargs='+', required=True)
    parser.add_argument('--caption', default='掃描檔勘誤、疑難處與文義校訂彙整表')
    parser.add_argument('--label', default='tab:errata_auto')
    parser.add_argument('--out', default='')
    args = parser.parse_args()

    out = [
        r'\small',
        r'\renewcommand{\arraystretch}{1.35}',
        r'\begin{xltabular}{\textwidth}{|p{3.2cm}|p{3.8cm}|X|}',
        rf'\caption{{{args.caption}}}\label{{{args.label}}} \\',
        r'\hline',
        r'\textbf{章節位置} & \textbf{掃描檔原始現象 / 誤植} & \textbf{考證說明與校訂處理} \\ \hline',
        r'\endfirsthead',
        r'\hline',
        r'\textbf{章節位置} & \textbf{掃描檔原始現象 / 誤植} & \textbf{考證說明與校訂處理} \\ \hline',
        r'\endhead',
        r'\hline',
        r'\endfoot',
    ]

    total = 0
    for tf in args.tex:
        sec_title, entries = extract_errata_from_file(tf)
        if not entries:
            continue
        if len(args.tex) > 1:
            out.append(rf'\multicolumn{{3}}{{|c|}}{{\textbf{{{sec_title}}}}} \\ \hline')
        for e in entries:
            total += 1
            out.append(
                rf"\hyperref[{e['label']}]{{{e['loc']}}} & {e['phenomenon']} & {e['explanation']} \\ \hline"
            )

    if total == 0:
        out.append(r'\multicolumn{3}{|c|}{（本範圍無發現印刷訛誤或待校訂項目）} \\ \hline')

    out.append(r'\end{xltabular}')
    out.append(r'\normalsize')
    rendered = '\n'.join(out) + '\n'

    if args.out:
        os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(rendered)
        print(f'Extracted {total} errata entries -> {args.out}')
    else:
        print(rendered)


if __name__ == '__main__':
    main()
