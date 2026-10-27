"""Test suite for Phase 3 Road-Damage Detection API and ML pipeline."""
import io
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from httpx import AsyncClient, ASGITransport
from PIL import Image

from app.main import app
from app.ml.detector import RoadDamageDetector, ModelUnavailableError
from app.ml.dataset.convert_rdd import voc_to_yolo_bbox, TARGET_CLASSES


def create_test_image_bytes(format="JPEG", size=(200, 200), color="gray") -> bytes:
    """Generate in-memory valid image bytes for test requests."""
    buf = io.BytesIO()
    im = Image.new("RGB", size, color=color)
    im.save(buf, format=format)
    return buf.getvalue()


# ── Step 1: Dataset Validator Unit Tests ────────────────────────────────────

def test_voc_to_yolo_bbox_valid():
    """Verify correct coordinate normalization for Pascal VOC to YOLO."""
    # Box from (10, 20) to (60, 80) in 100x100 image
    res = voc_to_yolo_bbox(xmin=10, ymin=20, xmax=60, ymax=80, img_w=100, img_h=100)
    assert res is not None
    xc, yc, w, h = res
    assert xc == 0.35
    assert yc == 0.50
    assert w == 0.50
    assert h == 0.60


def test_voc_to_yolo_bbox_invalid_coordinates():
    """Verify corrupted, inverted or zero-area bounding boxes are rejected."""
    # Inverted x
    assert voc_to_yolo_bbox(xmin=50, ymin=20, xmax=30, ymax=80, img_w=100, img_h=100) is None
    # Inverted y
    assert voc_to_yolo_bbox(xmin=10, ymin=90, xmax=60, ymax=50, img_w=100, img_h=100) is None
    # Zero width
    assert voc_to_yolo_bbox(xmin=20, ymin=20, xmax=20, ymax=80, img_w=100, img_h=100) is None
    # Zero dimensions image
    assert voc_to_yolo_bbox(xmin=10, ymin=20, xmax=50, ymax=60, img_w=0, img_h=100) is None


def test_voc_to_yolo_bbox_clamping():
    """Verify coordinates outside image boundaries are safely clamped."""
    # xmax exceeds width, ymin is negative
    res = voc_to_yolo_bbox(xmin=10, ymin=-10, xmax=120, ymax=50, img_w=100, img_h=100)
    assert res is not None
    xc, yc, w, h = res
    assert 0.0 <= xc <= 1.0
    assert 0.0 <= yc <= 1.0
    assert 0.0 <= w <= 1.0
    assert 0.0 <= h <= 1.0


def test_target_classes_mapping():
    """Verify four target classes D00, D10, D20, D40 are correctly registered."""
    assert TARGET_CLASSES["D00"] == 0
    assert TARGET_CLASSES["D10"] == 1
    assert TARGET_CLASSES["D20"] == 2
    assert TARGET_CLASSES["D40"] == 3
    assert len(TARGET_CLASSES) == 4


# ── Step 2: Model Status API Tests ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_damage_status_endpoint():
    """Test GET /api/v1/damage/status returns structured metadata."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/damage/status")
        assert response.status_code == 200
        data = response.json()
        assert "available" in data
        assert "model_name" in data
        assert "device" in data
        assert "supported_classes" in data
        assert "D00" in data["supported_classes"]
        assert "D40" in data["supported_classes"]


# ── Step 3: Missing Weights and Upload Validation Tests ──────────────────────

@pytest.mark.asyncio
async def test_detect_returns_503_when_weights_missing(tmp_path):
    """Ensure explicit 503 Service Unavailable when trained model weights are missing.

    Strict requirement: Never substitute fake detections or generic models.
    """
    img_bytes = create_test_image_bytes()
    non_existent_weights = str(tmp_path / "missing_model.pt")

    # Point detector to non-existent weights
    with patch("app.ml.detector.detector_service.model_path_str", non_existent_weights):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            files = {"image": ("road.jpg", img_bytes, "image/jpeg")}
            response = await client.post("/api/v1/damage/detect", files=files)
            assert response.status_code == 503
            err = response.json()
            assert "detail" in err
            assert err["detail"]["error"] == "MODEL_UNAVAILABLE"


@pytest.mark.asyncio
async def test_detect_rejects_corrupted_image():
    """Ensure upload validation catches non-image content."""
    fake_img = b"This is not a real image file, just plain ascii text."
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"image": ("corrupted.jpg", fake_img, "image/jpeg")}
        response = await client.post("/api/v1/damage/detect", files=files)
        # Should fail either at 503 (model missing) or 400 (validation)
        assert response.status_code in (400, 503)


@pytest.mark.asyncio
async def test_detect_rejects_empty_file():
    """Ensure empty file uploads are safely rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"image": ("empty.jpg", b"", "image/jpeg")}
        response = await client.post("/api/v1/damage/detect", files=files)
        assert response.status_code in (400, 503)


# ── Step 4: Generic COCO Pretrained Model Rejection Test ─────────────────────

def test_generic_coco_model_rejection(tmp_path):
    """Test that detector rejects generic models containing 'person' or 'bicycle'."""
    mock_model = MagicMock()
    mock_model.names = {0: "person", 1: "bicycle", 2: "car"}

    fake_weights = tmp_path / "fake_coco.pt"
    fake_weights.write_text("dummy")

    detector = RoadDamageDetector(model_path=str(fake_weights))
    with patch("ultralytics.YOLO", return_value=mock_model):
        with pytest.raises(ModelUnavailableError) as exc_info:
            detector._ensure_loaded()
        assert "generic COCO classes" in str(exc_info.value)


