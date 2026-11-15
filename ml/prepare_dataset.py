"""Organise a raw waste image dataset into the 5 project classes and split it.

Input : a folder containing one sub-folder per original class, e.g.
        - TrashNet:             cardboard, glass, metal, paper, plastic, trash
        - Kaggle "Garbage Classification" (12 classes): battery, biological, brown-glass,
          cardboard, clothes, green-glass, metal, paper, plastic, shoes, trash, white-glass
Output: data/dataset/{train,val,test}/{plastic,paper,metal,glass,organic}/

Original classes that do not map to one of the five categories (e.g. trash, battery,
clothes, shoes) are skipped. Unreadable images are skipped and counted.
All images are re-saved resized (default 128x128) so training reads small files.

Usage:
    python ml/prepare_dataset.py --raw data/raw --out data/dataset --size 128
"""
import argparse
import random
import shutil
import sys
from pathlib import Path

import cv2

CLASS_MAP = {
    "plastic": "plastic",
    "paper": "paper",
    "cardboard": "paper",
    "metal": "metal",
    "glass": "glass",
    "brown-glass": "glass",
    "green-glass": "glass",
    "white-glass": "glass",
    "organic": "organic",
    "biological": "organic",
    "compost": "organic",
}
SPLITS = ("train", "val", "test")
EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--out", default="data/dataset")
    ap.add_argument("--size", type=int, default=128)
    ap.add_argument("--val", type=float, default=0.15)
    ap.add_argument("--test", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    raw, out = Path(args.raw), Path(args.out)
    if not raw.is_dir():
        sys.exit(f"Raw dataset folder not found: {raw}")

    # Gather images per target category (searching one level or two for class folders).
    per_class = {}
    for folder in sorted(p for p in raw.rglob("*") if p.is_dir()):
        target = CLASS_MAP.get(folder.name.lower())
        if not target:
            continue
        files = [f for f in folder.iterdir() if f.suffix.lower() in EXTS]
        per_class.setdefault(target, []).extend(files)

    if not per_class:
        sys.exit("No recognised class folders found. Check CLASS_MAP in this script.")
    missing = {"plastic", "paper", "metal", "glass", "organic"} - set(per_class)
    if missing:
        print(f"WARNING: no images for categories: {sorted(missing)}")

    if out.exists():
        shutil.rmtree(out)
    rng = random.Random(args.seed)
    bad = 0
    for cat, files in per_class.items():
        rng.shuffle(files)
        n = len(files)
        n_test, n_val = int(n * args.test), int(n * args.val)
        parts = {
            "test": files[:n_test],
            "val": files[n_test : n_test + n_val],
            "train": files[n_test + n_val :],
        }
        for split, items in parts.items():
            dest = out / split / cat
            dest.mkdir(parents=True, exist_ok=True)
            for i, f in enumerate(items):
                img = cv2.imread(str(f), cv2.IMREAD_COLOR)
                if img is None:
                    bad += 1
                    continue
                img = cv2.resize(img, (args.size, args.size), interpolation=cv2.INTER_AREA)
                cv2.imwrite(str(dest / f"{f.parent.name}_{i:05d}.jpg"), img)
        print(f"{cat:8s} total={n:5d} train={len(parts['train'])} val={len(parts['val'])} test={len(parts['test'])}")
    print(f"Done. Skipped unreadable images: {bad}. Output: {out}")


if __name__ == "__main__":
    main()
