# -*- coding: utf-8 -*-
"""
Quick test for DSPy modules
"""

import sys, io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

print("Testing DSPy modules import...")

try:
    from analyze.dspy_modules import (
        ContentSummarizer,
        GapAnalyzer,
        OutlineGenerator,
        init_dspy
    )
    print("✅ All DSPy modules imported successfully!")

    print("\nModule classes:")
    print(f"  - ContentSummarizer: {ContentSummarizer}")
    print(f"  - GapAnalyzer: {GapAnalyzer}")
    print(f"  - OutlineGenerator: {OutlineGenerator}")
    print(f"  - init_dspy function: {init_dspy}")

except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
