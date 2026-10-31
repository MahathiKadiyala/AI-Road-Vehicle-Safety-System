"""Reproducible training pipeline for Road-Damage Detection with YOLOv8.

Handles model training, checkpoint management, hardware detection, hyperparameter
configuration, and training metadata recording.
"""
import argparse
import json
import logging
import os
import platform
import random
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import torch
import ultralytics
from ultralytics import YOLO

try:
    import numpy as np
except ImportError:
    np = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rdd_train")


def check_dataset_exists(data_yaml_path: Path) -> bool:
    """Verify that the dataset configuration file and splits exist."""
    if not data_yaml_path.exists():
        logger.error(f"Dataset config not found at: {data_yaml_path}")
        return False
    return True


def estimate_resource_requirements(epochs: int, batch_size: int, img_size: int, device: str) -> None:
    """Print estimated resource requirements and hardware considerations."""
    logger.info("=== Compute & Resource Assessment ===")
    logger.info(f"Execution Device: {device.upper()}")
    logger.info(f"Target Epochs: {epochs} | Batch Size: {batch_size} | Image Resolution: {img_size}x{img_size}")

    if device.lower() == "cpu":
        logger.warning(
            "TRAINING ON CPU: Deep neural network training on CPU will take significantly "
            "more time per epoch than on a dedicated NVIDIA CUDA GPU. Recommended settings: "
            "model='yolov8n.pt', epochs=10-30, batch=8-16, img_size=512 or 640."
        )


def train_road_damage_model(
    data_yaml: str | Path,
    base_model: str = "yolov8n.pt",
    epochs: int = 30,
    batch_size: int = 16,
    img_size: int = 640,
    device: str = "cpu",
    project: str = "runs/detect",
    name: str = "road_damage_run",
    artifact_dir: str | Path = "backend/app/ml/artifacts",
    patience: int = 10,
    seed: int = 42,
    learning_rate: float = 0.01,
) -> Dict[str, Any]:
    """Train YOLOv8 on road distress dataset and manage artifacts."""
    data_path = Path(data_yaml).resolve()
    if not check_dataset_exists(data_path):
        raise FileNotFoundError(f"data.yaml not found: {data_path}")

    artifact_dir = Path(artifact_dir).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)

    estimate_resource_requirements(epochs, batch_size, img_size, device)

    # Set seeds for full reproducibility
    random.seed(seed)
    if np is not None:
        np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    # Initialize YOLO model
    logger.info(f"Loading initial model weights from: {base_model}")
    model = YOLO(base_model)

    start_time = datetime.now()

    # Launch reproducible training
    logger.info("Starting YOLO training run...")
    results = model.train(
        data=str(data_path),
        epochs=epochs,
        batch=batch_size,
        imgsz=img_size,
        device=device,
        project=project,
        name=name,
        patience=patience,
        seed=seed,
        deterministic=True,
        workers=0,  # Single-process data loading to prevent Windows spawn deadlocks
        lr0=learning_rate,
        plots=True,
        save=True,
        val=True,
    )

    end_time = datetime.now()
    duration_sec = (end_time - start_time).total_seconds()

    # Identify best checkpoint
    run_dir = Path(project) / name
    best_pt = run_dir / "weights" / "best.pt"
    last_pt = run_dir / "weights" / "last.pt"

    dest_best_pt = artifact_dir / "road_damage_yolo.pt"
    if best_pt.exists():
        shutil.copy2(best_pt, dest_best_pt)
        logger.info(f"Successfully copied best model checkpoint to: {dest_best_pt}")
    elif last_pt.exists():
        shutil.copy2(last_pt, dest_best_pt)
        logger.info(f"Copied last model checkpoint to: {dest_best_pt}")

    # Record training metadata
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "training_duration_seconds": round(duration_sec, 2),
        "base_model": base_model,
        "epochs_requested": epochs,
        "batch_size": batch_size,
        "image_size": img_size,
        "device": device,
        "data_config": str(data_path),
        "python_version": sys.version,
        "torch_version": torch.__version__,
        "ultralytics_version": ultralytics.__version__,
        "platform": platform.platform(),
        "best_checkpoint_path": str(dest_best_pt) if dest_best_pt.exists() else None,
        "run_directory": str(run_dir),
    }

    metadata_path = artifact_dir / "training_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Training metadata recorded to: {metadata_path}")
    return metadata


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8 on Road Distress Dataset.")
    parser.add_argument("--data", type=str, required=True, help="Path to data.yaml.")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Pretrained YOLO model weights.")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs.")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size.")
    parser.add_argument("--img-size", type=int, default=640, help="Image resolution.")
    parser.add_argument("--device", type=str, default="cpu", help="Device: 'cpu' or '0' for CUDA.")
    parser.add_argument("--project", type=str, default="runs/detect", help="Output directory for runs.")
    parser.add_argument("--name", type=str, default="road_damage_run", help="Run experiment name.")
    parser.add_argument("--artifact-dir", type=str, default="backend/app/ml/artifacts", help="Artifact destination.")
    parser.add_argument("--patience", type=int, default=10, help="Early stopping patience.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    args = parser.parse_args()

    train_road_damage_model(
        data_yaml=args.data,
        base_model=args.model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        img_size=args.img_size,
        device=args.device,
        project=args.project,
        name=args.name,
        artifact_dir=args.artifact_dir,
        patience=args.patience,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
