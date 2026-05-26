"""
能源数据异常检测模型
支持：Isolation Forest / 统计规则 / Z-Score
"""
import logging
from typing import Optional
from datetime import datetime, timezone

import numpy as np

logger = logging.getLogger(__name__)


def detect_anomalies(
    data: np.ndarray,
    method: str = "isolation_forest",
    params: Optional[dict] = None,
) -> dict:
    """
    异常检测

    Args:
        data: 输入数据 [n_samples, n_features]
        method: 检测方法
        params: 方法参数

    Returns:
        包含 anomaly_indices, scores, threshold 的字典
    """
    if params is None:
        params = {}

    if method == "isolation_forest":
        return _isolation_forest(data, params)
    elif method == "zscore":
        return _zscore_detection(data, params)
    elif method == "iqr":
        return _iqr_detection(data, params)
    elif method == "statistical":
        return _statistical_rules(data, params)
    else:
        return _isolation_forest(data, params)


def _isolation_forest(data: np.ndarray, params: dict) -> dict:
    """Isolation Forest 异常检测"""
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data)

    model = IsolationForest(
        n_estimators=params.get("n_estimators", 100),
        contamination=params.get("contamination", 0.05),
        random_state=42,
        n_jobs=-1,
    )
    predictions = model.fit_predict(data_scaled)
    scores = model.decision_function(data_scaled)

    anomaly_indices = np.where(predictions == -1)[0].tolist()

    return {
        "method": "isolation_forest",
        "anomaly_count": len(anomaly_indices),
        "total_count": len(data),
        "anomaly_rate": round(len(anomaly_indices) / max(len(data), 1) * 100, 2),
        "anomaly_indices": anomaly_indices[:100],
        "scores": scores.tolist()[:100],
        "threshold": float(np.percentile(scores, 5)),
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }


def _zscore_detection(data: np.ndarray, params: dict) -> dict:
    """Z-Score 异常检测"""
    threshold = params.get("threshold", 3.0)
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    z_scores = np.abs((data - np.mean(data, axis=0)) / np.maximum(np.std(data, axis=0), 1e-8))
    anomaly_mask = np.any(z_scores > threshold, axis=1)
    anomaly_indices = np.where(anomaly_mask)[0].tolist()

    return {
        "method": "zscore",
        "anomaly_count": len(anomaly_indices),
        "total_count": len(data),
        "anomaly_rate": round(len(anomaly_indices) / max(len(data), 1) * 100, 2),
        "anomaly_indices": anomaly_indices[:100],
        "threshold": threshold,
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }


def _iqr_detection(data: np.ndarray, params: dict) -> dict:
    """IQR 异常检测"""
    multiplier = params.get("multiplier", 1.5)
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    q1 = np.percentile(data, 25, axis=0)
    q3 = np.percentile(data, 75, axis=0)
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr

    anomaly_mask = np.any((data < lower) | (data > upper), axis=1)
    anomaly_indices = np.where(anomaly_mask)[0].tolist()

    return {
        "method": "iqr",
        "anomaly_count": len(anomaly_indices),
        "total_count": len(data),
        "anomaly_rate": round(len(anomaly_indices) / max(len(data), 1) * 100, 2),
        "anomaly_indices": anomaly_indices[:100],
        "lower_bound": lower.tolist(),
        "upper_bound": upper.tolist(),
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }


def _statistical_rules(data: np.ndarray, params: dict) -> dict:
    """统计规则引擎（3-sigma + 趋势突变）"""
    sigma_threshold = params.get("sigma", 3.0)
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    anomalies = []

    for col in range(data.shape[1]):
        col_data = data[:, col]
        mean = np.mean(col_data)
        std = np.std(col_data)

        # 3-sigma 规则
        sigma_anomalies = np.where(np.abs(col_data - mean) > sigma_threshold * std)[0]

        # 趋势突变检测（一阶差分）
        diff = np.abs(np.diff(col_data))
        diff_mean = np.mean(diff)
        diff_std = np.std(diff)
        trend_anomalies = np.where(diff > diff_mean + 2 * diff_std)[0] + 1

        anomalies.extend(sigma_anomalies.tolist())
        anomalies.extend(trend_anomalies.tolist())

    anomaly_indices = sorted(set(anomalies))

    return {
        "method": "statistical",
        "anomaly_count": len(anomaly_indices),
        "total_count": len(data),
        "anomaly_rate": round(len(anomaly_indices) / max(len(data), 1) * 100, 2),
        "anomaly_indices": anomaly_indices[:100],
        "rules": ["3-sigma", "trend-break"],
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }
