# 《高中數學實驗教材》LaTeX 數位化專案核心規則

## 1. 專案目錄與組別命名規範
- **產物分層目錄**：
  - 全冊主控檔：`tex/main_B1.tex` ～ `tex/main_B6.tex`、`tex/main_B3_社會組.tex` ～ `tex/main_B6_社會組.tex`
  - 最終成品 PDF：`pdf/main_B1.pdf` ～ `pdf/main_B6_社會組.pdf`
  - 編譯中間檔：`build/`（所有 `.aux`／`.log`／`.out`／`.toc`，已列入 `.gitignore`）
  - 各冊章節原始碼：`chapters/B1/` ～ `chapters/B6/`、`chapters/B3_社會組/` ～ `chapters/B6_社會組/`
- **社會組命名規範（保留中文目錄與主檔名，內部 LaTeX Label 一律使用 ASCII）**：
  - 掃描檔：`original_scans/B{X}_社會組/`
  - 章節檔：`chapters/B{X}_社會組/Chapter{Y}.tex` 與 `Chapter{Y}_main.tex`
  - 全冊主控檔：`tex/main_B{X}_社會組.tex`
  - 內部 `\label` 前綴：統一使用 ASCII `b{X}s-`（例如 `sec:b3s-ch1`、`eq:b4s-1-2-1`、`note:b4s-ch2-p15-typo`），嚴禁在 `\label` 中使用中文字元。
- **共用附錄模組**：`chapters/shared/TrigTableBody.tex`（三角函數表）、`chapters/shared/LogTableBody.tex`（常用對數表）。遇到相同數值表直接 `\input`，禁止重新轉錄。

## 2. 本機零 Token 工具箱（`tools/`）
本機環境**未安裝** `pypdf`、`PyMuPDF (fitz)`、`PIL`、`pdftoppm`、`tesseract`，**禁止**浪費回合嘗試呼叫上述套件。請一律使用專案內建之 macOS 原生與純 Python 工具：
- `./tools/bin/pdf_tool info <pdf>`：查詢 PDF 頁數與尺寸。
- `./tools/bin/pdf_tool render <pdf> <out_dir> --start N --end M --dpi 150`：渲染指定頁碼為 PNG（高密度公式用 `200` DPI）。
- `./tools/bin/pdf_tool spread <pdf> <out_dir> --start N --end M --dpi 130`：將連續兩頁並排合成一張雙頁拼圖（附頁碼標頭），用於高重疊頁快速核對，**影像用量直接減半**。
- `./tools/bin/pdf_tool crop <in_png> <out_png> <x> <y> <w> <h>`：以 `[0,1]` 比例裁切局部細節（放大檢視模糊字模或插圖）。
- `./tools/bin/vision_ocr <pdf_or_png> --json <out.json>`：Apple Vision 繁中本地 OCR（0 AI Token）。**注意**：此工具須獨立單獨執行並設 `BypassSandbox: true`（不可與其他指令串接），其餘所有 `tools/` 工具皆在沙盒內執行。
- `python3 tools/index_natural_track.py`：產出自然組全套章節與 TikZ 索引。
- `python3 tools/diff_scan_vs_tex.py --ocr <json> --tex <自然組.tex...> --out <diff.md>`：零 Token 自動比對社會組 OCR 與自然組底稿，輸出逐頁重疊度與刪減區塊報告。
- `python3 tools/scaffold_social_chapter.py`：複製／拼接自然組底稿至 `chapters/B{X}_社會組/`，自動轉換 `b{X}s-` 標籤命名空間並建立 `Chapter{Y}_main.tex`。
- `python3 tools/build_errata.py`：自動從正文 `\label{note:...}` 抽取註腳並生成 `xltabular` 勘誤表。
- `python3 tools/verify_book.py <target.tex> --compile 2`：一鍵執行兩次 XeLaTeX 編譯、解析 `.log` 錯誤／斷鏈／嚴重溢出，並靜態檢查排版規範與頁數。
- 若二進位檔不存在，執行 `./tools/build_tools.sh` 重新編譯。所有暫存圖檔與報告一律置於 `scratch/`（已列入 `.gitignore`）。

## 3. 編譯環境
- 推薦一鍵編譯（自動輸出中間檔至 `build/`、成品至 `pdf/`）：`python3 tools/verify_book.py tex/main_B{X}.tex --compile 2`（或 `make B1`～`make B6s`／`make all`）。
- 編譯器絕對路徑：`/Library/TeX/texbin/xelatex -interaction=nonstopmode -output-directory=build tex/<file.tex>`（於專案根目錄執行兩次以解析目錄與交叉參照）。
- 共用樣式：`styles/preamble.tex`、`styles/Chinese_math_style.tex`、`styles/math_style.tex`。

## 4. 技能觸發原則（Skill Routing）
- **轉錄社會組（`B3_社會組`～`B6_社會組`）或改版重疊冊別**：**必須優先載入 `tms-track-diff-transcriber`**，先跑零 Token 差異比對與底稿繼承，嚴禁從零逐頁重打！
- **一般章節轉錄、格式規範、勘誤註腳**：載入 `tms-latex-transcriber`。
- **原書插圖重繪與編譯後圖形視覺自檢**：載入 `tms-tikz-illustrator`。

## 5. 成本最佳化與子代理分工建議
- 轉錄全冊時，主力高階模型負責「目錄規劃、全新內容（`NEW_CONTENT`）、複雜 TikZ 重繪與數學勘誤考證」。
- 經 `diff_scan_vs_tex.py` 判定為高重疊（`HIGH_OVERLAP`）或單純刪節修補（`PARTIAL_EDIT`）的章節，可分派給輕量模型子代理（`Model: "flash"`）平行執行 Copy-and-Patch，最後統一由 `tools/verify_book.py` 驗收。
