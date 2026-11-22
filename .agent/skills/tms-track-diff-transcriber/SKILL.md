---
name: tms-track-diff-transcriber
description: 《高中數學實驗教材》社會組（B3_社會組～B6_社會組）或改版重疊冊別之高效率、低 Token「差異化轉錄流水線（Diff-First Pipeline）」。利用本機零 Token OCR 與模糊比對定位自然組已轉錄底稿，採 Copy-and-Patch 與 TikZ 資產復用策略，大幅降低視覺輸入與文字輸出用量。凡轉錄社會組教材時，必須優先載入本技能。
---

# 社會組教材 Diff-First 差異化轉錄作業規範

社會組教材（第三至六冊）與已完成之自然組（`chapters/B3`～`B6`）存在大量重疊的定義、定理、例題、習題與 TikZ 插圖。為避免將 70%～85% 的 Token 浪費在重讀影像與從零重打既有內容，**嚴禁直接對社會組 PDF 進行全頁從零轉錄**，必須嚴格執行以下四階段流水線。

---

## 階段一：零浪費全冊目錄映射（TOC Mapping）

1. **生成自然組全套索引（0 Token）**：
   ```bash
   python3 tools/index_natural_track.py --books B3 B4 B5 B6 --out scratch/natural_index.md
   ```
2. **僅檢視社會組目錄 PDF（通常僅 2～4 頁）**：
   ```bash
   ./tools/bin/pdf_tool render original_scans/B{X}_社會組/*Contents*.pdf scratch/b{X}s_toc --dpi 150
   ```
3. **建立映射表 `scratch/b{X}s_mapping.md`**，將社會組每一章／每一節分類為 4 種模式：
   - `REUSE_SHARED`：共用數值附錄（三角函數表、對數表）→ 直接新建附錄殼檔並 `\input{chapters/shared/TrigTableBody.tex}` 或 `LogTableBody.tex`（**幾乎 0 Token**）。
   - `DIFF_PATCH`：與自然組某一章高度重疊（常見於刪去 `*` 進階節、精簡證明或刪減難題）。
   - `REORDERED_MERGE`：由自然組跨章／跨冊的數個基礎小節重組拼接而成。
   - `NEW_CONTENT`：社會組獨有單元（如商用數學、經濟／統計應用等）→ 走標準 `tms-latex-transcriber` 全頁精讀流程。

---

## 階段二：本機零 Token 預比對（Vision OCR + Diff Report）

針對每一章標記為 `DIFF_PATCH` 或 `REORDERED_MERGE` 的社會組 PDF，**先在本機跑零 Token 預比對**，精準掌握哪幾頁相同、哪幾段被刪除、哪幾頁有新增內容：

1. **獨立執行本機 Apple Vision OCR**（**注意**：此指令單獨呼叫且設定 `BypassSandbox: true`，不與其他指令串接；輸出會快取於 `scratch/ocr_cache/` 供反覆使用）：
   ```bash
   ./tools/bin/vision_ocr "original_scans/B{X}_社會組/<檔名>.pdf" --json scratch/ocr_cache/b{X}s_ch{Y}.json
   ```
2. **在沙盒內執行差異分析（0 Token）**：
   ```bash
   python3 tools/diff_scan_vs_tex.py \
     --ocr scratch/ocr_cache/b{X}s_ch{Y}.json \
     --tex chapters/B{src}/Chapter{src_ch}.tex \
     --out scratch/diff_reports/b{X}s_ch{Y}_diff.md
   ```
   （若是跨章合併，於 `--tex` 後一次傳入多個自然組 `.tex` 檔即可。）
3. **閱讀 `scratch/diff_reports/b{X}s_ch{Y}_diff.md`**，取得逐頁分級（`HIGH_OVERLAP` / `PARTIAL_EDIT` / `NEW_OR_HEAVY`）以及自然組疑似被刪除之區塊清單。

---

## 階段三：腳本生成底稿 + 分級 Copy-and-Patch（核心省用量步驟）

1. **用腳本建立社會組底稿（0 Output Token，直接繼承全部已精校 TikZ 與數學結構）**：
   ```bash
   python3 tools/scaffold_social_chapter.py \
     --src chapters/B{src}/Chapter{src_ch}.tex \
     --book {X} --chapter {Y} --title "<社會組章名>" --edition "<版次年份>"
   ```
   - 若為 `REORDERED_MERGE`，可指定行號切片拼接，例如 `--src chapters/B3/Chapter2.tex:1-420 chapters/B3/Chapter3.tex:1-280`。
   - 腳本會自動輸出 `chapters/B{X}_社會組/Chapter{Y}.tex` 與 `Chapter{Y}_main.tex`，並將所有 `\label`／`\ref`／`\eqref`／`\hyperref` 前綴轉為 ASCII `b{X}s-`。

