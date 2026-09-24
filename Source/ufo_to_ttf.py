#!/usr/bin/env python3
"""
Convert all 3 Nokora UFO sources to TTF using FontForge.

Run with FontForge's own python, NOT system python3:
    
    fontforge -script ufo_to_ttf.py


"""

import fontforge

FILES = [
    ("UFO3/Nokora-Thin.ufo", "Nokora-Thin.ttf"),
    ("UFO3/Nokora-Regular.ufo", "Nokora-Regular.ttf"),
    ("UFO3/Nokora-Black.ufo", "Nokora-Black.ttf"),
]

def convert(ufo_path, ttf_path):
    print(f"Converting {ufo_path} -> {ttf_path}")
    font = fontforge.open(ufo_path)
    font.generate(ttf_path)
    font.close()
    print(f"  Done: {ttf_path}")

def main():
    for ufo_path, ttf_path in FILES:
        try:
            convert(ufo_path, ttf_path)
        except Exception as e:
            print(f"  FAILED: {ufo_path} -> {e}")

if __name__ == "__main__":
    main()