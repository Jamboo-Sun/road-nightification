---
name: road-nightification
description: 将道路、坑洼或其他目标检测图像批量夜化，生成可复现的低照度退化图或夜间风格图。适用于白天转夜间、合成夜图、模拟欠曝和传感器噪声、NPD 等夜间检测任务的压力测试与数据增强。用户要把暗图提亮时应使用低照度增强流程。
---

# 道路图像夜化

根据目标选用流程：

- **有检测标注、需要稳定保留坐标或做退化强度实验**：运行 [低照度退化脚本](scripts/nightify.py)。它对 RGB 图像做逐像素曝光和噪声变换，保持原始像素网格。输出为合成低照度图。
- **需要道路夜间观感**：阅读 [CycleGAN-Turbo 夜间风格流程](references/night-style.md)。生成图的目标轮廓与标注需要复核。
- **目的未说明**：涉及检测训练、测试或沿用标注时，优先用确定参数的低照度退化流程。涉及视觉展示时，可预览两种效果。

## 可控低照度退化

脚本依赖 Python 3.9+、NumPy 和 Pillow（`python -m pip install numpy pillow`）。目录输入按相对路径递归处理，输出保留相对路径，统一使用无损 PNG。单图、目录均支持。每次输出到新目录，包含 `images/`、可选的 `labels/` 与 `manifest.json`。后者记录参数、随机种子、输入输出路径和尺寸。

```bash
python scripts/nightify.py day_images night_ev2 --labels day_labels --ev 2 --seed 42
```

在 Skill 根目录运行上例，或从其他目录使用脚本绝对路径。`--labels` 接受 YOLO 文本标签根目录。输入图像与标签按相对路径及文件名主干匹配。缺少标签默认报错，只有确认缺失文件代表无目标时才使用 `--allow-missing-labels`。COCO JSON 应另外按输出文件名更新 `images[].file_name`，保持图像 ID、坐标与标注对应，并检查名称冲突。

`--ev` 为曝光降低的档数，每增加一档，线性亮度乘以 0.5。默认 2 档。可用 1、2、3 档作初始梯度，根据试图效果调整。默认近似添加信号相关噪声和读噪声。`--noise none` 关闭噪声，`--noise read` 与 `--noise shot` 用于分别控制两项噪声。`--rgb-gains R G B` 用线性通道增益模拟偏色，默认均为 1。用 `--help` 查看噪声参数及默认值。

逐像素光度变换允许继承空间坐标，但过暗时可能不再能辨认目标。检查不同亮度及目标大小的成品，记录可见性和被排除样本的数量。脚本的退化模型参考 MAET 的曝光及噪声建模思路，属于基于 sRGB 的简化实现。论文中称其为合成低照度图或模拟退化图，并注明参数；如需引用方法来源，见 [MAET 原文](https://openaccess.thecvf.com/content/ICCV2021/html/Cui_Multitask_AET_With_Orthogonal_Tangent_Regularity_for_Dark_Object_Detection_ICCV_2021_paper.html) 和 [作者代码](https://github.com/cuiziteng/ICCV_MAET)。

## 实验记录

- 先确认数据用途及划分。合成训练样本只来自训练划分，同一原图及其变体保留在同一划分。真实测试集独立保留。
- 对已经为夜间的 NPD，进一步降曝光或加噪声属于鲁棒性测试。若使用固定测试集，使用同一批原图构建各退化级别和各模型的输入，单列模拟结果。
- 要检验 SNR 先验，优先用相同输入逐项改变曝光和噪声，并对比匹配结构的普通门控与 SNR 门控。记录原始集及各退化级别的 AP 和相对原始集的变化。