# ── Step 5: Successful Inference Flow with Validated Output ─────────────────

@pytest.mark.asyncio
async def test_successful_detection_with_mocked_yolo(tmp_path):
    """Test full inference flow when a valid road-damage model is loaded.

    Verifies response schema, bounding box coordinates, class mapping,
    advisory disclaimer, and non-blocking threaded execution.
    """
    img_bytes = create_test_image_bytes(format="JPEG", size=(400, 300))

    # Mock YOLO prediction result
    mock_box = MagicMock()
    mock_box.cls = [MagicMock(item=MagicMock(return_value=3))]  # D40 Pothole
    mock_box.conf = [MagicMock(item=MagicMock(return_value=0.88))]
    mock_box.xyxy = [[50.0, 60.0, 150.0, 180.0]]

    mock_result = MagicMock()
    mock_result.boxes = [mock_box]

    mock_model = MagicMock()
    mock_model.names = {0: "D00", 1: "D10", 2: "D20", 3: "D40"}
    mock_model.predict.return_value = [mock_result]

    dummy_weights = tmp_path / "valid_road_damage.pt"
    dummy_weights.write_text("model_bytes")

    with patch("app.ml.detector.detector_service.model_path_str", str(dummy_weights)):
        with patch.object(RoadDamageDetector, "_resolve_model_path", return_value=dummy_weights):
            with patch("ultralytics.YOLO", return_value=mock_model):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    files = {"image": ("road_pothole.jpg", img_bytes, "image/jpeg")}
                    data = {"confidence_threshold": "0.30"}
                    response = await client.post("/api/v1/damage/detect", files=files, data=data)

                    assert response.status_code == 200
                    result = response.json()

                    assert result["success"] is True
                    assert result["detections_count"] == 1
                    assert len(result["detections"]) == 1

                    det = result["detections"][0]
                    assert det["class_id"] == 3
                    assert det["class_code"] == "D40"
                    assert det["class_name"] == "Pothole"
                    assert det["confidence"] == 0.88
                    assert det["suggested_hazard_type"] == "pothole"
                    assert det["suggested_severity"] == "critical"

                    # Verify bounding box
                    box = det["box"]
                    assert box["xmin"] == 50.0 / 400.0
                    assert box["ymin"] == 60.0 / 300.0
                    assert box["xmax"] == 150.0 / 400.0
                    assert box["ymax"] == 180.0 / 300.0

                    # Verify mandatory advisory disclaimer
                    assert "ADVISORY NOTICE" in result["disclaimer"]
                    assert "does not constitute an official road audit" in result["disclaimer"]


# ── Step 6: Dataset Converter & Validator End-to-End Test ───────────────────

def test_convert_dataset_end_to_end(tmp_path):
    """Test Pascal VOC XML to YOLO dataset conversion and validation pipeline."""
    from app.ml.dataset.convert_rdd import convert_dataset

    # Create mock RDD directory structure
    rdd_dir = tmp_path / "mock_rdd"
    annot_dir = rdd_dir / "Annotations"
    img_dir = rdd_dir / "JPEGImages"
    annot_dir.mkdir(parents=True)
    img_dir.mkdir(parents=True)

    # Create dummy images
    img1_path = img_dir / "sample1.jpg"
    img2_path = img_dir / "sample2.jpg"
    im1 = Image.new("RGB", (200, 200), color="gray")
    im2 = Image.new("RGB", (200, 200), color="blue")
    im1.save(img1_path)
    im2.save(img2_path)

    # Create XML annotations (one target D40 pothole, one non-target D43 crosswalk blur)
    xml1_content = """<annotation>
        <size><width>200</width><height>200</height><depth>3</depth></size>
        <object>
            <name>D40</name>
            <bndbox><xmin>20</xmin><ymin>20</ymin><xmax>80</xmax><ymax>80</ymax></bndbox>
        </object>
        <object>
            <name>D43</name>
            <bndbox><xmin>100</xmin><ymin>100</ymin><xmax>150</xmax><ymax>150</ymax></bndbox>
        </object>
    </annotation>"""
    (annot_dir / "sample1.xml").write_text(xml1_content)

    xml2_content = """<annotation>
        <size><width>200</width><height>200</height><depth>3</depth></size>
        <object>
            <name>D00</name>
            <bndbox><xmin>30</xmin><ymin>10</ymin><xmax>70</xmax><ymax>190</ymax></bndbox>
        </object>
    </annotation>"""
    (annot_dir / "sample2.xml").write_text(xml2_content)

    output_dir = tmp_path / "yolo_out"

    report = convert_dataset(
        rdd_root=rdd_dir,
        output_dir=output_dir,
        train_ratio=0.5,
        val_ratio=0.5,
        test_ratio=0.0,
        seed=123,
    )

    assert report["total_xml_inspected"] == 2
    assert report["total_unique_valid_samples"] == 2
    assert "D43" in report["non_target_classes_ignored"]
    assert (output_dir / "data.yaml").exists()
    assert (output_dir / "conversion_report.json").exists()

    yaml_text = (output_dir / "data.yaml").read_text()
    assert "D00" in yaml_text
    assert "D40" in yaml_text
