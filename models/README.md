# 模型清单

工作流里所有模型名都带 `Anima\` 前缀，对应 `ComfyUI/models/<类别>/Anima/` 子目录。**文件夹名大小写要和这里一致**（Windows 不敏感，但换到 Linux 会挂）。

## 必需文件

| 作用 | 文件名 | 放置路径 | 大小 |
|---|---|---|---|
| 主模型（UNet） | `anima_aestheticV11.safetensors` | `models/diffusion_models/Anima/` | 4.18 GB |
| 文本编码器 | `qwen_3_06b_base.safetensors` | `models/clip/Anima/` | 1.19 GB |
| VAE | `qwen_image_vae.safetensors` | `models/vae/Anima/` | 254 MB |

> 文本编码器放 `models/clip/` 或 `models/text_encoders/` 都能被 `CLIPLoader` 读到，取决于 ComfyUI 版本。v0.34 两个路径都支持，本机在 `clip/` 下。

三条硬性约束：

1. **VAE 必须与主模型同系列**。用 SD1.5 的 VAE 会出黑图或彩色噪点。
2. **`CLIPLoader` 的 type 是 `stable_diffusion`**，不要改成 `qwen_image` 之类。
3. 主模型是 fp16 的 4.18 GB，8 GB 卡上加载后几乎没有余量 —— 这是必须开 `--enable-dynamic-vram` 的原因。

## LoRA

放 `models/loras/Anima/`，共 9 个（工作流当前启用）：

| # | 文件名 | 大小 | 栈 | 强度 |
|---|---|---|---|---|
| 1 | `chen-bin_v4.0.safetensors` | 88 MB | 画风 | 0.60 |
| 2 | `gulugulu_v1_epoch26.safetensors` | 44 MB | 画风 | 0.60 |
| 3 | `A1kx_sty-v2.safetensors` | 53 MB | 画风 | 0.60 |
| 4 | `khstyle_v1_epoch26.safetensors` | 44 MB | 画风 | 0.30 |
| 5 | `gpt-image-2_anima-base1_v1-1.safetensors` | 22 MB | 画风 | 0.30 |
| 6 | `semi-realisticV3.5.safetensors` | 132 MB | 画质 | 0.50 |
| 7 | `Anima_in_real_update_v2_epoch_20.safetensors` | 264 MB | 画质 | 0.50 |
| 8 | `anima-highres-aesthetic-boost.safetensors` | 132 MB | 画质 | 0.50 |
| 9 | `anima_context_detailer_base10.safetensors` | 88 MB | 画质 | 0.70 |

合计约 870 MB。

### 这些模型从哪来

它们都属于 **Anima** 这个动漫底模生态，主要来源是 Civitai 和作者发布的网盘。本仓库**不分发模型文件**，原因有两个：体积太大，以及各模型的授权各不相同（部分禁止再分发）。

找的办法：在 Civitai 按**完整文件名**搜索（文件名就是原作者的命名，一字不差能搜到）。搜不到的多半是整合包内附的，本机环境来自「机智整合包 V5 RDNA1」。

### 只用 5 个 LoRA 也能跑

如果只想要一份能出图的最小集合，保留 3、5、6、8、9 这五个就够（画风打底 + 画质补细节）。删掉的 4 个不会让工作流报错，`easy loraStack` 里把对应槽位设成 `None` 或把 `num_loras` 调小即可。

风格差异会明显，但**速度几乎不变** —— 原因见 [../docs/02-performance.md](../docs/02-performance.md)。

## 目录预览

```
ComfyUI/models/
├── diffusion_models/
│   └── Anima/
│       └── anima_aestheticV11.safetensors        4.18 GB
├── clip/
│   └── Anima/
│       └── qwen_3_06b_base.safetensors           1.19 GB
├── vae/
│   └── Anima/
│       └── qwen_image_vae.safetensors             254 MB
└── loras/
    └── Anima/
        ├── A1kx_sty-v2.safetensors                 53 MB
        ├── Anima_in_real_update_v2_epoch_20...    264 MB
        ├── anima-highres-aesthetic-boost...       132 MB
        ├── anima_context_detailer_base10...        88 MB
        ├── chen-bin_v4.0.safetensors               88 MB
        ├── gpt-image-2_anima-base1_v1-1...         22 MB
        ├── gulugulu_v1_epoch26.safetensors         44 MB
        ├── khstyle_v1_epoch26.safetensors          44 MB
        └── semi-realisticV3.5.safetensors         132 MB
```

## 模型放别的盘

把 `config/extra_model_paths.yaml.example` 复制成 `ComfyUI/extra_model_paths.yaml` 并改路径。示例里 D 盘是机械盘、只放冷模型，E 盘 SSD 的 `models/` 始终优先。

注意：`is_default: false` 表示只追加搜索路径，不覆盖主目录 —— 想要"多盘合并"就必须保持 false。
