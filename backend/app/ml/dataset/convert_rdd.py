"""RDD2020 / RDD2022 dataset converter and validator for YOLO training.

Converts Pascal VOC XML annotations to YOLO format, filters and maps the four
target road distress classes:
  - D00: Longitudinal Crack
  - D10: Transverse Crack
  - D20: Alligator Crack
  - D40: Pothole

Features:
  - Bounding box validation and sanity checking (clamps / rejects corrupt boxes).
  - Train / Val / Test splitting with reproducible random seeding.
  - Image deduplication via SHA256/MD5 hashing to prevent data leakage.
  - Automatic generation of YOLO `data.yaml` configuration.
  - Structured dataset audit report generation (JSON).
"""
import argparse
import hashlib
import json
import logging
import os
import random
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rdd_converter")

# Standard 4 target classes for Phase 3
TARGET_CLASSES: Dict[str, int] = {
    "D00": 0,  # Longitudinal Crack
    "D10": 1,  # Transverse Crack
    "D20": 2,  # Alligator Crack
    "D40": 3,  # Pothole
}

CLASS_NAMES: List[str] = ["D00", "D10", "D20", "D40"]

CLASS_DESCRIPTIONS: Dict[str, str] = {
    "D00": "Longitudinal Crack",
    "D10": "Transverse Crack",
    "D20": "Alligator Crack",
    "D40": "Pothole",
}


