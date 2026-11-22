---
name: tms-latex-transcriber
description: 《高中數學實驗教材》（1973–1976年版，第一至六冊，含自然組與社會組）掃描檔轉錄為高保真 XeLaTeX 原始碼之標準作業規範。凡進行章節轉錄、格式統一、直式算草排版或勘誤表整理時，必須優先載入並嚴格遵守本技能。
---

# 《高中數學實驗教材》LaTeX 數位轉錄核心規範

> 若目標為**社會組（`B3_社會組`～`B6_社會組`）**或與既有冊別高度重疊之版本，請**同時先載入 `tms-track-diff-transcriber`** 執行差異化底稿繼承流程，嚴禁從零重寫。

## 1. 專案檔案結構、組別命名與檔頭規範
- **目錄與檔名**：
  - 共同冊（B1–B2）與自然組（B3–B6）：`chapters/B{冊數}/Chapter{章數}.tex`、單章主檔 `Chapter{章數}_main.tex`、全冊主控檔 `main_B{冊數}.tex`（B1 為 `main.tex`）。
  - 社會組（B3–B6）：保留中文命名 `chapters/B{冊數}_社會組/Chapter{章數}.tex`、單章主檔 `Chapter{章數}_main.tex`、全冊主控檔 `main_B{冊數}_社會組.tex`。
- **章節檔頭**：每個 `Chapter{Y}.tex` 第一行必須加上 TeX root 宣告與**自動編號**章節指令（**嚴禁**使用 `\section*{第Y章 ...}`，亦**嚴禁**在 `\section{...}` 內重複硬寫「第Y章」）：
  ```latex
  % !TeX root = ChapterY_main.tex
  % =========================================================================
  % 《高中數學實驗教材》第 X 冊（自然組／社會組）
  % 第 Y 章 章節名稱
  % =========================================================================
  \section{章節名稱}\label{sec:bX-chY}
  ```
- **單章測試主檔（`Chapter{Y}_main.tex`）之計數器與勘誤錨點對齊**：
  - 在 `\include{ChapterY}` 正上方必須設定 `\setcounter{section}{Y-1}`（例如 `Chapter2_main.tex` 設為 `1`）。
  - 每個單章主檔與全冊主檔在勘誤表 `\section*{【說明】...}` 下方，除保留冊別專屬標籤外，**必須額外加上共用別名 `\label{sec:current_errata}`**，使正文註腳的 `\errataref` 在單章與全冊編譯時皆可無誤跳轉。
- **標籤命名空間（Label Namespace — 一律使用 ASCII）**：
  - 自然組／共同冊前綴為 `b{冊}`；**社會組前綴一律為 `b{冊}s`**（嚴禁在 `\label` 中使用中文字元）：
  - 章節：`sec:{前綴}-ch{章}`、`sec:{前綴}-{章}-{節}`、`subsec:{前綴}-{章}-{節}-a`
  - 習題：`sec:{前綴}-ex{章}-{節}`
  - 定理／例題／論例：`thm:{前綴}-{章}-{號}`、`ex:{前綴}-{章}-{號}`、`disc:{前綴}-{章}-{號}`（按節重編可加節號）
  - 公式：`eq:{前綴}-{章}-{節}-{號}`
  - 圖表：`fig:{前綴}-{章}-{號}`
  - 勘誤錨點：`note:{前綴}-ch{章}-p{原書頁碼}-{簡短英文關鍵字}`

## 2. 標題層級、章首大綱與節計數器重設規範

1. **章首大綱與導言**（若原書該章首頁印有大綱目錄與星號分隔線）：
   ```latex
   \begin{center}
   \begin{minipage}{0.75\textwidth}
   \begin{itemize}[leftmargin=2em, itemsep=0.3em]
     \item[§ I-1] \textbf{第一節名稱}
     \begin{itemize}[leftmargin=2em, itemsep=0.2em]
       \item[甲、] 子題名稱
       \item[乙、] 子題名稱
     \end{itemize}
   \end{itemize}
   \end{minipage}
   \end{center}

   \begin{center}
   $* \qquad * \qquad * \qquad * \qquad *$
   \end{center}
   ```

