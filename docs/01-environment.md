# 01 · 在 Windows 上装 ROCm 跑 ComfyUI（gfx1010 / RX 5700 XT）

Windows 版的 ROCm 不是装个驱动就完事，它是一组 **Python wheel**：`rocm_sdk_*` 提供 HIP 运行时和算子库，`torch` 是**针对这个 SDK 重新编译的版本**。两者版本必须咬死，混装就黑屏或者 `torch.cuda.is_available()` 返回 False。

本仓库验证过的组合：

| 组件 | 版本 | 说明 |
|---|---|---|
| Python | 3.12.10 | 必须 3.12，wheel 是 `cp312` |
| `rocm_sdk_core` | 7.12.0a20260207 | 运行时核心 |
| `rocm_sdk_libraries_gfx101x_dgpu` | 7.12.0a20260207 | **gfx101x 专用**算子库 |
| `torch` | 2.9.1+rocm7.12.0a20260207 | HIP 7.2.0 |
| `torchvision` | 0.24.0 | 与 torch 2.9.1 配套 |
| `torchaudio` | 2.9.0 | 同上 |
| ComfyUI | v0.34.4 | |

> ⚠️ 关键点：`rocm_sdk_libraries_gfx101x_dgpu` 这个包名里的 `gfx101x` 就是 RDNA1。官方的 `rocm` release 不包含它，必须用 **nightly / 专用构建**。

---

## 步骤

### 1. 准备干净的 Python

用 **Python 3.12.10**，不要用系统里已装的其他版本，更不要用 3.13（没有对应 wheel）。

最省事的做法是装一个 embeddable 版，放在例如 `E:\AI\python_embeded`：

1. 下载 `python-3.12.10-embed-amd64.zip` 解压
2. 修改 `python312._pth`，取消注释 `import site`（否则 pip 装的东西导不进来）
3. 下载 `get-pip.py` 并执行：`python.exe get-pip.py`

如果直接用安装版 Python 也可以，只要确认 `python -c "import sys; print(sys.version)"` 输出 3.12.10。

### 2. 装 wheel

把 5 个 wheel 放在同一目录（本项目里在 `E:\AI\`）：

```
rocm_sdk_core-7.12.0a20260207-py3-none-win_amd64.whl
rocm_sdk_libraries_gfx101x_dgpu-7.12.0a20260207-py3-none-win_amd64.whl
torch-2.9.1+rocm7.12.0a20260207-cp312-cp312-win_amd64.whl
torchvision-0.24.0+rocm7.12.0a20260207-cp312-cp312-win_amd64.whl
torchaudio-2.9.0+rocm7.12.0a20260207-cp312-cp312-win_amd64.whl
```

**先装 SDK，再装 torch**，顺序反了会因为找不到依赖而回落到 CPU 版：

```bat
cd /d E:\AI
python -m pip install --no-cache-dir rocm_sdk_core-*.whl rocm_sdk_libraries_gfx101x_dgpu-*.whl
python -m pip install --no-cache-dir torch-*.whl torchvision-*.whl torchaudio-*.whl
```

如果之前装过 CPU 版 torch，先卸干净：

```bat
python -m pip uninstall -y torch torchvision torchaudio
```

### 3. 验证

```bat
python -c "import torch; print(torch.__version__, torch.version.hip, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

期望输出形如：

```
2.9.1+rocm7.12.0a20260207 7.2.0-580ef16945 True AMD Radeon RX 5700 XT
```

接着跑一次真实矩阵乘法，这一步会触发 MIOpen 编译，是"真的能算"的证明：

```bat
python scripts\check_env.py
```

### 4. 装 ComfyUI

```bat
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
git checkout v0.34.4
python -m pip install -r requirements.txt
```

`requirements.txt` 里可能会试图升级 torch，注意看 pip 的输出：如果它要重装 `torch`，加 `--no-deps` 单独装其余包，或者先把 torch 版本锁死。

### 5. 启动

用 `scripts/launch_rdna1.bat`，或者在 ComfyUI 目录执行：

```bat
python main.py --enable-dynamic-vram --auto-launch --port 8188
```

`--enable-dynamic-vram` 是本配置的关键参数：允许 ComfyUI 在推理过程中按需把权重在显存和内存之间调度，8 GB 卡跑 4 GB 的 UNet 全靠它。

---

## 双显卡 / 有核显的机器

如果你有核显，或者插了两张卡，`torch.cuda.device_count()` 会把它们都列出来。用 `HIP_VISIBLE_DEVICES` 指定：

```bat
set HIP_VISIBLE_DEVICES=0
```

`launch_rdna1.bat` 里已经预留了这行，按需改成 0 或 1。选错了会看到 `Device: cuda:0 AMD Radeon(TM) Graphics` 这种 —— 那就是核显，跑起来慢十倍。

## 需要 MSVC 吗

本机启动脚本里加了这段：

```bat
SET "PATH=C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.51.36231;%PATH%"
```

它不是 ComfyUI 必需的，是给某些需要现场编译算子（Triton、部分自定义节点）的场景用的。没有 VS 就把这行删掉，不影响主流程。

## 装完预期看到的日志

```
Total VRAM 8176 MB, total RAM 16194 MB
pytorch version: 2.9.1+rocm7.12.0a20260207
AMD arch: gfx1010
ROCm version: (7, 2)
Set vram state to: HIGH_VRAM
Device: cuda:0 AMD Radeon RX 5700 XT : native
Using async weight offloading with 2 streams
Enabled pinned memory 6477.0
Using sub quadratic optimization for attention
```

其中两条"看起来像错误"的日志是**正常的**，详见 [03-troubleshooting.md](03-troubleshooting.md)：

```
[WARNING] offload-arch failed with return code 1
Found comfy_kitchen backend hip: {'available': False, ... 'architecture is not in the validated target manifest: gfx1010'}
```
