# 《高中數學實驗教材 第一冊》（1973年修訂版）LaTeX 數位轉錄專案

本專案依據 1973 年（民國六十二年）教育部修訂版《高中數學實驗教材 第一冊》（高一上）原始掃描教材進行高品質 \LaTeX{} 數位化轉錄與重排。

---

## 教材來源與背景說明

- **教材典藏來源**：[中華民國數學會（TMS）數學教育推廣平台 — 高中數學實驗教材](https://sites.google.com/math.ntu.edu.tw/tmseducation/學級資源/10-12年級/高中數學實驗教材)
- **歷史背景**：本教材為教育部高中數學實驗教材編輯小組於民國六十二年（1973）修訂出版之第一冊，為臺灣中學數學教育發展史上極具代表性之「新數學（New Math）」實驗課程教材，強調集合論語言、抽象代數結構與嚴謹邏輯推理。
- **數位化目標**：本專案以現代高品質之 \LaTeX{}（XeLaTeX）重排，校訂原書鉛字印損、錯別字與排印訛誤（詳見主檔目錄前勘誤表），並重繪高解析向量幾何圖與文氏圖，以供數學教學、學術研究與數位典藏參考。

---

## 專案目錄結構

```text
高中數學實驗教材數位化/
├── main.tex                    # 第一冊總主控檔（含第一冊勘誤彙整表與全書目錄，共 186 頁）
├── main.pdf                    # 第一冊編譯產出之高畫質 PDF（第一至七章完整收錄）
├── main_B2.tex                 # 第二冊總主控檔（含第二冊勘誤彙整表與全書目錄）
├── main_B2.pdf                 # 第二冊編譯產出之高畫質 PDF（目前含第一章，共 24 頁）
├── README.md                   # 專案架構與編譯導覽說明
├── .gitignore                  # Git 忽略設定（排除暫存編譯檔與原始掃描檔）
│
├── styles/                     # 全域巨集與樣式設定模組
│   ├── preamble.tex            # 巨集套件引入（geometry, xeCJK, amsmath, tikz, hyperref 等）
│   ├── Chinese_math_style.tex  # 中文數學專用定理環境設定（definition, theorem, example 等）
│   └── math_style.tex          # 常用數學運算符號與縮寫指令
│
├── chapters/                   # 第一冊各章原始碼與獨立編譯測試模組
│   ├── Chapter1.tex / Chapter1_main.tex / Chapter1_main.pdf   # 第一章「引言」
│   ├── Chapter2.tex / Chapter2_main.tex / Chapter2_main.pdf   # 第二章「符號用法、基本數學語句及集合的概念」
│   ├── Chapter3.tex / Chapter3_main.tex / Chapter3_main.pdf   # 第三章「數的概念」
│   ├── Chapter4.tex / Chapter4_main.tex / Chapter4_main.pdf   # 第四章「一次方程式」
│   ├── Chapter5.tex / Chapter5_main.tex / Chapter5_main.pdf   # 第五章「多項式及其運算」
│   ├── Chapter6.tex / Chapter6_main.tex / Chapter6_main.pdf   # 第六章「整數的因子分解」
│   ├── Chapter7.tex / Chapter7_main.tex / Chapter7_main.pdf   # 第七章「多項式的因子分解」
│   │
│   └── B2/                     # 第二冊各章模組
│       ├── Chapter1.tex        # 第二冊第一章「二次方程式」正文原始碼
│       ├── Chapter1_main.tex   # 第二冊第一章獨立編譯主檔
│       └── Chapter1_main.pdf   # 第二冊第一章單獨產出 PDF（共 24 頁）
│
└── original_scans/             # 教材原始高解析度掃描檔（已於 .gitignore 排除）
    ├── B1/                     # 第一冊各章原始掃描檔 (Ch1–Ch7)
    └── B2/                     # 第二冊原始掃描檔 (Ch1–Ch5 及目錄)
```

---

## 編譯說明

本專案使用 `XeLaTeX` 進行編譯，以確保中文與數學字型正常渲染：

### 1. 編譯全冊主檔
在專案根目錄下執行：
```bash
xelatex main.tex
xelatex main.tex
```

### 2. 單獨編譯特定章節
在 `chapters/` 目錄下執行對應的獨立主檔：
```bash
cd chapters
xelatex Chapter1_main.tex
xelatex Chapter2_main.tex
xelatex Chapter3_main.tex
xelatex Chapter4_main.tex
xelatex Chapter5_main.tex
xelatex Chapter6_main.tex
xelatex Chapter7_main.tex
```

---

## 各章進度與收錄狀態

### 第一冊（高一上，1973年修訂版）— 100% 已完成

| 章節 | 章節全名 | 狀態 | 原始掃描頁數 | 產出 PDF 頁數 |
| :--- | :--- | :---: | :---: | :---: |
| **第一章** | 引言 | **已完成** | 12 頁 | 6 頁 |
| **第二章** | 符號用法、基本數學語句及集合的概念 | **已完成** | 33 頁 | 33 頁 |
| **第三章** | 數的概念 | **已完成** | 29 頁 | 26 頁 |
| **第四章** | 一次方程式 | **已完成** | 31 頁 | 34 頁 |
| **第五章** | 多項式及其運算 | **已完成** | 40 頁 | 39 頁 |
| **第六章** | 整數的因子分解 | **已完成** | 21 頁 | 22 頁 |
| **第七章** | 多項式的因子分解 | **已完成** | 35 頁 | 35 頁 |

### 第二冊（高一下，1973年初版）— 進行中

全冊總控主檔：`main_B2.tex` / 產出：`main_B2.pdf`

| 章節 | 章節全名 | 狀態 | 原始掃描頁數 | 產出 PDF 頁數 |
| :--- | :--- | :---: | :---: | :---: |
| **第一章** | 二次方程式 | **已完成** | 23 頁 | 24 頁 |
| **第二章** | 次序與極限觀念 | 待轉錄 | 34 頁 | — |
| **第三章** | 實數系及其基本性質 | 待轉錄 | 20 頁 | — |
| **第四章** | 指數函數與對數函數 | 待轉錄 | 32 頁 | — |
| **第五章** | 對數表的用法與計算尺原理* | 待轉錄 | 12+ 頁 | — |

