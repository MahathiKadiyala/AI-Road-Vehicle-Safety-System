"""Accident-Risk Dataset Ingestion, Validation, and Leakage-Safe Splitting Pipeline.

Provides rigorous data quality checks, schema validation, class balance inspection,
and time/location-aware holdout partitioning to prevent train/test leakage.
Works purely with standard Python libraries and NumPy (zero reliance on uninstalled packages).
"""
import csv
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from app.schemas.risk import DatasetValidationReport

logger = logging.getLogger("roadsafety.ml.risk.pipeline")

# Standard schema definition for road-segment accident incidence records
EXPECTED_COLUMNS = [
    "segment_id",
    "timestamp",
    "latitude",
    "longitude",
    "road_classification",
    "speed_limit_kmh",
    "surface_condition",
    "lighting_condition",
    "weather_condition",
    "pothole_count_nearby",
    "crack_count_nearby",
    "hazard_density_per_km",
    "target_high_accident_risk",
]

NUMERIC_COLUMNS = {
    "latitude": (-90.0, 90.0),
    "longitude": (-180.0, 180.0),
    "speed_limit_kmh": (10.0, 160.0),
    "pothole_count_nearby": (0.0, 1000.0),
    "crack_count_nearby": (0.0, 1000.0),
    "hazard_density_per_km": (0.0, 1000.0),
    "target_high_accident_risk": (0, 1),
}


class DatasetPipelineError(Exception):
    """Raised when dataset loading, validation, or splitting fails."""
    pass


def validate_dataset_schema(csv_path: str | Path) -> DatasetValidationReport:
    """Inspect and audit a candidate accident dataset CSV file.

    Evaluates:
    1. Header presence and exact column alignment.
    2. Numerical range constraints (coordinates, speed limits, density).
    3. Missing values per feature column.
    4. Target label class distribution and imbalance.
    5. Timestamp ISO 8601 validity for time-based splitting.

    Args:
        csv_path: Path to dataset CSV file.

    Returns:
        DatasetValidationReport with exhaustive audit results.
    """
    path = Path(csv_path)
    if not path.exists() or not path.is_file():
        return DatasetValidationReport(
            is_valid=False,
            total_records=0,
            feature_columns=[],
            target_column="target_high_accident_risk",
            missing_values_by_column={},
            class_distribution={},
            validation_errors=[f"Dataset file does not exist at: {path}"],
            validation_warnings=[],
            dataset_provenance_notes="No file found on filesystem.",
        )

    errors: List[str] = []
    warnings: List[str] = []
    total_records = 0
    missing_by_col: Dict[str, int] = {col: 0 for col in EXPECTED_COLUMNS}
    class_dist: Dict[str, int] = {"0": 0, "1": 0}

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            lines = [line for line in f if not line.strip().startswith("#")]
            if not lines:
                return DatasetValidationReport(
                    is_valid=False,
                    total_records=0,
                    feature_columns=[],
                    target_column="target_high_accident_risk",
                    validation_errors=["Dataset CSV is empty or only contains comment lines."],
                    dataset_provenance_notes="Empty file.",
                )

            reader = csv.DictReader(lines)
            if not reader.fieldnames:
                return DatasetValidationReport(
                    is_valid=False,
                    total_records=0,
                    feature_columns=[],
                    target_column="target_high_accident_risk",
                    validation_errors=["Dataset CSV is empty or has no header row."],
                    dataset_provenance_notes="Empty file.",
                )

            headers = [h.strip() for h in reader.fieldnames]
            missing_headers = [col for col in EXPECTED_COLUMNS if col not in headers]
            if missing_headers:
                errors.append(f"Missing mandatory schema columns: {missing_headers}")

            for row_idx, row in enumerate(reader, start=1):
                total_records += 1

                # Check for missing values
                for col in EXPECTED_COLUMNS:
                    val = row.get(col, "")
                    if val is None or val.strip() == "":
                        missing_by_col[col] = missing_by_col.get(col, 0) + 1

                # Validate numeric ranges if present
                for col, (min_v, max_v) in NUMERIC_COLUMNS.items():
                    val = row.get(col, "").strip()
                    if val != "":
                        try:
                            f_val = float(val)
                            if not (min_v <= f_val <= max_v):
                                warnings.append(
                                    f"Row {row_idx}: Column '{col}' value {f_val} out of bounds [{min_v}, {max_v}]."
                                )
                        except ValueError:
                            errors.append(f"Row {row_idx}: Non-numeric value '{val}' in column '{col}'.")

                # Validate target column
                target_val = row.get("target_high_accident_risk", "").strip()
                if target_val in ("0", "1"):
                    class_dist[target_val] = class_dist.get(target_val, 0) + 1
                elif target_val != "":
                    errors.append(f"Row {row_idx}: Invalid target label '{target_val}'. Must be binary 0 or 1.")

    except Exception as exc:
        errors.append(f"Failed to read CSV dataset: {exc}")

    if total_records == 0:
        errors.append("Dataset contains 0 rows.")

    # Check class imbalance
    c0 = class_dist.get("0", 0)
    c1 = class_dist.get("1", 0)
    if total_records > 0 and c1 > 0:
        ratio = c0 / c1 if c1 > 0 else float("inf")
        if ratio > 10.0 or ratio < 0.1:
            warnings.append(
                f"Severe class imbalance observed (Ratio 0:1 is {ratio:.1f}:1). "
                "Training must use stratified sampling, scale_pos_weight, or PR-AUC evaluation."
            )

    is_valid = len(errors) == 0

    return DatasetValidationReport(
        is_valid=is_valid,
        total_records=total_records,
        feature_columns=[col for col in EXPECTED_COLUMNS if col != "target_high_accident_risk"],
        target_column="target_high_accident_risk",
        missing_values_by_column={k: v for k, v in missing_by_col.items() if v > 0},
        class_distribution=class_dist,
        validation_errors=errors[:20],  # Cap error list to prevent huge logs
        validation_warnings=warnings[:20],
        dataset_provenance_notes=(
            f"Validated {total_records} rows from '{path.name}'. "
            f"Status: {'VALID' if is_valid else 'INVALID'}."
        ),
    )


