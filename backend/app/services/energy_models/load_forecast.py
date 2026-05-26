"""
能源负荷预测模型
使用 sklearn 实现真实训练和评估
支持算法：XGBoost/RandomForest/GradientBoosting/Lasso
"""
import logging
import pickle
import base64
from typing import Optional
from datetime import datetime, timezone

import numpy as np

logger = logging.getLogger(__name__)


def train_load_forecast_model(
    features: np.ndarray,
    labels: np.ndarray,
    algorithm: str = "gradient_boosting",
    params: Optional[dict] = None,
    test_size: float = 0.2,
) -> dict:
    """
    训练负荷预测模型

    Args:
        features: 特征矩阵 [n_samples, n_features]，列：[温度, 湿度, 风速, 辐照度, 小时, 星期, 月份]
        labels: 目标值 [n_samples]，负荷值 (kW)
        algorithm: 算法选择
        params: 算法参数
        test_size: 测试集比例

    Returns:
        包含 metrics, model_base64, predictions 的字典
    """
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    if params is None:
        params = {}

    X_train, X_test, y_train, y_test = train_test_split(
        features, labels, test_size=test_size, random_state=42, shuffle=False
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = _create_model(algorithm, params)
    model.fit(X_train_scaled, y_train)
    y_pred = model.predict(X_test_scaled)

    # 计算评估指标
    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    r2 = float(r2_score(y_test, y_pred))
    mape = float(np.mean(np.abs((y_test - y_pred) / np.maximum(np.abs(y_test), 1e-8))) * 100)

    metrics = {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2": round(r2, 4),
        "mape": round(mape, 2),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "algorithm": algorithm,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }

    # 序列化模型
    model_bytes = pickle.dumps({"model": model, "scaler": scaler})
    model_base64 = base64.b64encode(model_bytes).decode("utf-8")

    return {
        "metrics": metrics,
        "model_base64": model_base64,
        "predictions": y_pred.tolist()[:100],
        "actual": y_test.tolist()[:100],
    }


def _create_model(algorithm: str, params: dict):
    """创建模型实例"""
    if algorithm == "gradient_boosting":
        from sklearn.ensemble import GradientBoostingRegressor
        return GradientBoostingRegressor(
            n_estimators=params.get("n_estimators", 200),
            max_depth=params.get("max_depth", 6),
            learning_rate=params.get("learning_rate", 0.1),
            subsample=params.get("subsample", 0.8),
            random_state=42,
        )
    elif algorithm == "random_forest":
        from sklearn.ensemble import RandomForestRegressor
        return RandomForestRegressor(
            n_estimators=params.get("n_estimators", 200),
            max_depth=params.get("max_depth", 12),
            random_state=42,
            n_jobs=-1,
        )
    elif algorithm == "xgboost":
        try:
            from xgboost import XGBRegressor
            return XGBRegressor(
                n_estimators=params.get("n_estimators", 300),
                max_depth=params.get("max_depth", 6),
                learning_rate=params.get("learning_rate", 0.05),
                subsample=params.get("subsample", 0.8),
                random_state=42,
                verbosity=0,
            )
        except ImportError:
            logger.warning("XGBoost not installed, falling back to GradientBoosting")
            from sklearn.ensemble import GradientBoostingRegressor
            return GradientBoostingRegressor(n_estimators=200, max_depth=6, random_state=42)
    elif algorithm == "lasso":
        from sklearn.linear_model import Lasso
        return Lasso(alpha=params.get("alpha", 0.1), random_state=42)
    else:
        from sklearn.ensemble import GradientBoostingRegressor
        return GradientBoostingRegressor(n_estimators=200, max_depth=6, random_state=42)


def predict_load(model_base64: str, features: np.ndarray) -> np.ndarray:
    """使用已训练模型进行预测"""
    model_bytes = base64.b64decode(model_base64)
    artifacts = pickle.loads(model_bytes)
    model = artifacts["model"]
    scaler = artifacts["scaler"]
    X_scaled = scaler.transform(features)
    return model.predict(X_scaled)
