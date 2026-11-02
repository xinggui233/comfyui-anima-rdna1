# 03 · 报错与排错

按"看起来像错误但其实不是"和"真错误"分两类。

## A. 看着吓人，其实正常

### `[WARNING] offload-arch failed with return code 1`

```
[WARNING] offload-arch failed with return code 1
[stderr]
```

ComfyUI 启动时试图用 `offload-arch` 查询 GPU 架构，Windows 上这个工具经常拿不到正确信息（stderr 是空的，说明它只是退出码异常）。ComfyUI 会回落到 `torch.cuda.get_device_name()`，日志后面能看到正确的 `AMD arch: gfx1010`。

**不用管。** 如果后面那行 `AMD arch:` 打不出来，才是真问题。

### `comfy_kitchen backend hip: available False, architecture is not in the validated target manifest: gfx1010`

```
Found comfy_kitchen backend hip: {'available': False, 'disabled': False,
  'unavailable_reason': 'architecture is not in the validated target manifest: gfx1010'}
```

`comfy-kitchen` 是针对验证过架构（gfx90a / gfx942 / gfx1100 之类）编译的算子后端，gfx1010 不在清单里，所以 HIP 后端不可用，退回 `eager` 实现。

**不影响出图**，只是少了些加速算子。这是 RDNA1 的常态，除非自己编译。

### `Warning: TAESD previews enabled, but could not find models/vae_approx/lighttaew2_1`

想要解码过程中的实时预览，需要把 TAESD 小模型放到 `models/vae_approx/`。不装就没有采样过程预览，只有最后成图。

想装：把 `taesd` / `lighttaew2_1` 的 safetensors 放进 `ComfyUI/models/vae_approx/`。

### `[DEPRECATION WARNING] Detected import of deprecated legacy API`

某个自定义节点用了老版前端 API。只要界面能正常加载就无害；如果某个节点面板是空白，去更新那个节点包。

### `DWPose: Onnxruntime not found ... switch to OpenCV with CPU device`

`comfyui_controlnet_aux` 缺少 ONNX Runtime 的 GPU 版。本工作流**不用 DWPose**，无影响。

### `[XB 硬件监控] LibreHardwareMonitor 初始化失败`

整合包自带的硬件监控组件缺依赖。跟出图无关，只是看不到 GPU 温度和占用曲线。

---

## B. 真问题

### `torch.cuda.is_available()` 返回 False

按顺序排查：

1. **torch 是不是 CPU 版**：`python -c "import torch; print(torch.version.hip)"`。输出 `None` 说明装的是 CPU wheel，或者被 `pip install -r requirements.txt` 悄悄换掉了。
2. **SDK 没装或顺序错**：`rocm_sdk_*` 必须先于 torch 安装。
3. **Python 版本不对**：wheel 是 `cp312`，3.11 / 3.13 都装不上。
4. **驱动问题**：Adrenalin 驱动太旧会加载不了 HIP 运行时。

根治办法：`pip uninstall -y torch torchvision torchaudio`，然后按 [01-environment.md](01-environment.md) 的顺序重装。

### 显存不足 / OOM

典型报错：

```
torch.OutOfMemoryError: HIP out of memory. Tried to allocate 256.00 MiB
```

8 GB 卡的常见触发点和处理：

| 触发点 | 处理 |
|---|---|
| 第二段采样（放大后） | 放大倍率 1.3 → 1.15 |
| VAE 解码 | 确认用的是 `VAEDecodeTiled` 而不是 `VAEDecode` |
| 两个模型同时驻留（换底模时） | 每次只保留一个；或启动加 `--lowvram` |
| 长提示词 | 提示词 token 数越多，注意力中间张量越大；把 200 token 压到 80 |

日志里 `loaded completely; X MB loaded` 的累计值超过 8176 MB 时，就已经在靠换出撑了，速度会断崖式下滑。

### 出纯黑图 / 纯噪点图

Anima 用 Qwen3 文本编码器，**CLIPLoader 的 type 必须匹配**。本工作流用的是：

```
CLIPLoader: Anima\qwen_3_06b_base.safetensors, type = stable_diffusion
```

如果换成别的 type，或者把 `qwen_image_vae` 换成 SD1.5 的 VAE，就会得到黑图/彩色噪点。VAE 与底模必须同系列。

### 节点全红 / "Missing Node Types"

缺自定义节点。本工作流需要：

| 节点 | 包 |
|---|---|
| `easy loraStack`、`easy loraStackApply` | ComfyUI-Easy-Use |
| `ShowText\|pysssss` | ComfyUI-Custom-Scripts |

用 ComfyUI-Manager 装完重启即可。`PrimitiveStringMultiline`、`PrimitiveInt`、`StringConcatenate` 是自带的，红色报错说明 ComfyUI 版本太旧（需要 ≥ v0.34）。

### 工作流能跑但模型名对不上

工作流里模型名带 `Anima\` 前缀，例如：

```
Anima\anima_aestheticV11.safetensors
```

这是**子目录**写法，文件实际位置是 `ComfyUI/models/diffusion_models/Anima/anima_aestheticV11.safetensors`。缺了 `Anima` 目录就会在下拉框里显示 `null`，然后静默报错。

`python scripts\check_env.py` 会把缺失的模型列出来。

### `Failed to register output` / `Asset scan failed`

```
Failed to register output: E:\AI\ComfyUI\output\Anima工作流_00008_.png
Asset scan failed
```

整合包自带的素材索引（Seeder）在扫 `output` 目录时失败。**图其实已经正常保存了**，只是没进素材库。文件名带中文或路径过长时会触发。

处理：把 `SaveImage` 的 `filename_prefix` 改成纯英文（本仓库版本已改为 `anima_rdna1/anima`）。

### 生成到一半进程直接消失（不是报错退出）

16 GB 系统内存被吃光了。Windows 会 kill 掉进程且不留异常栈。判断方法：任务管理器看提交内存是否接近上限。

缓解：

- 关掉浏览器里 ComfyUI 的其他标签页（每个标签都缓存一遍模型列表）
- 启动加 `--cache-none`
- 换模型前先手动清空（界面 Queue 面板的 Free model and node cache）

其实最有效的是加内存。16 GB 跑这个工作流属于及格线。
