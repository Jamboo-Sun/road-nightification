"""Synthesize low-light RGB images while preserving the input pixel grid."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from uuid import uuid4

import numpy as np
from PIL import Image


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def nightify(rgb, args, seed):
    srgb = rgb.astype(np.float32) / 255.0
    linear = np.where(
        srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4
    )
    signal = np.clip(
        linear * (2.0 ** -args.ev) * np.asarray(args.rgb_gains, np.float32),
        0.0,
        1.0,
    )
    rng = np.random.default_rng(seed)
    if args.noise in {"both", "shot"} and args.shot > 0:
        signal = (rng.poisson(signal * args.shot) / args.shot).astype(np.float32)
    if args.noise in {"both", "read"} and args.read > 0:
        signal += rng.standard_normal(signal.shape, dtype=np.float32) * args.read
    signal = np.clip(signal, 0.0, 1.0)
    srgb = np.where(
        signal <= 0.0031308, 12.92 * signal, 1.055 * signal ** (1.0 / 2.4) - 0.055
    )
    return np.rint(np.clip(srgb, 0.0, 1.0) * 255).astype(np.uint8)


def collect_images(args):
    source = args.source
    if source.is_file() and source.suffix.lower() in IMAGE_EXTENSIONS:
        root, paths = source.parent, [source]
    elif source.is_dir():
        root = source
        paths = sorted(
            p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        )
    else:
        raise ValueError(f"Unsupported or missing input: {source}")
    if not paths:
        raise ValueError(f"No supported image files found: {source}")
    if args.labels is not None and not args.labels.is_dir():
        raise ValueError(f"Label directory is missing: {args.labels}")

    outputs = set()
    for path in paths:
        relative = path.relative_to(root)
        output = relative.with_suffix(".png")
        name = output.as_posix().casefold()
        if name in outputs:
            raise ValueError(f"Multiple inputs would write to {output}")
        outputs.add(name)
        label = args.labels / relative.with_suffix(".txt") if args.labels else None
        if label is not None and not label.is_file() and not args.allow_missing_labels:
            raise ValueError(f"Missing YOLO label: {label}")
        yield path, relative, output, label


def convert(args):
    destination = args.destination
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"Choose a new output directory: {destination}")
    if args.source.is_dir() and destination.is_relative_to(args.source):
        raise ValueError("Output directory must be outside the input image directory")
    if args.labels and destination.is_relative_to(args.labels):
        raise ValueError("Output directory must be outside the input label directory")
    jobs = list(collect_images(args))
    destination.parent.mkdir(parents=True, exist_ok=True)

    output_root = destination.parent / f".nightify-{uuid4().hex}"
    output_root.mkdir()
    try:
        records = []
        for path, relative, output, label in jobs:
            digest = hashlib.sha256(relative.as_posix().encode("utf-8")).digest()
            seed = args.seed ^ int.from_bytes(digest[:8], "big")
            with Image.open(path) as source_image:
                orientation = source_image.getexif().get(274, 1)
                if orientation != 1:
                    raise ValueError(f"Normalize EXIF orientation and annotations before using {path}")
                if source_image.mode not in {"RGB", "L"}:
                    raise ValueError(f"Convert {source_image.mode} to standard sRGB or grayscale first: {path}")
                width, height = source_image.size
                result = nightify(np.asarray(source_image.convert("RGB")), args, seed)
            image_relative = Path("images") / output
            target = output_root / image_relative
            target.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(result).save(target)

            annotation = None
            if label is not None:
                annotation = Path("labels") / output.with_suffix(".txt")
                target_label = output_root / annotation
                target_label.parent.mkdir(parents=True, exist_ok=True)
                if label.is_file():
                    shutil.copyfile(label, target_label)
                else:
                    target_label.touch()
            records.append(
                {
                    "source": str(path),
                    "image": image_relative.as_posix(),
                    "width": width,
                    "height": height,
                    "seed": seed,
                    "label": annotation.as_posix() if annotation else None,
                    "label_status": (
                        "none" if label is None else "copied" if label.is_file() else "empty"
                    ),
                }
            )
        manifest = {
            "algorithm": "srgb-exposure-poisson-gaussian-v1",
            "ev": args.ev,
            "noise": args.noise,
            "shot_peak_electrons": args.shot,
            "read_sigma_linear": args.read,
            "rgb_gains": args.rgb_gains,
            "base_seed": args.seed,
            "numpy_version": np.__version__,
            "images": records,
        }
        (output_root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        output_root.rename(destination)
    finally:
        if output_root.exists():
            shutil.rmtree(output_root)
    print(f"Converted {len(records)} image(s). Manifest: {destination / 'manifest.json'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Image file or image directory")
    parser.add_argument("destination", type=Path, help="New output directory")
    parser.add_argument("--labels", type=Path, help="Optional YOLO label directory")
    parser.add_argument("--allow-missing-labels", action="store_true", help="Treat missing labels as empty")
    parser.add_argument("--ev", type=float, default=2.0, help="Exposure reduction in stops (default: 2)")
    parser.add_argument("--noise", choices=("none", "shot", "read", "both"), default="both")
    parser.add_argument("--shot", type=float, default=800.0, help="Full-scale electron count (default: 800)")
    parser.add_argument("--read", type=float, default=0.004, help="Read-noise sigma in linear units (default: 0.004)")
    parser.add_argument("--rgb-gains", nargs=3, type=float, default=[1.0, 1.0, 1.0])
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    numeric = [args.ev, args.shot, args.read, *args.rgb_gains]
    if not np.isfinite(numeric).all() or not 0 <= args.ev <= 20 or not 0 <= args.read <= 1:
        parser.error("Use finite values, with EV in [0, 20] and read sigma in [0, 1]")
    if not 0 <= args.shot <= 1e9 or not all(0 < gain <= 16 for gain in args.rgb_gains):
        parser.error("Use shot peak in [0, 1e9] and RGB gains in (0, 16]")
    if args.seed < 0 or (args.allow_missing_labels and args.labels is None):
        parser.error("Use a nonnegative seed and supply --labels before --allow-missing-labels")
    args.source, args.destination = args.source.resolve(), args.destination.resolve()
    if args.labels:
        args.labels = args.labels.resolve()
    try:
        convert(args)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
