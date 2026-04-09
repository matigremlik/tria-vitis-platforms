#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import argparse
import random
from typing import List, Tuple

import cv2
import numpy as np
import pyxrt as xrt

DEFAULT_XCLBIN = "/lib/firmware/xilinx/tria-u96v2-accel-dpu/tria-u96v2-accel-dpu.xclbin"
KERNEL_NAME = "pp_pipeline_accel"

OUT_W = 224
OUT_H = 224
OUT_NBYTES = OUT_W * OUT_H * 3  # int8 bytes


# ===== CPU preprocess copied from app_mt.py (exactly) =====
def preprocess_fn_cpu_appmt_style(image_path: str, fix_scale: int) -> np.ndarray:
    image = cv2.imread(image_path)
    if image is None:
        raise RuntimeError(f"cv2.imread failed for: {image_path}")
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = (image / 255.0) * fix_scale
    image = image.astype(np.int8)
    return image


def list_images_all(image_dir: str) -> List[str]:
    exts = (".jpg", ".jpeg", ".png", ".bmp")
    files = [
        os.path.join(image_dir, f)
        for f in os.listdir(image_dir)
        if f.lower().endswith(exts)
    ]
    files.sort()
    return files


def pick_random_images(files: List[str], n: int, seed: int | None) -> List[str]:
    if n <= 0 or n >= len(files):
        # n==0 means "all"
        picked = files[:]
    else:
        rng = random.Random(seed)
        picked = rng.sample(files, n)  # unique random sample

    # Randomize processing order (helps avoid “same order” effects)
    rng2 = random.Random(None if seed is None else seed + 1)
    rng2.shuffle(picked)
    return picked


def load_bgr_u8(image_path: str) -> np.ndarray:
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)  # BGR uint8
    if img is None:
        raise RuntimeError(f"cv2.imread failed for: {image_path}")
    return np.ascontiguousarray(img, dtype=np.uint8)


def compare_arrays(cpu_rgb_q: np.ndarray, pl_rgb_q: np.ndarray) -> Tuple[bool, int, int]:
    if cpu_rgb_q.shape != pl_rgb_q.shape:
        return False, 127, cpu_rgb_q.size
    diff = cpu_rgb_q.astype(np.int16) - pl_rgb_q.astype(np.int16)
    mism = int(np.count_nonzero(diff))
    max_abs = int(np.max(np.abs(diff))) if mism else 0
    return (mism == 0), max_abs, mism


