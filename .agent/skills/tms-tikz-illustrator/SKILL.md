---
name: tms-tikz-illustrator
description: 《高中數學實驗教材》向量幾何圖、函數圖、極座標與極圖映射（polar chart）、排列組合樹狀圖與三維二次曲面之 TikZ 高精度向量重繪與編譯後視覺自檢規範。凡轉錄過程中遇到原書插圖，必須載入本技能進行繪製與驗收。
---

# 《高中數學實驗教材》TikZ 幾何與函數圖重繪規範

## 1. 核心原則：絕不省略插圖、精準還原幾何關係
- 原書每一幅插圖（包含座標系、映射箭頭圖、正交分解盒、圓錐截痕、八卦圖、樹枝圖、文氏圖）皆須以 `TikZ` 原生向量程式碼重繪，**嚴禁**以 `[此處略去圖片]` 或外部截圖代替。
- **版面配置**：
  - 獨立置中圖形使用 `\begin{figure}[H] \centering ... \end{figure}`（或置中環境）。
  - 原書左右並排之雙子圖優先在同一個 `tikzpicture` 中使用 `\begin{scope}[xshift=...]` 繪製，或使用兩個 `\begin{minipage}[c]{0.48\textwidth}` 並排。
  - 文繞圖（例題旁的小型幾何圖）使用 `\noindent\begin{minipage}[t]{0.64\textwidth} ... \end{minipage}\hfill\begin{minipage}[t]{0.34\textwidth} ... \end{minipage}`。
  - 圖號標示：若原書僅印「圖 3-2」而無圖說標題，使用 `\caption*{圖 3-2}\label{fig:...}` 或置中 `\small 圖 3-2`，保持與原書一致。

## 2. 線條、箭頭與節點視覺標準
1. **箭頭與線寬**：
   - 統一在 `\begin{tikzpicture}` 加上 `[>=Stealth, scale=..., line cap=round, line join=round]`（**禁止**使用舊式 `>=latex`）。
   - 座標軸：`\draw[->, thick]`，軸端標註 `node[right] {$X$}`、`node[above] {$Y$}`，原點標註 `\node[below left] at (0,0) {$O$};`。
   - 主要幾何曲線／主向量：`\draw[very thick]` 或 `\draw[->, very thick]`。
   - 輔助投影線／對稱軸／漸近線：`\draw[dashed, semithick]` 或 `\draw[dashed]`。
2. **描點與端點**：
   - 實心點：`\fill (P) circle (1.5pt);`（空心點用 `\draw[thick, fill=white] (P) circle (2pt);`）。
3. **防重疊鐵律（Anti-Collision Rules）**：
   - 標籤絕對不可壓在曲線、線段或座標軸實線上！
   - 若標籤位置緊鄰格線或扇形邊界，加上白底光暈：`node[fill=white, inner sep=1pt, font=\footnotesize] {...}`。
   - 角度弧線（如 $\theta, \omega, \frac{\pi}{6}$）半徑須依層級錯開（例如內弧 `0.45cm`、外弧 `0.85cm`），角度文字置於弧線中點外側 `(角度:半徑+0.25)`。
   - 密集交點或密集刻度使用細引線 `\draw[thin, gray] (點) -- (空白處) node[black] {...};` 引出標註。
   - 務必核對原圖的**象限位置、虛實線區分（如立體投影可見／被遮蔽線段）、直角記號與相似三角形輔助線**，不可憑印象簡化。

## 3. 常見圖形標準模板

### A. 映射對照圖（集合對射／極圖映射 $\gamma: (\theta, r) \to (x, y)$）
- 左側 `scope` 繪製定義域，右側 `scope`（`xshift=7cm`）繪製對應域，中間以 `\draw[->, thick] (3.6, 0) -- node[above] {$\gamma$} (4.6, 0);` 連接。
- 特定點對點映射曲線使用貝茲曲線 `\draw[->, thick] (A) .. controls (c1) and (c2) .. (Ap);` 避開座標軸文字。

### B. 平面與極座標函數繪圖
- TikZ 預設三角單位為**度（degrees）**；若自變數 `\x` 為弧度，務必寫 `sin(\x r)`、`cos(\x r)`。
- 反函數圖形（如 $y = \sin^{-1} x, y = \log_2 x$）採參數對調 `plot ({sin(\x r)}, \x)` 或 `plot ({pow(2,\x)}, \x)`。
- 極座標曲線使用 `plot[domain=..., samples=300, smooth, variable=\t] (\t : {函數(\t)})`。

### C. 空間三維直角座標系 $(O; X, Y, Z)$ 與立體曲面
- 統一斜軸投影視角：
  ```latex
  \draw[->, thick] (0, 0) -- (-2.0, -1.5) node[below left] {$X$};
  \draw[->, thick] (0, 0) -- (3.8, 0) node[right] {$Y$};
  \draw[->, thick] (0, 0) -- (0, 3.4) node[above] {$Z$};
  ```
- 投影長方盒：先定出 $P_1, P_2, P'$，以 `dashed` 繪製底面平行四邊形與鉛垂線，主向量 $\vec{OP}$ 用 `very thick, ->`。
- 截面陰影使用 `pattern=north east lines, pattern color=gray!60` 或 `\path[clip]` 搭配平行細斜線。

## 4. 社會組／重疊章節之 TikZ 資產復用鐵律（節省 Token）
- 轉錄社會組（`B3_社會組`～`B6_社會組`）時，**嚴禁重新撰寫自然組已繪製完成且幾何結構相同的 TikZ 圖形**！
- 直接繼承自然組（已精校過之 `chapters/B3`～`B6`）的 `tikzpicture` 程式碼，僅依社會組掃描檔核對：
  1. 圖號是否改變（例如自然組「圖 3-5」→ 社會組「圖 3-4」）；
  2. 點位標籤、角度記號或是否刪去某條進階輔助線；
  3. 用 `edit_file` 局部微調即可。

## 5. 強制性編譯後視覺自檢閉環（Visual QA Loop）
凡新增或大幅修改 TikZ 圖形之章節，**在單章編譯完成後、宣告完成之前**，必須執行一次快速視覺自檢，避免事後整冊返工：
1. 編譯單章主檔：`python3 tools/verify_book.py chapters/<冊>/Chapter<Y>_main.tex --compile 2`。
2. 僅將**含新繪或修改 TikZ 的輸出頁碼**渲染成雙頁拼圖以節省用量：
   ```bash
   ./tools/bin/pdf_tool spread chapters/<冊>/Chapter<Y>_main.pdf scratch/qa_<ch> --start <頁1> --end <頁2> --dpi 130
   ```
3. 以 `read_file` 快速檢視產出拼圖，確認每幅圖符合 4 項標準：
   - 無文字壓線或標籤互相碰撞；
   - 圖形寬度未超出頁邊距（無 Overfull `\hbox`）；
   - 象限、角度方向、虛實線與原書掃描一致；
   - 發現瑕疵當場以 `edit_file` 修正並重編確認，做到**一次到位**。