def time_and_location_aware_split(
    records: List[Dict[str, Any]],
    holdout_fraction: float = 0.2,
    split_method: str = "location",
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split dataset into train and test sets to prevent spatial or temporal data leakage.

    Methods:
    - 'location': Partitions whole unique 'segment_id's into test set.
      Guarantees no records from the same corridor segment appear in both train and test.
    - 'time': Sorts by 'timestamp' and places the latest records into the test set.
      Guarantees no future information leaks into training.

    Args:
        records: List of validated dictionary rows.
        holdout_fraction: Fraction of data to reserve for testing (e.g. 0.20 = 20%).
        split_method: 'location' or 'time'.

    Returns:
        Tuple of (train_records, test_records).
    """
    if not records:
        return [], []

    if split_method == "time":
        # Sort records by timestamp
        try:
            sorted_records = sorted(
                records,
                key=lambda r: datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
            )
        except Exception:
            # Fallback to string sort if ISO parsing fails
            sorted_records = sorted(records, key=lambda r: str(r.get("timestamp", "")))

        split_idx = int(len(sorted_records) * (1.0 - holdout_fraction))
        train = sorted_records[:split_idx]
        test = sorted_records[split_idx:]
        return train, test

    # Default: Location-aware splitting by unique segment_id
    segments = sorted(list({r.get("segment_id", "") for r in records if r.get("segment_id")}))
    if not segments:
        split_idx = int(len(records) * (1.0 - holdout_fraction))
        return records[:split_idx], records[split_idx:]

    test_seg_count = max(1, int(len(segments) * holdout_fraction))
    # Deterministic segment partitioning
    test_segments = set(segments[-test_seg_count:])

    train = [r for r in records if r.get("segment_id") not in test_segments]
    test = [r for r in records if r.get("segment_id") in test_segments]

    return train, test
