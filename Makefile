# 《高中數學實驗教材》全套十冊一鍵編譯 Makefile
# 原始主控檔位於 tex/，編譯中間檔輸出至 build/，最終成品輸出至 pdf/

PYTHON := python3
VERIFY := tools/verify_book.py

BOOKS := B1 B2 B3 B4 B5 B6 B3s B4s B5s B6s

.PHONY: all clean $(BOOKS)

all: $(BOOKS)

B1:
	$(PYTHON) $(VERIFY) tex/main_B1.tex --compile 2

B2:
	$(PYTHON) $(VERIFY) tex/main_B2.tex --compile 2

B3:
	$(PYTHON) $(VERIFY) tex/main_B3.tex --compile 2

B4:
	$(PYTHON) $(VERIFY) tex/main_B4.tex --compile 2

B5:
	$(PYTHON) $(VERIFY) tex/main_B5.tex --compile 2

B6:
	$(PYTHON) $(VERIFY) tex/main_B6.tex --compile 2

B3s:
	$(PYTHON) $(VERIFY) tex/main_B3_社會組.tex --compile 2

B4s:
	$(PYTHON) $(VERIFY) tex/main_B4_社會組.tex --compile 2

B5s:
	$(PYTHON) $(VERIFY) tex/main_B5_社會組.tex --compile 2

B6s:
	$(PYTHON) $(VERIFY) tex/main_B6_社會組.tex --compile 2

clean:
	rm -rf build/*
