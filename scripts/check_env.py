# -*- coding: utf-8 -*-
"""
环境自检：确认 ROCm / torch / 显存 / 模型文件 / 自定义节点是否就位。

用法:
    python scripts/check_env.py                     # 自动猜 ComfyUI 路径
    python scripts/check_env.py --comfy E:\\AI\\ComfyUI
"""
from __future__ import annotations

import argparse
import os
import sys

OK = "[ OK ]"
WARN = "[WARN]"
FAIL = "[FAIL]"

results = []


def record(level: str, title: str, detail: str = "") -> None:
    results.append((level, title, detail))
    line = f"{level} {title}"
    if detail:
        line += f"  -> {detail}"
    print(line)


def check_torch() -> bool:
    try:
        import torch
    except Exception as e:  # noqa: BLE001
        record(FAIL, "import torch", repr(e))
        return False

    record(OK, "torch", torch.__version__)

    hip = getattr(torch.version, "hip", None)
    if hip:
        record(OK, "HIP runtime", str(hip))
    else:
        record(FAIL, "HIP runtime", "torch.version.hip 为 None，装的是 CPU wheel")

    if not torch.cuda.is_available():
        record(FAIL, "torch.cuda.is_available()", "False，检查 SDK wheel 与驱动")
        return False

    name = torch.cuda.get_device_name(0)
    total = torch.cuda.get_device_properties(0).total_memory / 1024**3
    record(OK, "device 0", f"{name}  {total:.1f} GB")
    if "5700" not in name and "gfx101" not in name.lower():
        record(WARN, "GPU 型号", "不是 RX 5700 XT，参数可能需要调整")

    # 真正跑一次矩阵乘法，触发 kernel 加载
    try:
        a = torch.randn(512, 512, device="cuda", dtype=torch.float16)
        b = torch.randn(512, 512, device="cuda", dtype=torch.float16)
        c = (a @ b).float().sum().item()
        record(OK, "fp16 matmul", f"sum={c:.2f}")
    except Exception as e:  # noqa: BLE001
        record(FAIL, "fp16 matmul", repr(e))
        return False
    return True


MODELS = {
    "diffusion_models/Anima/anima_aestheticV11.safetensors": "主模型",
    "clip/Anima/qwen_3_06b_base.safetensors": "文本编码器",
    "vae/Anima/qwen_image_vae.safetensors": "VAE",
    "loras/Anima/chen-bin_v4.0.safetensors": "LoRA 画风 1",
    "loras/Anima/gulugulu_v1_epoch26.safetensors": "LoRA 画风 2",
    "loras/Anima/A1kx_sty-v2.safetensors": "LoRA 画风 3",
    "loras/Anima/khstyle_v1_epoch26.safetensors": "LoRA 画风 4",
    "loras/Anima/gpt-image-2_anima-base1_v1-1.safetensors": "LoRA 画风 5",
    "loras/Anima/semi-realisticV3.5.safetensors": "LoRA 画质 1",
    "loras/Anima/Anima_in_real_update_v2_epoch_20.safetensors": "LoRA 画质 2",
    "loras/Anima/anima-highres-aesthetic-boost.safetensors": "LoRA 画质 3",
    "loras/Anima/anima_context_detailer_base10.safetensors": "LoRA 画质 4",
}

ALT_CLIP = "text_encoders/Anima/qwen_3_06b_base.safetensors"

NODES = {
    "comfyui-easy-use": "easy loraStack / loraStackApply",
    "ComfyUI-Custom-Scripts": "ShowText|pysssss",
}


def guess_comfy() -> str | None:
    for env in ("COMFY_PATH", "COMFYUI_PATH"):
        if os.environ.get(env):
            return os.environ[env]
    here = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.abspath(os.path.join(here, "..", "..", "..", "ComfyUI"))
    return cand if os.path.isdir(cand) else None


def check_models(comfy: str) -> None:
    base = os.path.join(comfy, "models")
    missing = []
    for rel, label in MODELS.items():
        path = os.path.join(base, rel.replace("/", os.sep))
        if os.path.isfile(path):
            size = os.path.getsize(path) / 1024**3
            record(OK, f"{label}", f"{rel}  {size:.2f} GB")
        elif rel.startswith("clip/") and os.path.isfile(
            os.path.join(base, ALT_CLIP.replace("/", os.sep))
        ):
            record(OK, f"{label}", f"{ALT_CLIP}（在 text_encoders/ 下）")
        else:
            record(FAIL, f"{label} 缺失", rel)
            missing.append(rel)
    if missing:
        print(f"\n共 {len(missing)} 个文件缺失，对照 models/README.md 补齐。")


def check_nodes(comfy: str) -> None:
    dir_ = os.path.join(comfy, "custom_nodes")
    for pkg, what in NODES.items():
        if os.path.isdir(os.path.join(dir_, pkg)):
            record(OK, f"自定义节点 {pkg}", what)
        else:
            record(FAIL, f"自定义节点 {pkg} 缺失", what)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--comfy", default=None, help="ComfyUI 根目录")
    args = ap.parse_args()

    print("=" * 62)
    print(" ComfyUI / ROCm (gfx1010) 环境自检")
    print("=" * 62)

    ok_gpu = check_torch()

    comfy = args.comfy or guess_comfy()
    print()
    if comfy and os.path.isdir(comfy):
        print(f"-- ComfyUI: {comfy}")
        check_models(comfy)
        check_nodes(comfy)
    else:
        record(WARN, "ComfyUI 目录", "未找到，跳过模型/节点检查（用 --comfy 指定）")

    fails = [r for r in results if r[0] == FAIL]
    warns = [r for r in results if r[0] == WARN]
    print("\n" + "=" * 62)
    print(f" 结果: {len(results) - len(fails) - len(warns)} 通过 / {len(warns)} 警告 / {len(fails)} 失败")
    print("=" * 62)

    if fails:
        print("\n失败项:")
        for _, title, detail in fails:
            print(f"  - {title}  {detail}")
        return 1
    if not ok_gpu:
        return 1
    print("\n环境可用，可以启动 ComfyUI 了。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