2. **分級視覺核對與局部修補（切勿整章重寫，一律使用 `edit_file` 精準增刪）**：
   > **為什麼高重疊頁仍須看縮圖？** Apple Vision OCR 對繁中敘述極準，但對數學上下標、分式、負號、係數與圖號可能漏看；因此採用「**2-up 雙頁拼圖低 DPI 核對**」，兼顧 100% 數學精確度與 50%+ 影像 Token 節省。

   - **`HIGH_OVERLAP` 頁面**：
     - 使用雙頁拼圖一次核對兩頁（影像呼叫數直接減半）：
       ```bash
       ./tools/bin/pdf_tool spread "original_scans/B{X}_社會組/<檔名>.pdf" scratch/b{X}s_ch{Y}_spreads --start A --end B --dpi 130
       ```
     - 快速掃描每頁的**公式係數、上下標、題號、圖號與刪減句**；確認完全一致就跳過，有微調才用 `edit_file` 修補。
   - **`PARTIAL_EDIT` 頁面**：
     - 依差異報告先處理「疑似刪除區塊」（核對拼圖確認社會組確實略過 `*` 節或特定習題後，直接刪除該區塊並對齊後續編號）。
     - 針對「疑似新增／未匹配片段」局部修正或補錄；若該處公式密集難以辨認，再對單頁用 `--dpi 180` 或 `crop` 檢視。
   - **`NEW_OR_HEAVY` 頁面**：
     - 僅針對這少數幾頁執行 200 DPI 單頁渲染並依 `tms-latex-transcriber` 與 `tms-tikz-illustrator` 精細轉錄：
       ```bash
       ./tools/bin/pdf_tool render "original_scans/B{X}_社會組/<檔名>.pdf" scratch/b{X}s_ch{Y}_hi --start P --end Q --dpi 200
       ```
   - **TikZ 資產復用**：
     - 凡幾何結構與自然組相同之插圖，**直接沿用底稿中的 `tikzpicture`**，只調整圖號（如 `圖 2-5` → `圖 2-4`）或微調標籤。

---

## 階段四：零 Token 自動化勘誤與驗收

1. **自動抽取勘誤表**：
   ```bash
   python3 tools/build_errata.py \
     --tex chapters/B{X}_社會組/Chapter{Y}.tex \
     --caption "第{Y}章掃描檔勘誤、疑難處與文義校訂表" \
     --label tab:errata_b{X}s_ch{Y} \
     --out scratch/b{X}s_ch{Y}_errata.tex
   ```
   將產生之表格貼入 `Chapter{Y}_main.tex` 的勘誤區塊。
2. **一鍵編譯與靜態檢查**：
   ```bash
   python3 tools/verify_book.py chapters/B{X}_社會組/Chapter{Y}_main.tex --compile 2
   ```
   確保 Exit Code 0、0 未定義參照、0 重複標籤、0 違規樣式。
3. **差異圖形視覺自檢**：僅針對本章**新增或有修改的 TikZ 所在輸出頁**，以 `pdf_tool spread` 抽檢無碰撞即可宣告完成，無須重檢未改動之繼承圖形。

---

## 附：整冊平行化與子代理模型分工策略

處理整冊社會組時，建議採「**主代理規劃統籌 + 分層子代理平行執行**」以最大化成本效益：
- **主代理（高階模型）負責**：
  1. 階段一目錄映射與批次規劃；
  2. 執行本機 `vision_ocr`（方便集中一次授權）與 `diff_scan_vs_tex.py`、`scaffold_social_chapter.py`；
  3. 親自處理 `NEW_CONTENT` 章節、全新複雜 TikZ 圖形、以及全冊主檔組裝與數學疑難勘誤考證。
- **輕量模型子代理（`invoke_subagent` 設 `Model: "flash"`）負責**：
  - 凡差異報告顯示 **`HIGH_OVERLAP` ≥ 70% 且無大量新 TikZ** 之章節，直接將「底稿檔案路徑 + Diff 報告路徑 + 預先渲染好的雙頁拼圖路徑」分派給 `flash` 子代理平行執行 Copy-and-Patch 與 `verify_book.py` 單章驗收。
