#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$SCRIPT_DIR/bin"

echo "Building pdf_tool..."
clang -O2 -fobjc-arc -framework Cocoa -framework PDFKit \
  "$SCRIPT_DIR/src/pdf_tool.m" -o "$SCRIPT_DIR/bin/pdf_tool"

echo "Building vision_ocr..."
clang -O2 -fobjc-arc -framework Cocoa -framework PDFKit -framework Vision \
  "$SCRIPT_DIR/src/vision_ocr.m" -o "$SCRIPT_DIR/bin/vision_ocr"

echo "Building pdf_compare..."
clang -O2 -fobjc-arc -framework Cocoa -framework PDFKit \
  "$SCRIPT_DIR/src/pdf_compare.m" -o "$SCRIPT_DIR/bin/pdf_compare"

echo "Done! Binaries built in $SCRIPT_DIR/bin/"
