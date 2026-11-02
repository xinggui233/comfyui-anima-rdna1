# 04 · 工作流参数说明

节点 ID 与 `workflows/anima_rdna1_txt2img_hires.json` 对应。

## 模型加载

| 节点 | 类型 | 值 | 说明 |
|---|---|---|---|
| 68 | `UNETLoader` | `Anima\anima_aestheticV11.safetensors`, `default` | Anima 主模型。`default` = 自动选 fp16 |
| 69 | `CLIPLoader` | `Anima\qwen_3_06b_base.safetensors`, `stable_diffusion` | Qwen3-0.6B 文本编码器。**type 不能改**，改了出黑图 |
| 67 | `VAELoader` | `Anima\qwen_image_vae.safetensors` | 必须与 UNet 同系列 |

> 文件名里的 `Anima\` 是子目录前缀，不是模型名的一部分。

## 采样

### 第一段（节点 76）— 出底图

| 参数 | 值 | 为什么 |
|---|---|---|
| `steps` | 30 | 底图决定构图和整体光影，30 步是画质拐点 |
| `cfg` | 7.0 | 7 偏低但稳，8 以上在 RDNA1 上容易过曝/糊 |
| `sampler` | `euler` | 每步耗时最低，30 步足以收敛 |
| `scheduler` | `simple` | 与 euler 搭配最稳 |
| `denoise` | 1.0 | 从纯噪声开始 |
| `seed` | 由节点 6 `PrimitiveInt` 提供，`fixed` | **两段采样共享同一种子**，保证放大后构图不跑偏 |

### 放大（节点 28）

| 参数 | 值 | 说明 |
|---|---|---|
| `upscale_method` | `nearest-exact` | 潜空间放大，不引入插值模糊 |
| `scale_by` | 1.3 | 768×1152 → 998×1497。8 GB 卡的甜点，1.5 开始爆显存 |

### 第二段（节点 75）— 补细节

| 参数 | 值 | 为什么 |
|---|---|---|
| `steps` | 15 | denoise 0.7 只需要补形，不需要重画 |
| `cfg` | 7.0 | 与第一段一致，避免风格断层 |
| `sampler` | `dpmpp_2m` | 高阶采样器，denoise < 1 时细节恢复明显优于 euler |
| `scheduler` | `karras` | 降噪曲线更贴合重绘场景 |
| `denoise` | 0.7 | 0.5 太肉，0.85 会改动五官 |

## LoRA 栈

三个 `easy loraStack` 首尾相接（106 → 103 → 81），最后统一进 86 `easy loraStackApply`。

链式拼接的好处：每个栈负责一类语义，调参时只动一类，不用在 9 个节点里找。`loraStackApply` 只做一次模型包装，比 9 个 `LoraLoader` 串联省 8 次包装开销。

> `easy loraStack` 的 `simple` 模式下，每个 LoRA 有 4 个控件：`name / strength / model_strength / clip_strength`，但只有第一个强度生效，后两个留默认 1.0 即可（切到 `advanced` 才分开控制）。`num_loras` 是**生效槽位数**，超出的槽位即使填了也不加载。

### 节点 106「人物」— 当前 0 个

| 槽位 | LoRA | 强度 |
|---|---|---|
| 1 | `None` | — |

留空是刻意的：角色 LoRA 换得最勤，单独一层方便整体替换，不污染画风和画质两层。

### 节点 103「画质和细节」— 4 个

| LoRA | 强度 | 作用 |
|---|---|---|
| `semi-realisticV3.5` | 0.5 | 半写实质感 |
| `Anima_in_real_update_v2_epoch_20` | 0.5 | 写实向微调 |
| `anima-highres-aesthetic-boost` | 0.5 | 高分辨率审美倾向，配合第二段采样 |
| `anima_context_detailer_base10` | 0.7 | 细节补充，权重最高 |

### 节点 81「画风」— 5 个

| LoRA | 强度 | 作用 |
|---|---|---|
| `chen-bin_v4.0` | 0.6 | 画师风格 |
| `gulugulu_v1_epoch26` | 0.6 | 画师风格 |
| `A1kx_sty-v2` | 0.6 | 画师风格 |
| `khstyle_v1_epoch26` | 0.3 | 画师风格，低权重混色 |
| `gpt-image-2_anima-base1_v1-1` | 0.3 | 出图审美倾向修正 |

**总强度 ≈ 3.6**（画风层 2.4 + 画质层 2.2 已互相压制）。超过 4 会开始出现"糊成一团"的风格均值化，这时候不是加步数能救的，要降权重。

## 提示词

结构：

```
节点 91 正面 ─┐
              ├→ 102 StringConcatenate ─→ 93 StringConcatenate(", ") ─→ 57 ShowText ─→ 20 CLIPTextEncode ─→ 采样器
节点 94 正面2 ┘

节点 5  负面 ─→ 21 CLIPTextEncode ─→ 采样器
```

- **正面拆两段**：91 放"主体 + 服饰"，94 放"场景 + 镜头 + 光线"。改场景时只动 94，主体描述不受影响。
- **拼接线用 `, ` 作分隔符**，别用换行 —— CLIP 对换行的处理在不同版本不一致。
- **57 `ShowText` 只是显示拼接结果**，同时把最终字符串送进编码器。它不参与计算，但删了会断链。

Anima 的负面提示词不需要很长。本工作流的负面分四组：画质缺陷 / 人体结构 / 水印文字 / 色调过处理。再加词收益递减，反而挤占 token。

## 解码与保存

| 节点 | 类型 | 值 | 说明 |
|---|---|---|---|
| 52 | `VAEDecode` | — | 第一段采样后的**预览**解码，配合 63 `PreviewImage` |
| 96 | `VAEDecodeTiled` | `512, 64, 64, 8` | 最终图分块解码。512 是 tile 边长，64 是重叠像素，8 是 batch |
| 35 | `SaveImage` | 前缀 `anima_rdna1/anima` | 纯英文前缀，避免素材索引扫不到 |

`VAEDecodeTiled` 的参数含义：tile 越小峰值显存越低、接缝风险越高；重叠 64 是接缝不明显的下限。tile 提到 1024 就等于放弃了分块的意义。

如果只看预览、不要最终图，可以把 96 和 35 一起禁用（Ctrl+M），省掉十几秒。

## 共享种子

节点 6 `PrimitiveInt`（`fixed`）同时接两个 KSampler 的 `seed` 输入。这样：

- 同一提示词下重跑，第一段和第二段用同一个种子，**放大后的图与原图构图一致**
- 想换种子只改一处，不用同步两个节点
- 想批量对比提示词时，可以把它切成 `randomize`，但两段会各自随机，构图不再对应

配套的 `KSampler` 内部 `control_after_generate` 保持 `randomize` 不会生效 —— 种子的实际来源是节点 6。
