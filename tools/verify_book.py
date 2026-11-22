#!/usr/bin/env python3
"""Zero-token automated LaTeX compiler, log analyzer, and style linter for TMS textbook project.

Usage:
  # Lint + 2-pass XeLaTeX compile of a master book (aux -> build/, pdf -> pdf/):
  python3 tools/verify_book.py tex/main_B4.tex --compile 2
  python3 tools/verify_book.py tex/main_B5_社會組.tex --compile 2

  # Lint + compile a standalone chapter (aux -> build/chapters/.../):
  python3 tools/verify_book.py chapters/B4/Chapter5_main.tex --compile 2

  # Static lint only (no compile):
  python3 tools/verify_book.py chapters/B4/Chapter5.tex
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys


XELATEX = shutil.which('xelatex') or '/Library/TeX/texbin/xelatex'
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
PDF_TOOL = os.path.join(TOOLS_DIR, 'bin', 'pdf_tool')


def is_master_tex(abs_tex: str) -> bool:
    tex_dir = os.path.join(REPO_ROOT, 'tex')
    parent = os.path.dirname(abs_tex)
    return parent == tex_dir or parent == REPO_ROOT


def resolve_included_files(main_tex: str) -> list:
    abs_tex = os.path.abspath(main_tex)
    base_dir = REPO_ROOT if is_master_tex(abs_tex) else os.path.dirname(abs_tex)
    files = [abs_tex]
    seen = {abs_tex}

    with open(abs_tex, encoding='utf-8') as f:
        content = f.read()

    for m in re.finditer(r'\\(?:include|input)\{([^}]+)\}', content):
        rel = m.group(1)
        if 'styles/' in rel:
            continue
        cand = os.path.join(base_dir, rel if rel.endswith('.tex') else rel + '.tex')
        cand = os.path.abspath(cand)
        if os.path.isfile(cand) and cand not in seen:
            seen.add(cand)
            files.append(cand)
    return files


def lint_tex_files(tex_files: list) -> dict:
    issues = []
    all_labels = set()
    all_refs = []
    tikz_summary = []
    period_counts = {'。': 0, '．': 0}

    for tf in tex_files:
        rel = os.path.relpath(tf, REPO_ROOT)
        with open(tf, encoding='utf-8') as f:
            text = f.read()
        lines = text.splitlines()

        tikz_lines = []
        in_display_math = False

        for idx, ln in enumerate(lines, start=1):
            stripped = ln.strip()
            if stripped.startswith('%'):
                continue

            if r'\begin{tikzpicture}' in ln:
                tikz_lines.append(idx)
                if '>=latex' in ln:
                    issues.append(f'[STYLE] {rel}:{idx}: TikZ uses legacy `>=latex` (prefer `>=Stealth`)')

            if r'\mathbf{R}' in ln or r'\mathbf{N}' in ln or r'\mathbf{Z}' in ln or r'\mathbf{Q}' in ln or r'\mathbf{C}' in ln:
                issues.append(f'[STYLE] {rel}:{idx}: Uses `\\mathbf{{R/C/...}}` (standard requires `\\mathbb{{...}}`)')

            if r'\begin{example-non}' in ln or r'\begin{example*}' in ln:
                issues.append(f'[STYLE] {rel}:{idx}: Uses legacy `example-non`/`example*` (prefer auto-numbered `example`)')

            # Track \[ ... \] single-line or multi-line for forbidden \footnote inside display math
            if r'\[' in ln and r'\]' in ln:
                if r'\footnote{' in ln:
                    issues.append(f'[LATEX] {rel}:{idx}: `\\footnote` directly inside `\\[...\\]` (use `\\footnotemark` + `\\footnotetext`)')
            else:
                if r'\[' in ln:
                    in_display_math = True
                if in_display_math and r'\footnote{' in ln:
                    issues.append(f'[LATEX] {rel}:{idx}: `\\footnote` inside display math (use `\\footnotemark` + `\\footnotetext`)')
                if r'\]' in ln:
                    in_display_math = False

            # Count Chinese periods in non-comment prose (skip _main.tex and main_*.tex boilerplate)
            if not rel.endswith('_main.tex') and not os.path.basename(rel).startswith('main'):
                period_counts['。'] += ln.count('。')
                period_counts['．'] += ln.count('．')

            for lm in re.finditer(r'\\label\{([^}]+)\}', ln):
                lbl = lm.group(1)
                if lbl in all_labels and lbl != 'sec:current_errata':
                    issues.append(f'[LABEL] {rel}:{idx}: Duplicate label `{lbl}`')
                all_labels.add(lbl)

            for rm in re.finditer(r'\\hyperref\[([^\]]+)\]', ln):
                all_refs.append((rel, idx, rm.group(1)))

        if tikz_lines:
            tikz_summary.append((rel, len(tikz_lines), tikz_lines))

    for rel, idx, target in all_refs:
        if target not in all_labels:
            issues.append(f'[REF] {rel}:{idx}: Broken `\\hyperref[{target}]` (label not defined in checked files)')

    # Flag mixed period usage if both exceed 10% of total
    total_p = period_counts['。'] + period_counts['．']
    if total_p > 20 and min(period_counts['。'], period_counts['．']) / total_p > 0.08:
        issues.append(
            f"[PUNCT] Mixed Chinese period styles across checked files: `。`={period_counts['。']}, `．`={period_counts['．']}"
        )

    return {
        'issues': issues,
        'tikz_summary': tikz_summary,
        'period_counts': period_counts,
        'label_count': len(all_labels),
    }


def compile_and_check_log(main_tex: str, passes: int) -> dict:
    abs_tex = os.path.abspath(main_tex)
    stem = os.path.splitext(os.path.basename(abs_tex))[0]
    master = is_master_tex(abs_tex)

    if master:
        work_dir = REPO_ROOT
        tex_arg = os.path.relpath(abs_tex, REPO_ROOT)
        build_dir = os.path.join(REPO_ROOT, 'build')
        final_pdf_dir = os.path.join(REPO_ROOT, 'pdf')
    else:
        work_dir = os.path.dirname(abs_tex)
        tex_arg = os.path.basename(abs_tex)
        rel_dir = os.path.relpath(work_dir, REPO_ROOT)
        build_dir = os.path.join(REPO_ROOT, 'build', rel_dir)
        final_pdf_dir = build_dir

    os.makedirs(build_dir, exist_ok=True)
    os.makedirs(final_pdf_dir, exist_ok=True)

    # Pre-create subdirs inside build_dir for any \include{...} targets so XeLaTeX can write child .aux files
    with open(abs_tex, encoding='utf-8') as f:
        for m in re.finditer(r'\\include\{([^}]+)\}', f.read()):
            sub = os.path.dirname(m.group(1))
            if sub:
                os.makedirs(os.path.join(build_dir, sub), exist_ok=True)

    log_path = os.path.join(build_dir, stem + '.log')
    built_pdf = os.path.join(build_dir, stem + '.pdf')
    final_pdf = os.path.join(final_pdf_dir, stem + '.pdf')

    exit_code = 0
    for _ in range(1, passes + 1):
        res = subprocess.run(
            [XELATEX, '-interaction=nonstopmode', f'-output-directory={build_dir}', tex_arg],
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors='replace',
        )
        exit_code = res.returncode
        if exit_code != 0:
            break

    if exit_code == 0 and os.path.isfile(built_pdf) and built_pdf != final_pdf:
        shutil.move(built_pdf, final_pdf)

    log_info = {
        'exit_code': exit_code,
        'pdf_path': os.path.relpath(final_pdf, REPO_ROOT) if os.path.isfile(final_pdf) else None,
        'pdf_pages': None,
        'errors': [],
        'undef_refs': [],
        'dup_labels': [],
        'missing_chars': [],
        'severe_overfull': [],
    }

    if os.path.isfile(log_path):
        with open(log_path, encoding='utf-8', errors='replace') as f:
            for ln in f:
                s = ln.strip()
                if s.startswith('! '):
                    log_info['errors'].append(s)
                elif 'Reference `' in s and 'undefined' in s:
                    log_info['undef_refs'].append(s)
                elif 'Multiply-defined' in s:
                    log_info['dup_labels'].append(s)
                elif 'Missing character:' in s:
                    log_info['missing_chars'].append(s)
                elif s.startswith('Overfull \\hbox'):
                    om = re.search(r'\(([0-9.]+)pt too wide\)', s)
                    if om and float(om.group(1)) >= 12.0:
                        log_info['severe_overfull'].append(s)

    if os.path.isfile(final_pdf) and os.path.isfile(PDF_TOOL):
        res = subprocess.run([PDF_TOOL, 'info', final_pdf], stdout=subprocess.PIPE, text=True)
        if res.returncode == 0:
            try:
                log_info['pdf_pages'] = json.loads(res.stdout).get('pages')
            except json.JSONDecodeError:
                pass

    return log_info


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('target', help='Target .tex file (tex/main_*.tex, chapters/.../ChapterY_main.tex, or ChapterY.tex)')
    parser.add_argument('--compile', type=int, default=0, help='Number of XeLaTeX compile passes (0=lint only, 2=full)')
    args = parser.parse_args()

    tex_files = resolve_included_files(args.target)
    lint = lint_tex_files(tex_files)

    print(f"=== Verify: {args.target} ({len(tex_files)} .tex files, {lint['label_count']} labels) ===")
    print(f"Chinese period counts: 「。」={lint['period_counts']['。']}, 「．」={lint['period_counts']['．']}")

    total_tikz = sum(c for _, c, _ in lint['tikz_summary'])
    print(f"TikZ figures: {total_tikz} total")
    for rel, cnt, _ in lint['tikz_summary']:
        print(f"  - {rel}: {cnt}")

    if lint['issues']:
        print(f"\nLint warnings/issues ({len(lint['issues'])}):")
        for item in lint['issues'][:30]:
            print(f"  {item}")
        if len(lint['issues']) > 30:
            print(f"  ... (+{len(lint['issues']) - 30} more)")
    else:
        print("\nLint: 0 issues!")

    exit_status = 0
    if args.compile > 0:
        print(f"\nCompiling ({args.compile} pass(es) of XeLaTeX)...")
        ci = compile_and_check_log(args.target, args.compile)
        print(f"XeLaTeX Exit Code: {ci['exit_code']} | Output PDF: {ci['pdf_path']} ({ci['pdf_pages']} pages)")
        if ci['errors']:
            print(f"Errors ({len(ci['errors'])}):")
            for e in ci['errors'][:15]:
                print(f"  {e}")
            exit_status = 1
        if ci['undef_refs']:
            print(f"Undefined references ({len(ci['undef_refs'])}):")
            for r in ci['undef_refs'][:15]:
                print(f"  {r}")
        if ci['dup_labels']:
            print(f"Duplicate labels ({len(ci['dup_labels'])}):")
            for d in ci['dup_labels'][:15]:
                print(f"  {d}")
        if ci['missing_chars']:
            print(f"Missing characters ({len(ci['missing_chars'])}):")
            for mc in ci['missing_chars'][:10]:
                print(f"  {mc}")
        if ci['severe_overfull']:
            print(f"Severe Overfull \\hbox >= 12pt ({len(ci['severe_overfull'])}):")
            for ov in ci['severe_overfull'][:10]:
                print(f"  {ov}")
        if ci['exit_code'] != 0:
            exit_status = ci['exit_code']

    sys.exit(exit_status)


if __name__ == '__main__':
    main()