2. **節與子節層級（嚴禁使用 `\subsection*` 或在 `\subsection` 內重複硬寫 `§ X-Y`）**：
   - 節（§ X-Y）：統一使用自動編號 `\subsection{節名稱}\label{sec:bX-Y-Z}`（星號或雙十字選讀節寫成 `\subsection{*節名稱}` 或 `\subsection{\texorpdfstring{$\ddagger$ }{‡ }節名稱}`）。
   - **各節計數器歸零（`\resetsectcounters`）**：凡原書進入新節時定理、例題、論例、公式從 `1` 重新起算者，緊接在 `\subsection{...}\label{...}` 下一行加上 `\resetsectcounters`。
   - 子節（甲、乙、丙、丁）：一律使用 `\subsubsection*{甲、子節名稱}\label{subsec:...}`（**嚴禁**誤用 `\paragraph{甲、...}`）。
   - 隨堂作業：一律使用 `\subsubsection*{作業 N}`。
   - 節末習題：一律使用 `\subsubsection*{習題 X-Y}\label{sec:...}`。
   - 附錄：章末小附錄使用 `\phantomsection\subsection*{附錄 N\quad 附錄名稱}\label{...}\addcontentsline{toc}{subsection}{...}\resetsectcounters`；獨立附錄使用 `\phantomsection\section*{附錄 N\quad 附錄名稱}\label{...}\addcontentsline{toc}{section}{...}\resetsectcounters`。
   - **共用附錄表復用**：遇三角函數表或常用對數表，僅宣告該冊對應的 `\section*` 與 `\label` 後，直接 `\input{chapters/shared/TrigTableBody.tex}` 或 `\input{chapters/shared/LogTableBody.tex}`。

## 3. 定理、論例、例題、證明與公式編號規範（嚴防編號漂移）

嚴格禁止混用裸寫粗體、`tcolorbox`、舊式 `example-non` 或手動硬寫編號，統一採用 `styles/Chinese_math_style.tex` 定義之標準環境：

1. **定義、定理、引理、命題、推論**：
   - `\begin{definition}` / `\begin{definition*}`（無編號用 `*`，雙星號用 `\begin{definition*}[**]`）
   - `\begin{theorem}[定理名稱]\label{...}`（若原書採「定理 2.1」格式，可設 `\renewcommand{\thetheorem}{2.\arabic{theorem}}`）
   - `\begin{lemma}`、`\begin{prop}`／`\begin{proposition}`、`\begin{corollary}`
   - 定義內首次出現之核心專有名詞以 `\textbf{專有名詞}` 標示（不加底線）。
2. **例題與論例（嚴禁混用計數器）**：
   - 一般例題：一律用 `\begin{example}\label{...}`（星號進階例題用 `\begin{example}[*]`）。**嚴禁**使用 `\begin{example*}[例 N]` 或 `\begin{example-non}`。
   - 「【論例 N】」：**必須**使用獨立計數器 `\begin{discussion}\label{...}`（星號用 `\begin{discussion}[*]`）。**嚴禁**寫成 `\begin{example}[論例 N]`。
3. **證明、解答與注意／註記**：
   - 證明：`\paragraph{【證明】}` 或 `\begin{proof}[【證明】] ... \end{proof}`；原書末印 `#` 號者加 `\hfill$\#$`。
   - 解答：`\paragraph{【解】}` 或 `\begin{solution} ... \end{solution}`。
   - 注意／註記：`\paragraph{注意：}`、`\paragraph{註：}`。
4. **公式編號對齊**：
   - 原書右側印有 `(1), (2), ...` 者使用 `\begin{equation}\label{eq:...}` 或 `\begin{align}`；無編號獨立算式用 `\[ ... \]` 或 `align*`。
   - 衍生編號 `(1')`、羅馬編號 `(I)` 使用 `\tag{$1'$}`、`\tag{I}`。

## 4. 數學符號、巨集與排版鐵律

