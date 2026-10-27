"""Inference service for Road-Damage Detection with YOLO.

Provides structured distress detection, validation, non-blocking execution,
and explicit model availability checks.
"""
import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings
from app.schemas.damage_detection import (
    BoundingBox,
    DamageDetectionItem,
    DamageDetectionResponse,
    DamageModelStatusResponse,
)

logger = logging.getLogger("roadsafety.ml.detector")

# Expected 4 target classes
TARGET_CLASSES_MAP: Dict[int, Dict[str, str]] = {
    0: {
        "code": "D00",
        "name": "Longitudinal Crack",
        "hazard_type": "crack",
        "severity": "low",
        "color": "#3b82f6",  # Blue
    },
    1: {
        "code": "D10",
        "name": "Transverse Crack",
        "hazard_type": "crack",
        "severity": "medium",
        "color": "#06b6d4",  # Cyan
    },
    2: {
        "code": "D20",
        "name": "Alligator Crack",
        "hazard_type": "crack",
        "severity": "high",
        "color": "#f59e0b",  # Amber
    },
    3: {
        "code": "D40",
        "name": "Pothole",
        "hazard_type": "pothole",
        "severity": "critical",
        "color": "#ef4444",  # Red
    },
}


class ModelUnavailableError(Exception):
    """Raised when trained road damage model weights are absent or invalid."""
    pass


