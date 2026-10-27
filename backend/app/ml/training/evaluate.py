"""Evaluation and metrics calculation module for Road-Damage YOLO model.

Calculates actual Precision, Recall, mAP@0.50, and mAP@0.50:0.95 across all
classes and per-class (D00, D10, D20, D40).
"""
import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rdd_evaluate")

TARGET_CLASSES = {
    0: "D00: Longitudinal Crack",
    1: "D10: Transverse Crack",
    2: "D20: Alligator Crack",
    3: "D40: Pothole",
}


def evaluate_model(
    model_weights: str | Path,
    data_yaml: str | Path,
    split: str = "val",
    img_size: int = 640,
    batch_size: int = 16,
    device: str = "cpu",
    output_dir: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Run model evaluation on validation or test split and compute metrics."""
    weights_path = Path(model_weights).resolve()
    if not weights_path.exists():
        raise FileNotFoundError(f"Model weights not found: {weights_path}")

    data_path = Path(data_yaml).resolve()
    if not data_path.exists():
        raise FileNotFoundError(f"data.yaml not found: {data_path}")

    logger.info(f"Loading model for evaluation: {weights_path}")
    model = YOLO(str(weights_path))

    logger.info(f"Evaluating on split: '{split}' (img_size={img_size}, device={device})...")
    metrics = model.val(
        data=str(data_path),
        split=split,
        imgsz=img_size,
        batch=batch_size,
        device=device,
        plots=True,
    )

    # Extract metrics safely from actual YOLO validation results
    box_metrics = metrics.box
    precision = float(box_metrics.mp) if hasattr(box_metrics, "mp") else 0.0
    recall = float(box_metrics.mr) if hasattr(box_metrics, "mr") else 0.0
    map50 = float(box_metrics.map50) if hasattr(box_metrics, "map50") else 0.0
    map50_95 = float(box_metrics.map) if hasattr(box_metrics, "map") else 0.0

    per_class_results = {}
    if hasattr(box_metrics, "maps") and box_metrics.maps is not None:
        for idx, score in enumerate(box_metrics.maps):
            class_label = TARGET_CLASSES.get(idx, f"Class_{idx}")
            per_class_results[class_label] = {
                "mAP50_95": round(float(score), 4),
            }

    evaluation_summary = {
        "model_path": str(weights_path),
        "split": split,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "mAP_50": round(map50, 4),
        "mAP_50_95": round(map50_95, 4),
        "per_class_metrics": per_class_results,
        "observations_on_edge_cases": {
            "shadows": "Tree and building shadows can trigger false positive crack detections (D00/D10).",
            "road_markings": "Faded lane markings and pedestrian crossings may induce transverse crack confusion.",
            "water_and_rain": "Water puddles can obscure potholes (D40) or reflect sunlight causing specular false alarms.",
            "night_and_low_light": "Low-contrast imagery reduces recall on thin cracks (D00/D10).",
        },
    }

    if output_dir:
        out_path = Path(output_dir) / f"evaluation_{split}_results.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(evaluation_summary, f, indent=2)
        logger.info(f"Evaluation report saved to: {out_path}")

    logger.info("=== Evaluation Results Summary ===")
    logger.info(f"Precision: {evaluation_summary['precision']:.4f}")
    logger.info(f"Recall:    {evaluation_summary['recall']:.4f}")
    logger.info(f"mAP@0.50:  {evaluation_summary['mAP_50']:.4f}")
    logger.info(f"mAP@0.5:95:{evaluation_summary['mAP_50_95']:.4f}")

    return evaluation_summary


def main():
    parser = argparse.ArgumentParser(description="Evaluate YOLO Road Damage Detection Model.")
    parser.add_argument("--weights", type=str, required=True, help="Path to trained .pt weights.")
    parser.add_argument("--data", type=str, required=True, help="Path to data.yaml.")
    parser.add_argument("--split", type=str, default="val", help="Split to evaluate: 'val' or 'test'.")
    parser.add_argument("--img-size", type=int, default=640, help="Image size.")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu or cuda).")
    parser.add_argument("--output-dir", type=str, default="backend/app/ml/artifacts", help="Output directory.")
    args = parser.parse_args()

    evaluate_model(
        model_weights=args.weights,
        data_yaml=args.data,
        split=args.split,
        img_size=args.img_size,
        device=args.device,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
