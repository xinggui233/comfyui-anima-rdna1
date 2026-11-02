# ComfyUI · Anima on RX 5700 XT (RDNA1 / gfx1010)

A working ComfyUI workflow for the **Anima** anime model, tuned for **AMD RX 5700 XT (RDNA1, gfx1010, 8 GB VRAM)** on Windows with ROCm.

RDNA1 is not on AMD's validated architecture list, and most public workflows assume NVIDIA plus 12 GB+ VRAM. This repo fixes the non-obvious choices that make it actually run.

## Why this exists

| Problem | What this repo does |
|---|---|
| Official ROCm releases don't support gfx1010 | Pins the `rocm_sdk_libraries_gfx101x_dgpu` nightly wheels + matching torch build |
| 8 GB VRAM can't fit a 4 GB UNet plus hires pass | 768×1152 base → 1.3× latent upscale → tiled VAE decode |
| 9 chained `LoraLoader` nodes are slow to cold-start | Easy-Use `loraStack` chain (character → quality → style), applied once |
| `comfy-kitchen` HIP backend refuses gfx1010 | Documented as expected; falls back to eager, still works |

## Environment

| | |
|---|---|
| GPU | RX 5700 XT, 8 GB (gfx1010) |
| Python | 3.12.10 |
| PyTorch | `2.9.1+rocm7.12.0a20260207` (HIP 7.2.0) |
| ComfyUI | v0.34.4 |
| Launch | `python main.py --enable-dynamic-vram --auto-launch --port 8188` |

## Quick start

1. Install ROCm SDK wheels + matching torch — see [docs/01-environment.md](docs/01-environment.md) (Chinese).
2. Put the models under `ComfyUI/models/*/Anima/` — see [models/README.md](models/README.md).
3. Verify: `python scripts/check_env.py --comfy E:\AI\ComfyUI`
4. Launch with `scripts/launch_rdna1.bat`, then drag `workflows/anima_rdna1_txt2img_hires.json` into ComfyUI.

Custom nodes required: [ComfyUI-Easy-Use](https://github.com/yolain/ComfyUI-Easy-Use) and [ComfyUI-Custom-Scripts](https://github.com/pythongosssss/ComfyUI-Custom-Scripts).

## Pipeline

```
EmptyLatent 768×1152
  → KSampler #1 (30 steps, euler/simple, denoise 1.0)
  → LatentUpscaleBy 1.3× (998×1497)
  → KSampler #2 (15 steps, dpmpp_2m/karras, denoise 0.7)
  → VAEDecodeTiled (512 tile / 64 overlap)
  → SaveImage
```

LoRAs: 3 chains (character / quality / style) feeding one `loraStackApply`. 9 active LoRAs, total weight ≈ 3.6.

## Measured performance

RX 5700 XT 8 GB, 768×1152 → 1.3×, 9 LoRAs:

- Full image: **~12–13 min**
- Sampling: **26–32 s per step** (≈95% of total time)
- First cold start (MIOpen kernel build): **+5–10 min**

Speed scales with step count almost linearly. Removing LoRAs saves load time and VRAM but **not** sampling time. Details in [docs/02-performance.md](docs/02-performance.md).

## Known quirks

```
[WARNING] offload-arch failed with return code 1
Found comfy_kitchen backend hip: {'available': False, ... 'gfx1010'}
```

Both are expected on gfx1010, not misconfiguration. Full error catalogue: [docs/03-troubleshooting.md](docs/03-troubleshooting.md).

## License

Docs and scripts: MIT. Models and LoRAs keep their original licenses and are not distributed here.
