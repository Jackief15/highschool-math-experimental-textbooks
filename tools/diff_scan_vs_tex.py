#!/usr/bin/env python3
"""Zero-token local diff between a Social Track scan OCR JSON and candidate Natural Track .tex file(s).

Step 1 (outside sandbox):
  ./tools/bin/vision_ocr original_scans/B4_社會組/..._Ch1.pdf --json scratch/ocr_cache/b4s_ch1.json
Step 2 (sandboxed, 0 AI tokens):
  python3 tools/diff_scan_vs_tex.py --ocr scratch/ocr_cache/b4s_ch1.json \
      --tex chapters/B4/Chapter1.tex --out scratch/diff_reports/b4s_ch1_diff.md
"""
import argparse
import difflib
import json
import os
import re
from typing import List, Tuple


CJK_RE = re.compile(r'[\u4e00-\u9fff]+')
NORM_RE = re.compile(r'[^\u4e00-\u9fffa-zA-Z0-9]+')

BLOCK_START_RE = re.compile(
    r'^\s*(\\section|\\subsection|\\subsubsection|\\begin\{(?:definition|theorem|lemma|prop|proposition|corollary|example|discussion|homework|tikzpicture|enumerate)|\\item\b)'
)


def strip_latex(text: str) -> str:
    # Drop comments
    text = re.sub(r'(?<!\\)%.*', '', text)
    # Remove tikzpictures entirely from prose matching
    text = re.sub(r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}', ' [圖] ', text, flags=re.DOTALL)
    # Keep footnote text out of primary prose matching
    text = re.sub(r'\\footnote\{[^{}]*\}', '', text)
    text = re.sub(r'\\(?:label|ref|eqref|hyperref|phantomsection|resetsectcounters|addcontentsline|markboth)\b(?:\[[^\]]*\])?(?:\{[^}]*\})*', '', text)
    text = re.sub(r'\\(?:begin|end)\{[^}]*\}(?:\[[^\]]*\])?', ' ', text)
    text = re.sub(r'\\[a-zA-Z]+\*?', ' ', text)
    text = re.sub(r'[{}$^_&~\\]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def cjk_only(text: str) -> str:
    return ''.join(CJK_RE.findall(text))


def bigrams(s: str) -> set:
    if len(s) < 2:
        return {s} if s else set()
    return {s[i:i + 2] for i in range(len(s) - 1)}


def split_tex_blocks(tex_path: str) -> List[dict]:
    with open(tex_path, encoding='utf-8') as f:
        lines = f.readlines()

    blocks = []
    cur_start = 1
    cur_lines = []
    in_tikz = False

    def flush(end_line: int):
        nonlocal cur_lines, cur_start
        if not cur_lines:
            return
        raw = ''.join(cur_lines)
        plain = strip_latex(raw)
        cjk = cjk_only(plain)
        has_tikz = r'\begin{tikzpicture}' in raw
        first_nonempty = next((l.strip() for l in cur_lines if l.strip()), '')
        blocks.append({
            'file': tex_path,
            'start_line': cur_start,
            'end_line': end_line,
            'header': first_nonempty[:70],
            'plain': plain,
            'cjk': cjk,
            'bigrams': bigrams(cjk),
            'has_tikz': has_tikz,
            'matched_pages': [],
        })
        cur_lines = []

    for idx, line in enumerate(lines, start=1):
        if r'\begin{tikzpicture}' in line:
            in_tikz = True
        if not in_tikz and cur_lines and (line.strip() == '' and len(cur_lines) >= 6 or BLOCK_START_RE.match(line)):
            if len(''.join(cur_lines).strip()) > 30:
                flush(idx - 1)
                cur_start = idx
        cur_lines.append(line)
        if r'\end{tikzpicture}' in line:
            in_tikz = False
    flush(len(lines))
    return [b for b in blocks if len(b['cjk']) >= 8 or b['has_tikz']]


def page_overlap_score(page_cjk: str, block_cjk: str) -> Tuple[float, float]:
    """Return (containment_of_block_in_page, containment_of_page_in_block) using CJK bigrams."""
    if not page_cjk or not block_cjk:
        return 0.0, 0.0
    pb = bigrams(page_cjk)
    bb = bigrams(block_cjk)
    inter = len(pb & bb)
    return inter / max(len(bb), 1), inter / max(len(pb), 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ocr', required=True, help='OCR JSON produced by tools/bin/vision_ocr')
    parser.add_argument('--tex', nargs='+', required=True, help='Candidate Natural Track .tex file(s)')
    parser.add_argument('--out', required=True, help='Output Markdown diff report path')
    args = parser.parse_args()

    with open(args.ocr, encoding='utf-8') as f:
        ocr_data = json.load(f)

    all_blocks = []
    for tf in args.tex:
        all_blocks.extend(split_tex_blocks(tf))

    pages = ocr_data.get('pages', [])
    page_reports = []
    summary_counts = {'HIGH_OVERLAP': 0, 'PARTIAL_EDIT': 0, 'NEW_OR_HEAVY': 0}

    for p in pages:
        pno = p['page']
        raw_text = p.get('text', '')
        # Strip running header/page number lines (first/last very short lines)
        p_lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
        body_lines = [ln for ln in p_lines if not re.fullmatch(r'[\[\(（【\-—\s\d\]\)）】]+', ln) and '高中數學實驗教材' not in ln]
        p_cjk = cjk_only(''.join(body_lines))
        p_bigrams = bigrams(p_cjk)

        if len(p_cjk) < 15:
            status = 'NEW_OR_HEAVY'
            summary_counts[status] += 1
            page_reports.append({
                'page': pno, 'status': status, 'coverage': 0.0,
                'ranges': [], 'snippet': '（文字極少，可能為純圖表、封面或計算題頁，請直接檢視原圖）',
                'tikz_inherited': 0
            })
            continue

        matched_blocks = []
        covered_bigrams = set()
        for b in all_blocks:
            if not b['cjk']:
                continue
            in_page, _ = page_overlap_score(p_cjk, b['cjk'])
            # A block belongs to this page if >= 35% of its CJK bigrams appear on this page (or >= 14 shared bigrams)
            shared = p_bigrams & b['bigrams']
            if in_page >= 0.32 or len(shared) >= 16:
                matched_blocks.append((b, in_page, len(shared)))
                covered_bigrams |= shared
                b['matched_pages'].append(pno)

        coverage = len(covered_bigrams) / max(len(p_bigrams), 1)
        if coverage >= 0.68:
            status = 'HIGH_OVERLAP'
        elif coverage >= 0.35:
            status = 'PARTIAL_EDIT'
        else:
            status = 'NEW_OR_HEAVY'
        summary_counts[status] += 1

        # Group matched blocks into contiguous file/line ranges
        by_file = {}
        tikz_inherited = 0
        for b, score, _ in matched_blocks:
            by_file.setdefault(b['file'], []).append((b['start_line'], b['end_line']))
            if b['has_tikz']:
                tikz_inherited += 1

        ranges_str = []
        for fn, spans in by_file.items():
            spans.sort()
            merged = [spans[0]]
            for s, e in spans[1:]:
                if s <= merged[-1][1] + 25:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], e))
                else:
                    merged.append((s, e))
            for s, e in merged:
                ranges_str.append(f'`{os.path.basename(fn)}:L{s}-L{e}`')

        # Find lines on the OCR page that had low match (potential new content)
        unmatched_lines = []
        matched_cjk_pool = ''.join(b['cjk'] for b, _, _ in matched_blocks)
        matched_pool_bg = bigrams(matched_cjk_pool)
        for ln in body_lines:
            lc = cjk_only(ln)
            if len(lc) >= 8:
                lbg = bigrams(lc)
                hit = len(lbg & matched_pool_bg) / max(len(lbg), 1)
                if hit < 0.35:
                    unmatched_lines.append(ln[:60])

        page_reports.append({
            'page': pno,
            'status': status,
            'coverage': coverage,
            'ranges': ranges_str,
            'unmatched_preview': unmatched_lines[:4],
            'tikz_inherited': tikz_inherited,
        })

    # Find unmatched Natural Track blocks (likely deleted in Social Track)
    deleted_blocks = [b for b in all_blocks if not b['matched_pages'] and len(b['cjk']) >= 18]

    # Build Markdown report
    out = []
    out.append(f"# 社會組 vs 自然組 零 Token 差異比對報告\n")
    out.append(f"- **掃描檔來源**：`{ocr_data.get('source', '')}`（共 {len(pages)} 頁）")
    out.append(f"- **比對自然組底稿**：{', '.join(f'`{t}`' for t in args.tex)}")
    out.append(f"- **分級統計**：")
    out.append(f"  - `HIGH_OVERLAP`（高重疊，建議 130 DPI 雙頁拼圖快核公式）：**{summary_counts['HIGH_OVERLAP']} 頁**")
    out.append(f"  - `PARTIAL_EDIT`（局部增刪，建議雙頁/單頁比對修補）：**{summary_counts['PARTIAL_EDIT']} 頁**")
    out.append(f"  - `NEW_OR_HEAVY`（新增或大幅改寫，須 200 DPI 精讀轉錄）：**{summary_counts['NEW_OR_HEAVY']} 頁**\n")

    out.append("## 1. 逐頁對應與建議處理方式\n")
    out.append("| 掃描頁 | 分級 | 覆蓋率 | 對應自然組區間 | 疑似新增／未匹配片段 |")
    out.append("| :---: | :---: | :---: | :--- | :--- |")
    for r in page_reports:
        ranges = ', '.join(r['ranges']) if r['ranges'] else '—'
        preview = ' / '.join(r.get('unmatched_preview', [])) or r.get('snippet', '—')
        preview = preview.replace('|', '\\|')
        out.append(f"| p.{r['page']} | `{r['status']}` | {r['coverage']*100:.0f}% | {ranges} | {preview} |")

    out.append("\n## 2. 自然組存在但社會組未匹配之區塊（疑似已刪減）\n")
    if not deleted_blocks:
        out.append("（無明顯整段刪除區塊）\n")
    else:
        for b in deleted_blocks:
            tikz_tag = ' `[含TikZ]`' if b['has_tikz'] else ''
            out.append(f"- `{os.path.basename(b['file'])}:L{b['start_line']}-L{b['end_line']}`{tikz_tag}：{b['header']}")

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')

    print(
        f"Diff report written -> {args.out} | "
        f"HIGH={summary_counts['HIGH_OVERLAP']}, "
        f"PARTIAL={summary_counts['PARTIAL_EDIT']}, "
        f"NEW={summary_counts['NEW_OR_HEAVY']}, "
        f"DELETED_BLOCKS={len(deleted_blocks)}"
    )


if __name__ == '__main__':
    main()
