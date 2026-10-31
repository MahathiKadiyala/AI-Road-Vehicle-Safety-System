"""Accident-Risk Evaluation and Probabilistic Calibration Metrics Module.

Computes mathematically rigorous classification and probability calibration metrics
using standard Python and NumPy without relying on uninstalled external dependencies:
  - Confusion Matrix (TP, FP, TN, FN)
  - Precision, Recall, Specificity, F1, Balanced Accuracy
  - ROC-AUC (Trapezoidal Area Under Receiver Operating Characteristic Curve)
  - PR-AUC (Average Precision / Area Under Precision-Recall Curve)
  - Brier Score (Mean Squared Probability Calibration Error)
  - Expected Calibration Error (ECE) and Binned Calibration Curve
  - Log-Loss / Binary Cross-Entropy
"""
import math
from typing import Dict, List, Optional, Tuple, Any


def compute_confusion_matrix(y_true: List[int], y_pred: List[int]) -> Dict[str, int]:
    """Compute binary confusion matrix counts."""
    if len(y_true) != len(y_pred):
        raise ValueError(f"Lengths must match: len(y_true)={len(y_true)}, len(y_pred)={len(y_pred)}")

    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)

    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def compute_classification_metrics(
    y_true: List[int],
    y_pred: List[int],
) -> Dict[str, float]:
    """Calculate accuracy, precision, recall, specificity, F1, and balanced accuracy."""
    cm = compute_confusion_matrix(y_true, y_pred)
    tp, fp, tn, fn = cm["tp"], cm["fp"], cm["tn"], cm["fn"]
    total = tp + fp + tn + fn

    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    f1 = (2.0 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    balanced_acc = (recall + specificity) / 2.0

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "specificity": round(specificity, 4),
        "f1": round(f1, 4),
        "balanced_accuracy": round(balanced_acc, 4),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def compute_roc_auc(y_true: List[int], y_prob: List[float]) -> float:
    """Calculate ROC-AUC (Area Under ROC Curve) via the trapezoidal rule.

    Handles ties in predicted probability correctly.
    """
    if len(y_true) != len(y_prob):
        raise ValueError("Lengths must match.")

    n_pos = sum(1 for y in y_true if y == 1)
    n_neg = len(y_true) - n_pos

    if n_pos == 0 or n_neg == 0:
        return 0.5

    # Sort descending by predicted probability
    pairs = sorted(zip(y_prob, y_true), key=lambda x: x[0], reverse=True)

    # Compute ROC points
    tpr_list = [0.0]
    fpr_list = [0.0]

    cur_tp = 0
    cur_fp = 0

    idx = 0
    n = len(pairs)
    while idx < n:
        score = pairs[idx][0]
        # Process all ties at once
        while idx < n and pairs[idx][0] == score:
            if pairs[idx][1] == 1:
                cur_tp += 1
            else:
                cur_fp += 1
            idx += 1

        tpr_list.append(cur_tp / n_pos)
        fpr_list.append(cur_fp / n_neg)

    # Trapezoidal integration
    auc = 0.0
    for i in range(1, len(fpr_list)):
        dx = fpr_list[i] - fpr_list[i - 1]
        avg_y = (tpr_list[i] + tpr_list[i - 1]) / 2.0
        auc += dx * avg_y

    return round(max(0.0, min(1.0, auc)), 4)


def compute_pr_auc(y_true: List[int], y_prob: List[float]) -> float:
    """Calculate PR-AUC (Average Precision score / Area Under Precision-Recall curve)."""
    if len(y_true) != len(y_prob):
        raise ValueError("Lengths must match.")

    n_pos = sum(1 for y in y_true if y == 1)
    if n_pos == 0:
        return 0.0

    # Sort descending by predicted probability
    pairs = sorted(zip(y_prob, y_true), key=lambda x: x[0], reverse=True)

    prev_recall = 0.0
    cur_tp = 0
    ap = 0.0

    for idx, (_, yt) in enumerate(pairs, start=1):
        if yt == 1:
            cur_tp += 1
            current_precision = cur_tp / idx
            current_recall = cur_tp / n_pos
            recall_step = current_recall - prev_recall
            ap += current_precision * recall_step
            prev_recall = current_recall

    return round(max(0.0, min(1.0, ap)), 4)


def compute_brier_score(y_true: List[int], y_prob: List[float]) -> float:
    """Calculate Brier score: mean squared difference between predicted probabilities and labels.

    Score of 0.0 indicates perfect calibration; lower is better.
    """
    if len(y_true) != len(y_prob) or not y_true:
        raise ValueError("Inputs must be non-empty and matching length.")

    total_sq_err = sum((p - y) ** 2 for p, y in zip(y_prob, y_true))
    return round(total_sq_err / len(y_true), 4)


def compute_calibration_curve(
    y_true: List[int],
    y_prob: List[float],
    n_bins: int = 5,
) -> Dict[str, Any]:
    """Calculate calibration curve bins and Expected Calibration Error (ECE)."""
    if len(y_true) != len(y_prob) or not y_true:
        raise ValueError("Inputs must be non-empty and matching length.")

    bin_width = 1.0 / n_bins
    bins_data: List[Dict[str, Any]] = []
    total_samples = len(y_true)
    weighted_ece = 0.0

    for b in range(n_bins):
        low = b * bin_width
        high = (b + 1) * bin_width if b < n_bins - 1 else 1.0001

        bin_indices = [
            i for i, p in enumerate(y_prob)
            if low <= p < high or (b == n_bins - 1 and p == 1.0)
        ]
        count = len(bin_indices)

        if count > 0:
            mean_prob = sum(y_prob[i] for i in bin_indices) / count
            fraction_pos = sum(y_true[i] for i in bin_indices) / count
            gap = abs(mean_prob - fraction_pos)
            weighted_ece += (count / total_samples) * gap

            bins_data.append({
                "bin_index": b + 1,
                "range": f"[{low:.2f}, {min(1.0, (b + 1) * bin_width):.2f})",
                "sample_count": count,
                "mean_predicted_prob": round(mean_prob, 4),
                "fraction_positive": round(fraction_pos, 4),
                "calibration_gap": round(gap, 4),
            })
        else:
            bins_data.append({
                "bin_index": b + 1,
                "range": f"[{low:.2f}, {min(1.0, (b + 1) * bin_width):.2f})",
                "sample_count": 0,
                "mean_predicted_prob": None,
                "fraction_positive": None,
                "calibration_gap": None,
            })

    return {
        "expected_calibration_error": round(weighted_ece, 4),
        "bins": bins_data,
        "n_bins": n_bins,
    }


def compute_log_loss(y_true: List[int], y_prob: List[float], eps: float = 1e-15) -> float:
    """Calculate binary cross-entropy loss with epsilon clipping."""
    if len(y_true) != len(y_prob) or not y_true:
        raise ValueError("Inputs must be non-empty and matching length.")

    total_loss = 0.0
    for y, p in zip(y_true, y_prob):
        p_clipped = max(eps, min(1.0 - eps, p))
        total_loss -= (y * math.log(p_clipped) + (1.0 - y) * math.log(1.0 - p_clipped))

    return round(total_loss / len(y_true), 4)


def evaluate_risk_model(
    y_true: List[int],
    y_prob: List[float],
    threshold: float = 0.5,
    n_calibration_bins: int = 5,
) -> Dict[str, Any]:
    """Comprehensive evaluation returning classification, ranking, and calibration metrics."""
    if len(y_true) != len(y_prob) or not y_true:
        raise ValueError("Inputs must be non-empty and matching length.")

    y_pred = [1 if p >= threshold else 0 for p in y_prob]

    class_metrics = compute_classification_metrics(y_true, y_pred)
    roc_auc = compute_roc_auc(y_true, y_prob)
    pr_auc = compute_pr_auc(y_true, y_prob)
    brier = compute_brier_score(y_true, y_prob)
    log_loss = compute_log_loss(y_true, y_prob)
    calibration = compute_calibration_curve(y_true, y_prob, n_bins=n_calibration_bins)

    return {
        "threshold": threshold,
        "total_samples": len(y_true),
        "positive_samples": sum(y_true),
        "negative_samples": len(y_true) - sum(y_true),
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "brier_score": brier,
        "log_loss": log_loss,
        "expected_calibration_error": calibration["expected_calibration_error"],
        "accuracy": class_metrics["accuracy"],
        "precision": class_metrics["precision"],
        "recall": class_metrics["recall"],
        "specificity": class_metrics["specificity"],
        "f1": class_metrics["f1"],
        "balanced_accuracy": class_metrics["balanced_accuracy"],
        "confusion_matrix": {
            "tp": class_metrics["tp"],
            "fp": class_metrics["fp"],
            "tn": class_metrics["tn"],
            "fn": class_metrics["fn"],
        },
        "calibration_bins": calibration["bins"],
    }
