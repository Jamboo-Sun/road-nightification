# 道路图像夜化 · Road Nightification

一个用于目标检测数据的 Codex Skill，也可以当作独立的 Python 命令行工具使用。默认在 CPU 上批量模拟欠曝、散粒噪声和读出噪声，保持图像尺寸与原始像素网格。带 YOLO 标注时，可将对应标签逐字节复制到输出目录。

| 目的 | 使用流程 | 标注处理 |
| --- | --- | --- |
| 合成低照度图、做强度可控的鲁棒性实验 | 本仓库的 `scripts/nightify.py` | 框坐标不随光度变换改变。仍要检查目标可见性 |
| 将白天照片转成夜间驾驶风格 | [CycleGAN-Turbo 指南](references/night-style.md)，在作者项目中运行 | 生成可能改变轮廓或内容，复核后再沿用标签 |

## 快速使用

在仓库根目录执行。默认流程需要 Python 3.9+、NumPy 和 Pillow。

```bash
python -m pip install -r requirements.txt
python scripts/nightify.py day_images outputs/ev2 --labels day_labels --ev 2 --seed 42
```

输入可以是单张图，也可以是递归读取的文件夹。支持 RGB 或灰度 JPEG、PNG、BMP、WebP。遇到启用 EXIF 旋转的文件，先统一图像显示方向，并确认标注使用同一坐标系。

比如，`day_images/subset/frame.jpg` 对应 `day_labels/subset/frame.txt`。脚本会在新目录生成如下文件：

```text
outputs/ev2/
├── images/subset/frame.png
├── labels/subset/frame.txt
└── manifest.json
```

没有标签时可省略 `--labels`。提供标签目录后，缺失标签默认报错。只有数据集明确用缺失标签表示空目标图时，才使用 `--allow-missing-labels`。每次选择一个新的输出目录。清单记录单图种子、输入路径、输出路径和尺寸。分享清单前可检查其中的输入路径。

想分别观察欠曝和噪声的影响，可以先做纯曝光对照：

```bash
python scripts/nightify.py day_images outputs/ev1-clean --ev 1 --noise none
python scripts/nightify.py day_images outputs/ev3-clean --ev 3 --noise none
python scripts/nightify.py day_images outputs/ev3-noisy --ev 3 --noise both --seed 42
python scripts/nightify.py --help
```

`--ev` 每加 1 档，线性亮度减半。`--noise` 支持 `none`、`shot`、`read`、`both`。`--shot` 控制模拟满量程电子数，`--read` 控制线性空间读噪声标准差，`--rgb-gains` 接收三个通道增益。同一输入相对路径、参数、种子和依赖环境用于复现实验。

## 在 Codex 中使用

将整个 `road-nightification` 仓库文件夹放到 Codex 的技能目录，保留 `SKILL.md`、`scripts/` 和 `references/` 的相对位置。也可以把 [SKILL.md](SKILL.md) 的路径交给 Codex，在当前任务中按其中流程操作。

示例请求：

> 用 `$road-nightification` 对给定检测图像分别模拟降低 1、2、3 档曝光。每一档输出到独立目录，保留 YOLO 标签，关闭噪声以单独比较曝光影响。

用于科研时，按真实图与合成图区分报告结果。同一原图和它的变体应留在同一数据划分。对已是夜间的 NPD 再做退化时，可将其作为额外压力测试，并保留原始真实夜间结果。生成质量和检测收益需要在自己的图像上验证。

## 方法来源与许可

- 默认命令行实现参考 MAET 的曝光和噪声建模思路，使用简化的 sRGB 光度模型。[Cui 等，ICCV 2021](https://openaccess.thecvf.com/content/ICCV2021/html/Cui_Multitask_AET_With_Orthogonal_Tangent_Regularity_for_Dark_Object_Detection_ICCV_2021_paper.html)
- 夜间风格流程引用 CycleGAN-Turbo 作者的实现和权重发布方式。[Parmar 等，2024](https://arxiv.org/abs/2403.12036)
- 道路昼夜翻译及其检测增强应用可参考 [Zheng 等，ForkGAN，ECCV 2020](https://www.ecva.net/papers/eccv_2020/papers_ECCV/papers/123480154.pdf)。

本仓库的原创代码和文档采用 [MIT License](LICENSE)。外部链接指向的代码、模型与权重按各自上游条款使用，本仓库不分发这些资源。
