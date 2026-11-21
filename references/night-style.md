# 用 CycleGAN-Turbo 生成道路夜间风格

1. 使用 [作者仓库](https://github.com/GaParmar/img2img-turbo) 和 [论文](https://arxiv.org/abs/2403.12036)。仓库提供 `day_to_night` 权重、依赖和推理入口。按该仓库当前环境说明使用单独的 CUDA 环境，避免改动检测器环境。首次运行按上游代码加载 SD-Turbo 基础模型和昼转夜权重。
2. 在作者仓库根目录先转换一张自己的白天照片，再抽查多种道路、坑洼尺度和视角。下例为上游推理入口，输出目录应独立于源目录。

   ```bash
   python src/inference_unpaired.py --model_name day_to_night --input_image day.jpg --output_dir night_preview
   ```

3. 基于上游当前代码核实预处理方式和输出尺寸。当前默认内部缩放至 512×512，再将输出恢复至原始尺寸。原尺寸一致无法保证图像内容或目标边缘位置一致。并排查看原图、生成图以及两者叠加的原框，重点检查坑洼是否被抹掉、边界是否偏移、路面是否产生类似坑洼的新伪影。对失败图剔除或重新标注，再加入训练数据。
4. 如果明确需要批处理，可复用一次加载的模型，按源图相对路径写结果，并记录上游提交号、母图、权重、参数和人工复核状态。目录结构和同名文件检查应在批量生成前完成。报告中使用“合成夜间风格”描述这一分支。

[Cui 等的 MAET](https://github.com/cuiziteng/ICCV_MAET) 适用于曝光与噪声可控的对照。[Zheng 等的 ForkGAN](https://github.com/zhengziqiang/ForkGAN) 展示了道路昼转夜与检测增强的先例，官方环境使用 TensorFlow 1.14。
