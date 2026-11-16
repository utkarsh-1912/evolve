#!/usr/bin/env python3
"""Decode a QR PNG with OpenCV and compare it to the expected text (verifies @evolve/ui encodeQr/QRCode).
Usage: python verify_qr.py <png> <expected-text-file>   -> exit 0 and prints OK on an exact match."""
import pathlib
import sys

import cv2

img = cv2.imread(sys.argv[1])
if img is None:
    sys.exit("cannot read image")
img = cv2.copyMakeBorder(img, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=(255, 255, 255))
text, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
expected = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
if text != expected:
    sys.exit(f"MISMATCH: decoded {len(text)} chars, expected {len(expected)}")
print(f"OK: decoded {len(text)} chars")