class PLPreprocessor:
    def __init__(self, xclbin_path: str, device_index: int):
        self.dev = xrt.device(device_index)
        self.uuid = self.dev.load_xclbin(xrt.xclbin(xclbin_path))
        self.krnl = xrt.kernel(self.dev, self.uuid, KERNEL_NAME)

        # Reuse BOs
        self.bo_in = None
        self.bo_in_bytes = 0

        self.bo_out = xrt.bo(self.dev, OUT_NBYTES, xrt.bo.flags.cacheable, self.krnl.group_id(1))
        self.bo_out_mv = self.bo_out.map()

    def _ensure_in_bo(self, nbytes: int):
        if self.bo_in is None or nbytes != self.bo_in_bytes:
            self.bo_in = xrt.bo(self.dev, nbytes, xrt.bo.flags.cacheable, self.krnl.group_id(0))
            self.bo_in_bytes = nbytes

    def run(self, in_bgr_u8: np.ndarray, in_w: int, in_h: int, fix_scale: int) -> np.ndarray:
        if in_bgr_u8.dtype != np.uint8 or in_bgr_u8.ndim != 3 or in_bgr_u8.shape[2] != 3:
            raise ValueError("Input must be HxWx3 uint8 (BGR).")
        if not in_bgr_u8.flags["C_CONTIGUOUS"]:
            in_bgr_u8 = np.ascontiguousarray(in_bgr_u8)

        self._ensure_in_bo(in_bgr_u8.nbytes)

        self.bo_in.write(in_bgr_u8, 0)
        self.bo_in.sync(xrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)

        run = self.krnl(self.bo_in, self.bo_out,
                        np.uint32(in_w), np.uint32(in_h), np.uint32(fix_scale))
        run.wait()

        self.bo_out.sync(xrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)

        raw_u8 = np.frombuffer(self.bo_out_mv, dtype=np.uint8, count=OUT_NBYTES)
        out_rgb_q = raw_u8.view(np.int8).reshape((OUT_H, OUT_W, 3)).copy()
        return out_rgb_q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--image_dir", type=str, default="images")
    ap.add_argument("-n", "--limit", type=int, default=0, help="Number of random images to use (0=all)")
    ap.add_argument("--seed", type=int, default=None, help="Random seed (optional, for repeatability)")
    ap.add_argument("--fix_point", type=int, default=6)
    ap.add_argument("--xclbin", type=str, default=DEFAULT_XCLBIN)
    ap.add_argument("--device", type=int, default=0)
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--check_first", type=int, default=10, help="Compare first N images (0=all)")
    ap.add_argument("--require_224", action="store_true", default=True,
                    help="Skip images not 224x224 (default True; matches app_mt assumptions)")
    ap.add_argument("--allow_non224", action="store_true",
                    help="If set, we will still run PL, but CPU/PL shapes will differ and comparison will be skipped.")
    args = ap.parse_args()

    if args.allow_non224:
        args.require_224 = False

    fix_scale = 1 << args.fix_point

    all_files = list_images_all(args.image_dir)
    if not all_files:
        print(f"No images found in {args.image_dir}")
        return

    picked = pick_random_images(all_files, args.limit, args.seed)

    print(f"Images (found): {len(all_files)}")
    print(f"Images (picked): {len(picked)} (random sample)")
    print(f"seed: {args.seed}")
    print(f"fix_point: {args.fix_point} fix_scale: {fix_scale}")
    print(f"xclbin: {args.xclbin}")
    print(f"device: {args.device}")
    print(f"Comparison mode: CPU preprocess EXACTLY app_mt.py (no resize, float math)")

    pl = PLPreprocessor(args.xclbin, args.device)

    # Filter by size if required
    usable = []
    skipped = 0
    for p in picked:
        bgr = cv2.imread(p, cv2.IMREAD_COLOR)
        if bgr is None:
            skipped += 1
            continue
        h, w = bgr.shape[:2]
        if args.require_224 and (w != OUT_W or h != OUT_H):
            skipped += 1
            continue
        usable.append(p)

    if not usable:
        print("No usable images after filtering. If your dataset isn't 224x224, your app_mt.py would also break.")
        return

    if skipped:
        print(f"Usable images: {len(usable)} (skipped {skipped} due to size/read issues)")

    # Warmup PL
    for _ in range(max(0, args.warmup)):
        bgr = load_bgr_u8(usable[0])
        h, w = bgr.shape[:2]
        _ = pl.run(bgr, w, h, fix_scale)

    # CPU
    cpu_outs = []
    t0 = time.perf_counter()
    for p in usable:
        cpu_outs.append(preprocess_fn_cpu_appmt_style(p, fix_scale))
    t1 = time.perf_counter()
    cpu_total = t1 - t0

    # PL
    pl_outs = []
    t2 = time.perf_counter()
    for p in usable:
        bgr = load_bgr_u8(p)
        h, w = bgr.shape[:2]
        pl_outs.append(pl.run(bgr, w, h, fix_scale))
    t3 = time.perf_counter()
    pl_total = t3 - t2

    # Compare
    to_check = len(usable) if args.check_first == 0 else min(args.check_first, len(usable))
    exact_all = True
    worst = {"file": None, "max_abs": 0, "mism": 0}
    compared = 0

    for i in range(to_check):
        cpu_arr = cpu_outs[i]
        pl_arr = pl_outs[i]

        if cpu_arr.shape != pl_arr.shape:
            continue

        compared += 1
        exact, max_abs, mism = compare_arrays(cpu_arr, pl_arr)
        if not exact:
            exact_all = False
        if max_abs > worst["max_abs"] or mism > worst["mism"]:
            worst = {"file": os.path.basename(usable[i]), "max_abs": max_abs, "mism": mism}

    n = len(usable)
    print("\n--- Timing ---")
    print(f"CPU(app_mt.py): {n} images in {cpu_total:.4f}s => {n/cpu_total:.2f} img/s ({cpu_total/n*1000:.3f} ms/img)")
    print(f"PL(pp_pipeline): {n} images in {pl_total:.4f}s => {n/pl_total:.2f} img/s ({pl_total/n*1000:.3f} ms/img)")

    print("\n--- Output compare (CPU app_mt.py vs PL) ---")
    if compared == 0:
        print("No images were comparable (shape mismatch). This usually means your images aren't 224x224.")
        return

    if exact_all:
        print(f"✅ Exact match on {compared}/{to_check} compared images.")
    else:
        print(f"❌ MISMATCH on {compared}/{to_check} compared images.")
        print(f"Worst: file={worst['file']} max_abs_diff={worst['max_abs']} mismatched_elements={worst['mism']}")
        if worst["file"] is not None:
            idx = [os.path.basename(p) for p in usable].index(worst["file"])
            print("CPU first 24:", cpu_outs[idx].reshape(-1)[:24].tolist())
            print("PL  first 24:", pl_outs[idx].reshape(-1)[:24].tolist())
            print("\nNOTE: Differences of 1 can happen if PL uses integer (val*scale)//255 while CPU uses float (val/255.0)*scale.")


if __name__ == "__main__":
    main()
