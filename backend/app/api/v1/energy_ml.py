"""
能源机器学习 API
负荷预测 / 异常检测 / DP-SGD / PSI
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.utils.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 请求模型 ====================

class LoadForecastRequest(BaseModel):
    features: list = Field(description="特征矩阵 [[temp, humidity, wind, irradiance, hour, dow, month], ...]")
    labels: list = Field(description="目标值 [load_kw, ...]")
    algorithm: str = Field(default="gradient_boosting", description="算法: gradient_boosting/random_forest/xgboost/lasso")
    test_size: float = Field(default=0.2, description="测试集比例")


class AnomalyDetectionRequest(BaseModel):
    data: list = Field(description="输入数据 [[feature1, feature2, ...], ...]")
    method: str = Field(default="isolation_forest", description="方法: isolation_forest/zscore/iqr/statistical")
    params: Optional[dict] = Field(default=None, description="方法参数")


class DPSGDRequest(BaseModel):
    gradient: list = Field(description="梯度向量")
    epsilon: float = Field(default=1.0, description="隐私预算 ε")
    delta: float = Field(default=1e-5, description="失败概率 δ")
    sensitivity: float = Field(default=1.0, description="梯度敏感度")
    batch_size: int = Field(default=32, description="批次大小")


class PSIRequest(BaseModel):
    party_a: List[str] = Field(description="A方集合")
    party_b: List[str] = Field(description="B方集合")


# ==================== API 端点 ====================

@router.post("/load-forecast/train", summary="训练负荷预测模型")
async def train_load_forecast(request: LoadForecastRequest, user: dict = Depends(get_current_user)):
    """使用真实 sklearn 训练负荷预测模型"""
    try:
        import numpy as np
        from app.services.energy_models.load_forecast import train_load_forecast_model

        features = np.array(request.features)
        labels = np.array(request.labels)

        if features.shape[0] != labels.shape[0]:
            raise HTTPException(status_code=400, detail="特征和标签数量不匹配")

        result = train_load_forecast_model(features, labels, request.algorithm, test_size=request.test_size)
        return {"code": 0, "message": "训练成功", "data": result}
    except ImportError:
        raise HTTPException(status_code=500, detail="sklearn 未安装，请安装 scikit-learn")
    except Exception as e:
        logger.error(f"Load forecast training failed: {e}")
        raise HTTPException(status_code=500, detail=f"训练失败: {str(e)}")


@router.post("/anomaly-detection/detect", summary="异常检测")
async def detect_anomalies(request: AnomalyDetectionRequest, user: dict = Depends(get_current_user)):
    """使用多种算法进行异常检测"""
    try:
        import numpy as np
        from app.services.energy_models.anomaly_detection import detect_anomalies

        data = np.array(request.data)
        result = detect_anomalies(data, request.method, request.params)
        return {"code": 0, "message": "检测完成", "data": result}
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@router.post("/dp-sgd/apply", summary="应用 DP-SGD")
async def apply_dp_sgd(request: DPSGDRequest, user: dict = Depends(get_current_user)):
    """对梯度应用差分隐私噪声"""
    try:
        import numpy as np
        from app.services.energy_models.dp_sgd import apply_dp_sgd

        gradient = np.array(request.gradient)
        result = apply_dp_sgd(gradient, request.epsilon, request.delta, request.sensitivity, request.batch_size)
        # 不返回 noisy_gradient（太大），只返回元数据
        result.pop("noisy_gradient", None)
        return {"code": 0, "message": "DP-SGD 应用成功", "data": result}
    except Exception as e:
        logger.error(f"DP-SGD failed: {e}")
        raise HTTPException(status_code=500, detail=f"DP-SGD 失败: {str(e)}")


@router.post("/psi/intersect", summary="隐私集合求交")
async def psi_intersect(request: PSIRequest, user: dict = Depends(get_current_user)):
    """运行 ECDH-PSI 隐私集合求交协议"""
    try:
        from app.services.energy_models.psi_service import run_psi_protocol

        if len(request.party_a) > 10000 or len(request.party_b) > 10000:
            raise HTTPException(status_code=400, detail="集合大小不能超过 10000")

        result = run_psi_protocol(request.party_a, request.party_b)
        return {"code": 0, "message": "PSI 完成", "data": result}
    except Exception as e:
        logger.error(f"PSI failed: {e}")
        raise HTTPException(status_code=500, detail=f"PSI 失败: {str(e)}")
