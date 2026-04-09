#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compare_cpu_pl_preproc.py

Runs CPU reference preprocessing and PL (pp_pipeline_accel) preprocessing on the
same images, compares outputs, and reports timing.

CPU reference is written to MATCH your HLS kernel exactly:

HLS kernel behavior (from your C++):
- Output is always 224x224x3 int8 (RGB order)
- Nearest-neighbor sampling:
    src_y = (y * in_h) / 224   (integer trunc)
    src_x = (x * in_w) / 224
- Input is BGR uint8
- Reorder BGR -> RGB
- Quantize (integer truncation):
    q = (val * fix_scale) / 255

PL kernel signature (from embedded metadata):
  pp_pipeline_accel(in_bgr*, out_rgb_q*, in_w, in_h, fix_scale)

Notes on pyxrt differences on your image:
- xrt.kernel() does NOT accept a CU instance name string; use xrt.kernel(dev, uuid, name)
- bo.read() on your build doesn't support reading into a numpy array, and returns empty in your case.
  We use bo.map() + np.frombuffer() after sync instead (more robust).
"""

import os
import time
import argparse
from typing import List

import cv2
import numpy as np
import pyxrt as xrt

DEFAULT_XCLBIN = "/lib/firmware/xilinx/tria-u96v2-accel-dpu/tria-u96v2-accel-dpu.xclbin"
KERNEL_NAME = "pp_pipeline_accel"

OUT_W = 224
OUT_H = 224
OUT_NBYTES = OUT_W * OUT_H * 3  # int8 bytes


def list_images(image_dir: str, limit: int = 0) -> List[str]:
    exts = (".jpg", ".jpeg", ".png", ".bmp")
    files = sorted(
        os.path.join(image_dir, f)
        for f in os.listdir(image_dir)
        if f.lower().endswith(exts)
    )
    if limit and limit > 0:
        files = files[:limit]
    return files


def load_bgr_u8(image_path: str) -> np.ndarray:
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)  # BGR uint8
    if img is None:
        raise RuntimeError(f"cv2.imread failed for: {image_path}")
    return np.ascontiguousarray(img, dtype=np.uint8)


def cpu_reference_like_hls(in_bgr: np.ndarray, fix_scale: int) -> np.ndarray:
    """
    CPU reference that matches your HLS kernel exactly.
    Returns (224,224,3) int8 RGB.
    """
    in_h, in_w = in_bgr.shape[:2]
    out = np.empty((OUT_H, OUT_W, 3), dtype=np.int8)
    fs = int(fix_scale)

    for y in range(OUT_H):
        src_y = (y * in_h) // OUT_H
        row = in_bgr[src_y]  # (in_w,3)
        for x in range(OUT_W):
            src_x = (x * in_w) // OUT_W
            b, g, r = row[src_x]

            rq = (int(r) * fs) // 255
            gq = (int(g) * fs) // 255
            bq = (int(b) * fs) // 255

            out[y, x, 0] = np.int8(rq)
            out[y, x, 1] = np.int8(gq)
            out[y, x, 2] = np.int8(bq)

    return out


def compare_outputs(cpu_rgb_q: np.ndarray, pl_rgb_q: np.ndarray):
    """
    Return (exact_match, max_abs_diff, mismatched_elements)
    """
    if cpu_rgb_q.shape != pl_rgb_q.shape:
        return False, 127, cpu_rgb_q.size

    diff = cpu_rgb_q.astype(np.int16) - pl_rgb_q.astype(np.int16)
    mism = int(np.count_nonzero(diff))
    max_abs = int(np.max(np.abs(diff))) if mism else 0
    return mism == 0, max_abs, mism


class PLPreprocessor:
    """
    PL pp_pipeline_accel driver using pyxrt.

    For meaningful timing later, this class REUSES BOs:
      - input BO is resized when needed (if a new image has different in_w/in_h)
      - output BO is fixed (224*224*3 bytes)
    """

    def __init__(self, xclbin_path: str = DEFAULT_XCLBIN, device_index: int = 0):
        self.dev = xrt.device(device_index)
        self.uuid = self.dev.load_xclbin(xrt.xclbin(xclbin_path))

        # Your pyxrt build supports:
        #   xrt.kernel(device, uuid, name)
        self.krnl = xrt.kernel(self.dev, self.uuid, KERNEL_NAME)

        self.bo_in = None
        self.bo_in_bytes = 0
        self.bo_out = xrt.bo(self.dev, OUT_NBYTES, xrt.bo.flags.cacheable, self.krnl.group_id(1))

        # Cache the mapped output memoryview once (valid for life of BO)
        self.bo_out_mv = self.bo_out.map()

    def _ensure_in_bo(self, nbytes: int):
        if (self.bo_in is None) or (nbytes != self.bo_in_bytes):
            self.bo_in = xrt.bo(self.dev, nbytes, xrt.bo.flags.cacheable, self.krnl.group_id(0))
            self.bo_in_bytes = nbytes

    def run(self, in_bgr_u8: np.ndarray, fix_scale: int) -> np.ndarray:
        """
        in_bgr_u8: HxWx3 uint8 (BGR), contiguous
        returns:   224x224x3 int8 (RGB quantized)
        """
        if in_bgr_u8.dtype != np.uint8:
            raise ValueError("PL input must be uint8 BGR")
        if in_bgr_u8.ndim != 3 or in_bgr_u8.shape[2] != 3:
            raise ValueError("PL input must be HxWx3")
        if not in_bgr_u8.flags["C_CONTIGUOUS"]:
            in_bgr_u8 = np.ascontiguousarray(in_bgr_u8)

        in_h, in_w = in_bgr_u8.shape[:2]
        self._ensure_in_bo(in_bgr_u8.nbytes)

        # Write input
        self.bo_in.write(in_bgr_u8, 0)
        self.bo_in.sync(xrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE)

        # Launch kernel: (in_bgr*, out_rgb_q*, in_w, in_h, fix_scale)
        run = self.krnl(self.bo_in, self.bo_out,
                        np.uint32(in_w), np.uint32(in_h), np.uint32(fix_scale))
        run.wait()

        # Sync back output
        self.bo_out.sync(xrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE)

        # Read using map() (robust across your pyxrt build)
        raw_u8 = np.frombuffer(self.bo_out_mv, dtype=np.uint8, count=OUT_NBYTES)
        out_rgb_q = raw_u8.view(np.int8).reshape((OUT_H, OUT_W, 3)).copy()
        return out_rgb_q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--image_dir", type=str, default="images")
    ap.add_argument("-n", "--limit", type=int, default=0)
    ap.add_argument("--fix_point", type=int, default=6)
    ap.add_argument("--xclbin", type=str, default=DEFAULT_XCLBIN)
    ap.add_argument("--device", type=int, default=0)
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--check_first", type=int, default=10,
                    help="Compare outputs for first N images (0 = all)")
    args = ap.parse_args()

    fix_scale = 1 << args.fix_point
    files = list_images(args.image_dir, args.limit)

    if not files:
        print(f"No images found in {args.image_dir}")
        return

    print(f"Images: {len(files)}")
    print(f"fix_point: {args.fix_point} fix_scale: {fix_scale}")
    print(f"xclbin: {args.xclbin}")
    print(f"device: {args.device}")
    print(f"PL output: {OUT_W}x{OUT_H} RGB int8 (matches your HLS)")

    # Init PL
    pl = PLPreprocessor(args.xclbin, args.device)

    # Warmup
    for _ in range(max(0, args.warmup)):
        bgr = load_bgr_u8(files[0])
        _ = pl.run(bgr, fix_scale)

    # CPU preprocess all
    cpu_outs = []
    t0 = time.perf_counter()
    for p in files:
        bgr = load_bgr_u8(p)
        cpu_outs.append(cpu_reference_like_hls(bgr, fix_scale))
    t1 = time.perf_counter()
    cpu_total = t1 - t0

    # PL preprocess all
    pl_outs = []
    t2 = time.perf_counter()
    for p in files:
        bgr = load_bgr_u8(p)
        pl_outs.append(pl.run(bgr, fix_scale))
    t3 = time.perf_counter()
    pl_total = t3 - t2

    # Compare
    to_check = len(files) if args.check_first == 0 else min(args.check_first, len(files))
    exact_all = True
    worst = {"file": None, "max_abs": 0, "mism": 0}

    for i in range(to_check):
        exact, max_abs, mism = compare_outputs(cpu_outs[i], pl_outs[i])
        if not exact:
            exact_all = False
        if max_abs > worst["max_abs"] or mism > worst["mism"]:
            worst = {"file": os.path.basename(files[i]), "max_abs": max_abs, "mism": mism}

    # Report timing
    n = len(files)
    print("\n--- Timing ---")
    print(f"CPU: {n} images in {cpu_total:.4f}s => {n/cpu_total:.2f} img/s ({cpu_total/n*1000:.3f} ms/img)")
    print(f"PL : {n} images in {pl_total:.4f}s => {n/pl_total:.2f} img/s ({pl_total/n*1000:.3f} ms/img)")

    # Report compare
    print("\n--- Output compare (CPU ref vs PL) ---")
    if exact_all:
        print(f"✅ Exact match on first {to_check} images.")
    else:
        print(f"❌ MISMATCH on first {to_check} images.")
        print(f"Worst: file={worst['file']} max_abs_diff={worst['max_abs']} mismatched_elements={worst['mism']}")
        if worst["file"] is not None:
            idx = [os.path.basename(f) for f in files].index(worst["file"])
            print("CPU first 24:", cpu_outs[idx].reshape(-1)[:24].tolist())
            print("PL  first 24:", pl_outs[idx].reshape(-1)[:24].tolist())

    print()


if __name__ == "__main__":
    main()