def calculate_image_hash(image_path: Path) -> str:
    """Calculate MD5 hash of image to detect duplicate images."""
    hasher = hashlib.md5()
    with open(image_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def voc_to_yolo_bbox(
    xmin: float, ymin: float, xmax: float, ymax: float, img_w: int, img_h: int
) -> Optional[Tuple[float, float, float, float]]:
    """Convert Pascal VOC pixel box [xmin, ymin, xmax, ymax] to YOLO normalized box.

    Returns:
        (x_center, y_center, width, height) normalized to [0, 1], or None if invalid.
    """
    if img_w <= 0 or img_h <= 0:
        return None

    # Sanity checks
    if xmin >= xmax or ymin >= ymax:
        return None

    # Clamp coordinates to image boundaries
    xmin = max(0.0, min(float(xmin), float(img_w)))
    xmax = max(0.0, min(float(xmax), float(img_w)))
    ymin = max(0.0, min(float(ymin), float(img_h)))
    ymax = max(0.0, min(float(ymax), float(img_h)))

    box_w = xmax - xmin
    box_h = ymax - ymin

    if box_w <= 1.0 or box_h <= 1.0:
        return None

    x_center = (xmin + (box_w / 2.0)) / img_w
    y_center = (ymin + (box_h / 2.0)) / img_h
    norm_w = box_w / img_w
    norm_h = box_h / img_h

    # Ensure within bounds
    x_center = min(1.0, max(0.0, x_center))
    y_center = min(1.0, max(0.0, y_center))
    norm_w = min(1.0, max(0.0, norm_w))
    norm_h = min(1.0, max(0.0, norm_h))

    return x_center, y_center, norm_w, norm_h


def parse_voc_xml(xml_path: Path) -> Tuple[Optional[Tuple[int, int]], List[Tuple[str, Tuple[float, float, float, float]]]]:
    """Parse Pascal VOC XML annotation file.

    Returns:
        Tuple of ((img_width, img_height), list of (class_name, (xmin, ymin, xmax, ymax))).
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        size_elem = root.find("size")
        if size_elem is None:
            return None, []

        w_elem = size_elem.find("width")
        h_elem = size_elem.find("height")
        if w_elem is None or h_elem is None:
            return None, []

        width = int(w_elem.text)
        height = int(h_elem.text)

        objects = []
        for obj in root.findall("object"):
            name_elem = obj.find("name")
            if name_elem is None or not name_elem.text:
                continue
            name = name_elem.text.strip()

            bndbox = obj.find("bndbox")
            if bndbox is None:
                continue

            try:
                xmin = float(bndbox.find("xmin").text)
                ymin = float(bndbox.find("ymin").text)
                xmax = float(bndbox.find("xmax").text)
                ymax = float(bndbox.find("ymax").text)
                objects.append((name, (xmin, ymin, xmax, ymax)))
            except (TypeError, ValueError):
                continue

        return (width, height), objects
    except Exception as err:
        logger.warning(f"Error parsing XML {xml_path}: {err}")
        return None, []


def convert_dataset(
    rdd_root: str | Path,
    output_dir: str | Path,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
    copy_images: bool = True,
) -> Dict:
    """Convert RDD dataset in Pascal VOC format to YOLO format with split management.

    Returns:
        Detailed audit report dictionary.
    """
    random.seed(seed)
    rdd_root = Path(rdd_root).resolve()
    output_dir = Path(output_dir).resolve()

    if not rdd_root.exists():
        raise FileNotFoundError(f"RDD dataset directory does not exist: {rdd_root}")

    # Discover XML annotations
    xml_files = list(rdd_root.rglob("*.xml"))
    if not xml_files:
        raise FileNotFoundError(f"No XML annotation files found in: {rdd_root}")

    logger.info(f"Found {len(xml_files)} XML annotation files.")

    # Prepare YOLO destination directories
    splits = ["train", "val", "test"]
    for split in splits:
        (output_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    seen_hashes: Dict[str, str] = {}
    valid_samples: List[Dict] = []
    skipped_duplicates = 0
    non_target_classes_found: Dict[str, int] = {}
    corrupted_boxes = 0

    for xml_file in xml_files:
        # Locate corresponding image
        base_name = xml_file.stem
        img_candidates = [
            xml_file.parent.parent / "JPEGImages" / f"{base_name}.jpg",
            xml_file.parent.parent / "images" / f"{base_name}.jpg",
            xml_file.parent / f"{base_name}.jpg",
            xml_file.parent / f"{base_name}.png",
        ]
        image_path = None
        for cand in img_candidates:
            if cand.exists():
                image_path = cand
                break

        if not image_path:
            continue

        # Prevent duplicate image leakage
        img_hash = calculate_image_hash(image_path)
        if img_hash in seen_hashes:
            skipped_duplicates += 1
            continue
        seen_hashes[img_hash] = str(image_path)

        # Parse VOC
        dims, objects = parse_voc_xml(xml_file)
        if dims is None or dims[0] <= 0 or dims[1] <= 0:
            continue

        img_w, img_h = dims
        yolo_annotations: List[str] = []

        for name, box in objects:
            if name not in TARGET_CLASSES:
                non_target_classes_found[name] = non_target_classes_found.get(name, 0) + 1
                continue

            class_id = TARGET_CLASSES[name]
            yolo_box = voc_to_yolo_bbox(box[0], box[1], box[2], box[3], img_w, img_h)
            if yolo_box is None:
                corrupted_boxes += 1
                continue

            yolo_annotations.append(f"{class_id} {yolo_box[0]:.6f} {yolo_box[1]:.6f} {yolo_box[2]:.6f} {yolo_box[3]:.6f}")

        # Keep sample if it has valid target distress annotations or as background sample
        valid_samples.append({
            "image_path": image_path,
            "annotations": yolo_annotations,
            "has_target_distress": len(yolo_annotations) > 0,
            "base_name": base_name,
        })

    # Shuffle deterministically
    random.shuffle(valid_samples)

    total_valid = len(valid_samples)
    n_train = int(total_valid * train_ratio)
    n_val = int(total_valid * val_ratio)

    sample_splits = {
        "train": valid_samples[:n_train],
        "val": valid_samples[n_train : n_train + n_val],
        "test": valid_samples[n_train + n_val :],
    }

    class_distribution: Dict[str, Dict[str, int]] = {s: {c: 0 for c in CLASS_NAMES} for s in splits}

    for split, samples in sample_splits.items():
        for sample in samples:
            dst_img = output_dir / "images" / split / sample["image_path"].name
            dst_lbl = output_dir / "labels" / split / f"{sample['base_name']}.txt"

            if copy_images:
                shutil.copy2(sample["image_path"], dst_img)

            with open(dst_lbl, "w", encoding="utf-8") as f:
                for line in sample["annotations"]:
                    f.write(f"{line}\n")
                    cid = int(line.split()[0])
                    class_name = CLASS_NAMES[cid]
                    class_distribution[split][class_name] += 1

    # Generate data.yaml
    yaml_content = f"""# YOLOv8 Road Distress Dataset Configuration
path: {output_dir.as_posix()}
train: images/train
val: images/val
test: images/test

names:
  0: D00
  1: D10
  2: D20
  3: D40

descriptions:
  0: "Longitudinal Crack"
  1: "Transverse Crack"
  2: "Alligator Crack"
  3: "Pothole"
"""
    yaml_path = output_dir / "data.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    report = {
        "dataset_name": "RDD2020_to_YOLO",
        "random_seed": seed,
        "total_xml_inspected": len(xml_files),
        "total_unique_valid_samples": total_valid,
        "skipped_duplicate_images": skipped_duplicates,
        "corrupted_boxes_filtered": corrupted_boxes,
        "non_target_classes_ignored": non_target_classes_found,
        "splits_count": {s: len(sample_splits[s]) for s in splits},
        "class_distribution_by_split": class_distribution,
        "data_yaml_path": str(yaml_path),
    }

    report_path = output_dir / "conversion_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Conversion complete. Config saved to: {yaml_path}")
    logger.info(f"Audit report saved to: {report_path}")
    return report


def main():
    parser = argparse.ArgumentParser(description="Convert RDD2020/2022 dataset to YOLO format.")
    parser.add_argument("--rdd-dir", type=str, required=True, help="Path to RDD dataset folder.")
    parser.add_argument("--output-dir", type=str, default="datasets/road_damage_yolo", help="Destination YOLO folder.")
    parser.add_argument("--train-ratio", type=float, default=0.70, help="Train ratio.")
    parser.add_argument("--val-ratio", type=float, default=0.15, help="Val ratio.")
    parser.add_argument("--test-ratio", type=float, default=0.15, help="Test ratio.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for splitting.")
    args = parser.parse_args()

    convert_dataset(
        rdd_root=args.rdd_dir,
        output_dir=args.output_dir,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
