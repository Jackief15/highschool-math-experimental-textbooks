#!/usr/bin/env python3
"""Index all existing chapters (B1-B6) for fast Natural->Social track TOC mapping.

Usage:
  python3 tools/index_natural_track.py [--books B3 B4 B5 B6] [--out scratch/natural_index.md] [--json scratch/natural_index.json]
"""
import argparse
import glob
import json
import os
import re


HEADING_RE = re.compile(
    r'^\s*\\(section|subsection|subsubsection)(\*?)(?:\[[^\]]*\])?\{'
)


def extract_braced(text: str, open_idx: int):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == '\\' and i + 1 < len(text):
            continue
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:i], i
    return text[open_idx + 1:], len(text) - 1


def clean_tex_title(s: str) -> str:
    s = re.sub(r'\\texorpdfstring\{[^}]*\}\{([^}]*)\}', r'\1', s)
    s = re.sub(r'\\(?:quad|qquad|textbf|emph)\b', ' ', s)
    s = re.sub(r'[{}]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def index_file(path: str) -> dict:
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()

    headings = []
    tikz_count = 0
    for idx, line in enumerate(lines, start=1):
        if r'\begin{tikzpicture}' in line:
            tikz_count += 1
        m = HEADING_RE.match(line)
        if m:
            level, star = m.groups()
            title, close_i = extract_braced(line, m.end() - 1)
            lm = re.search(r'\\label\{([^}]+)\}', line[close_i + 1:])
            headings.append({
                'line': idx,
                'level': level + star,
                'title': clean_tex_title(title),
                'label': lm.group(1) if lm else ''
            })

    return {
        'path': path,
        'lines': len(lines),
        'tikz_count': tikz_count,
        'headings': headings,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--books', nargs='*', default=['B1', 'B2', 'B3', 'B4', 'B5', 'B6'])
    parser.add_argument('--out', default='')
    parser.add_argument('--json', dest='json_out', default='')
    args = parser.parse_args()

    result = {}
    md_lines = ['# 自然組／既有各冊章節結構索引\n']

    for book in args.books:
        book_dir = os.path.join('chapters', book)
        if not os.path.isdir(book_dir):
            continue
        tex_files = sorted(
            p for p in glob.glob(os.path.join(book_dir, '*.tex'))
            if not p.endswith('_main.tex')
        )
        result[book] = []
        md_lines.append(f'## {book}\n')
        for tf in tex_files:
            info = index_file(tf)
            result[book].append(info)
            sec_title = next((h['title'] for h in info['headings'] if h['level'].startswith('section')), os.path.basename(tf))
            md_lines.append(f"### `{tf}` — {sec_title} ({info['lines']} 行, {info['tikz_count']} 張 TikZ)")
            for h in info['headings']:
                if h['level'].startswith('subsection'):
                    md_lines.append(f"- L{h['line']}: **{h['title']}**")
                elif h['level'].startswith('subsubsection') and not h['title'].startswith('作業'):
                    md_lines.append(f"  - L{h['line']}: {h['title']}")
            md_lines.append('')

    md_text = '\n'.join(md_lines)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(md_text)
        print(f'Wrote Markdown index -> {args.out}')
    else:
        print(md_text)

    if args.json_out:
        os.makedirs(os.path.dirname(args.json_out) or '.', exist_ok=True)
        with open(args.json_out, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f'Wrote JSON index -> {args.json_out}')


if __name__ == '__main__':
    main()