1. **數系記號**：統一使用 `\mathbb{N}, \mathbb{Z}, \mathbb{Q}, \mathbb{R}, \mathbb{C}`（或 `\N, \Z, \Q, \R, \C`），**嚴禁** `\mathbf{R}`。
2. **向量與幾何記號**：單字母向量用 `\vect{a}` 或 `\mathbf{a}`；兩點有向線段全章統一 `\vec{AB}` 或 `\overrightarrow{AB}`（勿同節混用）；線段長 `\overline{AB}`；圓弧 `\wideparen{AB}`。
3. **分式與定界符**：行內簡單數字分數可用 `\frac`，多項式／繁分式／三角分式與列表題目一律用 `\dfrac`；高大分式括號用 `\left( ... \right)`；二項式係數優先 `\binom{n}{k}`（討論排列組合記號時保留 `P_m^n, C_m^n, H_m^n`）。
4. **反三角函數**：主值用 `\operatorname{Sin}^{-1} x` 等，一般反三角用 `\sin^{-1} x`。
5. **直式算草與綜合除法**：使用 `\begin{center}\renewcommand{\arraystretch}{1.2}\begin{tabular}{...}` 搭配 `\cline` 與 `\multicolumn{1}{|r}{...}` 忠實重現，不得改寫為橫式。
6. **列表與多欄習題**：習題用 `\begin{enumerate}[label=\arabic*.]`（星號題寫 `\item[\textbf{*8.}]`）；短子題雙欄用 `\begin{multicols}{2}`；填空空格統一用 `\blank`。

## 5. 標點符號與文字忠實度規範

- **同一冊內句號必須完全一致**：全冊統一使用全形句號「`。`」（若既有冊別使用「`．`」則依該冊慣例維持一致，**嚴禁混用**）。
- 中文語境用全形標點「`、`」「`，`」「`：`」「`（...）`」「`〔...〕`」；數學模式 `$...$` 內一律半形。
- 忠實保留 1970 年代術語（如「樸式」「質式」「分項分式」「嵌射」「蓋射」「對射」「固有值／固有向量」「$\sim A$」）與設問句（「（為什麼？）」「（何故？）」）。

## 6. 掃描檔勘誤、印損校訂與雙向錨點規範

1. **雜訊剔除**：圖書館藏章、頁邊塗鴉、背頁透印直接剔除。
2. **正文校正與原位註腳**：明顯排印訛誤直接於正文修正，並緊接插入錨點與註腳（統一使用 `\errataref` 連回勘誤表）：
   ```latex
   ...正確文字或算式\phantomsection\label{note:bXs-chY-pZ-keyword}\footnote{【原書校訂】：原書第 Z 頁此處印作「...」，係鉛字磨損／排印訛誤，茲校訂為「...」，詳見\errataref。}
   ```
3. **嚴禁在 `\[...\]`、`equation`、`align` 等展示數學環境內直接放置 `\footnote`**！若錯處在展示算式內，**必須**於環境內放 `\footnotemark`、環境正上方放 `\phantomsection\label{note:...}`、環境正下方放 `\footnotetext{...}`。
4. **重大數學邏輯瑕疵**：正文忠實保留原書文字，並以註腳詳述反例與考證。

## 7. 全冊／長章節自動化分段轉錄工作流（免人工中斷）

1. **盤點頁數與批次切分（使用本機 `tools/`）**：
   - 以 `./tools/bin/pdf_tool info <pdf>` 查詢頁數。
   - 以 `./tools/bin/pdf_tool render <pdf> scratch/<tmp_dir> --start 1 --end 8 --dpi 200` 分批渲染（每批 5～8 頁，文字極清晰頁可用 `160` DPI）。
2. **逐批檢視與追加寫入**：
   - 每批轉錄完成後立即以 `write_file`（`Append: true`）寫入目標 `Chapter{Y}.tex`，絕不可省略任何段落、算式、插圖或習題。
   - 若遇無法辨認之殘損字模，使用 `./tools/bin/pdf_tool crop` 局部放大檢視。
3. **自動生成勘誤表與單章驗收**：
   - 執行 `python3 tools/build_errata.py --tex <ChapterY.tex> --out scratch/<errata.tex>` 自動彙整勘誤表並嵌入 `Chapter{Y}_main.tex`。
   - 執行 `python3 tools/verify_book.py <ChapterY_main.tex> --compile 2`，確認 Exit Code 0、0 斷鏈、0 Lint 違規。
   - 若該章含有 TikZ 插圖，依 `tms-tikz-illustrator` 執行**編譯後視覺自檢**，通過後立即自動進入下一章。
4. **全冊總控組裝與最終驗收**：
   - 用 `python3 tools/build_errata.py --tex <全冊各章.tex>` 產生目錄前總勘誤表，組裝全冊主控檔（加上 `\label{sec:current_errata}`），執行 `python3 tools/verify_book.py <main_file.tex> --compile 2`，並核對真實章名與頁數更新 `README.md`。