class RoadDamageDetector:
    """YOLO Road Damage Detection inference manager."""

    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        self.model_path_str = model_path or settings.ROAD_DAMAGE_MODEL_PATH
        self.device = device or settings.ML_DEVICE
        self._model = None
        self._load_attempted = False
        self._load_error: Optional[str] = None

    def _resolve_model_path(self) -> Path:
        """Resolve model path relative to project or backend root."""
        raw_path = Path(self.model_path_str)
        if raw_path.is_absolute():
            return raw_path

        # Try relative to current working directory, backend, or app dir
        candidates = [
            raw_path,
            Path("backend") / raw_path,
            Path(__file__).parent.parent / "ml" / "artifacts" / raw_path.name,
            Path(__file__).parent / "artifacts" / raw_path.name,
        ]
        for cand in candidates:
            if cand.exists():
                return cand.resolve()

        return raw_path.resolve()

    def get_status(self) -> DamageModelStatusResponse:
        """Return diagnostic status of the road damage model."""
        resolved_path = self._resolve_model_path()
        weights_exist = resolved_path.exists() and resolved_path.is_file()

        details = None
        available = False

        if not weights_exist:
            details = (
                f"Model weights file not found at '{resolved_path}'. "
                "Train the model using 'app/ml/training/train.py' or provide a trained road_damage_yolo.pt checkpoint."
            )
        else:
            # Check if model can be loaded and validates road distress classes
            try:
                self._ensure_loaded()
                available = True
                details = f"Loaded successfully on {self.device}."
            except Exception as e:
                available = False
                details = f"Model weights found but failed to initialize: {str(e)}"

        return DamageModelStatusResponse(
            available=available,
            model_name="YOLO-RoadDamage-Detector",
            model_path=str(resolved_path),
            weights_present=weights_exist,
            device=self.device,
            supported_classes={item["code"]: item["name"] for item in TARGET_CLASSES_MAP.values()},
            details=details,
        )

    def _ensure_loaded(self):
        """Lazy load the YOLO model weights and verify classes."""
        if self._model is not None:
            return

        resolved_path = self._resolve_model_path()
        if not resolved_path.exists():
            self._load_error = f"Model file '{resolved_path}' does not exist."
            raise ModelUnavailableError(self._load_error)

        try:
            from ultralytics import YOLO

            logger.info(f"Loading Road Damage YOLO model from: {resolved_path}")
            model = YOLO(str(resolved_path))

            # Strictly verify that weights are for road distress and NOT generic COCO
            # COCO class 0 is 'person', whereas Road Damage class 0 is 'D00' or distress
            model_names = model.names if hasattr(model, "names") else {}
            if model_names:
                names_values = list(model_names.values())
                # If model is default COCO containing 'person' or 'bicycle', reject
                if "person" in names_values or "bicycle" in names_values:
                    self._load_error = (
                        "Invalid model: The provided checkpoint contains generic COCO classes "
                        "(e.g., 'person', 'bicycle') instead of Road Distress classes (D00, D10, D20, D40). "
                        "Generic models must never be substituted for road damage detection."
                    )
                    raise ModelUnavailableError(self._load_error)

            self._model = model
            self._load_error = None
            logger.info("Road Damage YOLO model loaded and verified successfully.")
        except ModelUnavailableError:
            raise
        except Exception as exc:
            self._load_error = f"Failed to load YOLO model: {exc}"
            logger.error(self._load_error)
            raise ModelUnavailableError(self._load_error) from exc

    def _render_annotated_image(
        self,
        image_path: Path,
        detections: List[DamageDetectionItem],
        img_w: int,
        img_h: int,
    ) -> Optional[str]:
        """Draw bounding boxes and class badges onto image, saving to static storage."""
        try:
            im = Image.open(image_path).convert("RGB")
            draw = ImageDraw.Draw(im)

            # Try to load a reasonable font or use default
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None

            for det in detections:
                box = det.box
                x1 = int(box.xmin * img_w)
                y1 = int(box.ymin * img_h)
                x2 = int(box.xmax * img_w)
                y2 = int(box.ymax * img_h)

                class_meta = TARGET_CLASSES_MAP.get(det.class_id, {})
                color = class_meta.get("color", "#ef4444")

                # Draw bounding rectangle (thick outline)
                for thickness in range(3):
                    draw.rectangle([x1 - thickness, y1 - thickness, x2 + thickness, y2 + thickness], outline=color)

                # Draw label banner
                label_text = f"{det.class_code} {int(det.confidence * 100)}%"
                text_bbox = draw.textbbox((x1, y1), label_text, font=font) if font else (x1, y1, x1 + 60, y1 + 14)
                text_w = text_bbox[2] - text_bbox[0] + 6
                text_h = text_bbox[3] - text_bbox[1] + 4

                label_top = max(0, y1 - text_h)
                draw.rectangle([x1, label_top, x1 + text_w, label_top + text_h], fill=color)
                draw.text((x1 + 3, label_top + 2), label_text, fill="white", font=font)

            # Save annotated image
            out_filename = f"ai_annotated_{uuid.uuid4().hex}.jpg"
            upload_dir = Path(settings.UPLOAD_DIR) / "ai_annotated"
            upload_dir.mkdir(parents=True, exist_ok=True)
            out_path = upload_dir / out_filename
            im.save(out_path, format="JPEG", quality=88)

            # Return URL relative to static uploads mount
            return f"/static/uploads/ai_annotated/{out_filename}"
        except Exception as err:
            logger.warning(f"Could not render annotated image: {err}")
            return None

    def detect_sync(
        self,
        image_path: str | Path,
        confidence_threshold: Optional[float] = None,
    ) -> DamageDetectionResponse:
        """Synchronous detection method. Must be called via thread offload from async handlers."""
        self._ensure_loaded()
        conf_thr = confidence_threshold or settings.DAMAGE_CONFIDENCE_THRESHOLD

        img_path = Path(image_path).resolve()
        if not img_path.exists():
            raise FileNotFoundError(f"Image not found at: {img_path}")

        # Validate that image is readable
        try:
            with Image.open(img_path) as img:
                img_w, img_h = img.size
        except Exception as e:
            raise ValueError(f"Uploaded file is not a valid or readable image: {e}")

        start_time = time.perf_counter()

        # Run inference
        results = self._model.predict(
            source=str(img_path),
            conf=conf_thr,
            device=self.device,
            verbose=False,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        detections: List[DamageDetectionItem] = []

        if results and len(results) > 0:
            result = results[0]
            boxes = result.boxes

            if boxes is not None:
                for box in boxes:
                    raw_cls = box.cls[0]
                    cls_id = int(raw_cls.item() if hasattr(raw_cls, "item") else raw_cls)

                    raw_conf = box.conf[0]
                    conf = float(raw_conf.item() if hasattr(raw_conf, "item") else raw_conf)

                    # Map class ID
                    meta = TARGET_CLASSES_MAP.get(cls_id)
                    if not meta:
                        # Fallback for known RDD classes if mapped differently
                        class_code = f"D{cls_id:02d}"
                        meta = {
                            "code": class_code,
                            "name": "Road Distress",
                            "hazard_type": "crack",
                            "severity": "medium",
                        }

                    # Box coordinates in xyxy pixel format
                    raw_xyxy = box.xyxy[0]
                    xyxy = raw_xyxy.tolist() if hasattr(raw_xyxy, "tolist") else list(raw_xyxy)
                    px_x1, px_y1, px_x2, px_y2 = xyxy

                    # Compute normalized coordinates
                    norm_xmin = max(0.0, min(1.0, px_x1 / img_w))
                    norm_ymin = max(0.0, min(1.0, px_y1 / img_h))
                    norm_xmax = max(0.0, min(1.0, px_x2 / img_w))
                    norm_ymax = max(0.0, min(1.0, px_y2 / img_h))
                    norm_w = max(0.0, norm_xmax - norm_xmin)
                    norm_h = max(0.0, norm_ymax - norm_ymin)

                    bbox = BoundingBox(
                        xmin=round(norm_xmin, 4),
                        ymin=round(norm_ymin, 4),
                        xmax=round(norm_xmax, 4),
                        ymax=round(norm_ymax, 4),
                        width=round(norm_w, 4),
                        height=round(norm_h, 4),
                        pixel_box=[int(px_x1), int(px_y1), int(px_x2), int(px_y2)],
                    )

                    detections.append(
                        DamageDetectionItem(
                            class_id=cls_id,
                            class_code=meta["code"],
                            class_name=meta["name"],
                            confidence=round(conf, 4),
                            box=bbox,
                            suggested_hazard_type=meta["hazard_type"],
                            suggested_severity=meta["severity"],
                        )
                    )

        # Render annotated image with bounding boxes
        annotated_url = self._render_annotated_image(img_path, detections, img_w, img_h)

        return DamageDetectionResponse(
            success=True,
            model_name="YOLO-RoadDamage-Detector",
            model_version="1.0.0",
            device=self.device,
            detections_count=len(detections),
            detections=detections,
            inference_time_ms=round(latency_ms, 2),
            image_width=img_w,
            image_height=img_h,
            annotated_image_url=annotated_url,
        )

    async def detect_async(
        self,
        image_path: str | Path,
        confidence_threshold: Optional[float] = None,
    ) -> DamageDetectionResponse:
        """Asynchronously dispatch detection to worker thread to avoid blocking event loop."""
        return await asyncio.to_thread(self.detect_sync, image_path, confidence_threshold)


# Global detector singleton
detector_service = RoadDamageDetector()
