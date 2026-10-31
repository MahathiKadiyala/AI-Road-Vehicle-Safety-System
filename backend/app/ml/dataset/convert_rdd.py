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
from typing import Dict, List, Optional, Tuple, Any

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


def validate_yolo_dataset(dataset_dir: str | Path) -> Dict[str, Any]:
    """Validate a YOLO format dataset for road damage detection.

    Validates:
      - Directory layout: images/{train,val} and labels/{train,val}.
      - Class indices: strictly in {0, 1, 2, 3} for D00, D10, D20, D40.
      - Image and label pairing (no orphan labels or missing annotations).
      - Label bounds: normalized (xc, yc, w, h) in [0.0, 1.0].
      - Empty labels treated as intentional negative background samples.
      - Image duplicate leakage across splits using MD5 checksums.

    Args:
        dataset_dir: Root directory of YOLO dataset.

    Returns:
        Structured audit report dict.
    """
    root = Path(dataset_dir).resolve()
    errors: List[str] = []
    warnings: List[str] = []

    if not root.exists():
        return {
            "is_valid": False,
            "dataset_path": str(root),
            "errors": [f"Dataset root directory does not exist: {root}"],
            "warnings": [],
            "splits_found": [],
            "total_images": 0,
            "total_labels": 0,
            "background_images": 0,
            "class_distribution": {},
            "data_leakage_detected": False,
        }

    images_dir = root / "images"
    labels_dir = root / "labels"

    if not images_dir.exists():
        errors.append(f"Missing 'images' directory in {root}")
    if not labels_dir.exists():
        errors.append(f"Missing 'labels' directory in {root}")

    if errors:
        return {
            "is_valid": False,
            "dataset_path": str(root),
            "errors": errors,
            "warnings": warnings,
            "splits_found": [],
            "total_images": 0,
            "total_labels": 0,
            "background_images": 0,
            "class_distribution": {},
            "data_leakage_detected": False,
        }

    splits = [d.name for d in images_dir.iterdir() if d.is_dir()]
    if not splits:
        errors.append(f"No split subdirectories (e.g. 'train', 'val') found in {images_dir}")

    total_images = 0
    total_labels = 0
    background_images = 0
    class_distribution: Dict[str, Dict[str, int]] = {}
    image_hashes_by_split: Dict[str, Dict[str, str]] = {}
    leakage_records: List[Dict[str, str]] = []

    valid_img_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    for split in splits:
        class_distribution[split] = {c: 0 for c in CLASS_NAMES}
        split_img_dir = images_dir / split
        split_lbl_dir = labels_dir / split

        if not split_lbl_dir.exists():
            warnings.append(f"Split '{split}' has an images folder but no matching 'labels/{split}' folder.")
            continue

        images = [p for p in split_img_dir.iterdir() if p.suffix.lower() in valid_img_extensions]
        labels = [p for p in split_lbl_dir.iterdir() if p.suffix.lower() == ".txt"]

        total_images += len(images)
        total_labels += len(labels)

        image_stems = {img.stem: img for img in images}
        label_stems = {lbl.stem: lbl for lbl in labels}

        # Check image hashes for cross-split leakage
        image_hashes_by_split[split] = {}
        for img in images:
            h = calculate_image_hash(img)
            image_hashes_by_split[split][h] = img.name

        # Find orphan labels (label exists without corresponding image)
        for stem, lbl_path in label_stems.items():
            if stem not in image_stems:
                errors.append(f"[{split}] Orphan label file without matching image: {lbl_path.name}")

        # Validate label contents and missing labels
        for stem, img_path in image_stems.items():
            if stem not in label_stems:
                errors.append(f"[{split}] Missing label file for image: {img_path.name}")
                continue

            lbl_file = label_stems[stem]
            try:
                content = lbl_file.read_text(encoding="utf-8").strip()
            except Exception as e:
                errors.append(f"[{split}] Could not read label file {lbl_file.name}: {e}")
                continue

            if not content:
                # Valid negative/background sample
                background_images += 1
                continue

            lines = content.splitlines()
            for line_no, line in enumerate(lines, start=1):
                tokens = line.strip().split()
                if not tokens:
                    continue
                if len(tokens) != 5:
                    errors.append(
                        f"[{split}:{lbl_file.name}:L{line_no}] Invalid YOLO line format (expected 5 tokens, got {len(tokens)}): '{line}'"
                    )
                    continue

                class_str, xc_str, yc_str, w_str, h_str = tokens
                try:
                    class_id = int(class_str)
                except ValueError:
                    errors.append(f"[{split}:{lbl_file.name}:L{line_no}] Non-integer class index: '{class_str}'")
                    continue

                if class_id not in (0, 1, 2, 3):
                    errors.append(
                        f"[{split}:{lbl_file.name}:L{line_no}] Invalid class index {class_id}. "
                        "Target classes must be strictly in {0: D00, 1: D10, 2: D20, 3: D40}."
                    )
                    continue

                class_name = CLASS_NAMES[class_id]
                class_distribution[split][class_name] += 1

                try:
                    xc, yc, w, h = float(xc_str), float(yc_str), float(w_str), float(h_str)
                except ValueError:
                    errors.append(f"[{split}:{lbl_file.name}:L{line_no}] Non-numeric bbox values in line: '{line}'")
                    continue

                if not (0.0 <= xc <= 1.0 and 0.0 <= yc <= 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0):
                    errors.append(
                        f"[{split}:{lbl_file.name}:L{line_no}] Bbox coordinates out of bounds [0, 1]: ({xc}, {yc}, {w}, {h})"
                    )

    # Check for cross-split data leakage (identical image in multiple splits)
    split_names = list(image_hashes_by_split.keys())
    for i in range(len(split_names)):
        for j in range(i + 1, len(split_names)):
            s1, s2 = split_names[i], split_names[j]
            overlap = set(image_hashes_by_split[s1].keys()).intersection(set(image_hashes_by_split[s2].keys()))
            for h in overlap:
                img1 = image_hashes_by_split[s1][h]
                img2 = image_hashes_by_split[s2][h]
                leakage_records.append({
                    "split_a": s1,
                    "image_a": img1,
                    "split_b": s2,
                    "image_b": img2,
                    "hash": h,
                })
                errors.append(
                    f"DATA LEAKAGE DETECTED: Image duplicate present across '{s1}' ({img1}) and '{s2}' ({img2})."
                )

    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "dataset_path": str(root),
        "splits_found": splits,
        "total_images": total_images,
        "total_labels": total_labels,
        "background_images": background_images,
        "class_distribution": class_distribution,
        "data_leakage_detected": len(leakage_records) > 0,
        "leakage_records": leakage_records,
        "errors": errors[:50],  # Cap to prevent giant outputs
        "warnings": warnings[:50],
    }


def main():
    parser = argparse.ArgumentParser(description="Convert RDD2020/2022 dataset to YOLO format or validate existing.")
    parser.add_argument("--rdd-dir", type=str, help="Path to RDD dataset folder.")
    parser.add_argument("--output-dir", type=str, default="datasets/road_damage_yolo", help="Destination YOLO folder.")
    parser.add_argument("--train-ratio", type=float, default=0.70, help="Train ratio.")
    parser.add_argument("--val-ratio", type=float, default=0.15, help="Val ratio.")
    parser.add_argument("--test-ratio", type=float, default=0.15, help="Test ratio.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for splitting.")
    parser.add_argument("--validate-only", type=str, help="Path to existing YOLO dataset to validate.")
    args = parser.parse_args()

    if args.validate_only:
        report = validate_yolo_dataset(args.validate_only)
        print(json.dumps(report, indent=2))
        return

    if not args.rdd_dir:
        parser.error("--rdd-dir is required when not using --validate-only.")

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
