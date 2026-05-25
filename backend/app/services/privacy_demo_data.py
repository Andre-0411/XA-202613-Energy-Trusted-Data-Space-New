"""
隐私计算演示数据服务 (Privacy Compute Demo Data Service)
======================================================

生成能源领域隐私计算演示数据集，用于 HE/MPC/DP 等隐私计算场景的演示和测试。

数据集:
  - 负荷预测数据集 (load_forecast): 1000条记录
  - 电价数据集 (electricity_price): 500条记录
  - 光伏出力数据集 (photovoltaic_output): 800条记录
  - 风电出力数据集 (wind_power_output): 600条记录

所有数据使用真实数值范围和合理的统计分布（正态分布、周期性）。
支持导出为 CSV 和 JSON 格式。
"""
import math
import random
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ==================== 数据集配置 ====================

DATASET_CONFIGS = {
    "load_forecast": {
        "name": "负荷预测数据集",
        "description": "电力系统负荷预测相关数据，包含气象因素与负荷值",
        "record_count": 1000,
        "fields": ["timestamp", "temperature", "humidity", "wind_speed", "solar_irradiance", "load_mw"],
    },
    "electricity_price": {
        "name": "电价数据集",
        "description": "实时电价与预测电价数据，包含供需比信息",
        "record_count": 500,
        "fields": ["timestamp", "realtime_price", "forecast_price", "supply_demand_ratio"],
    },
    "photovoltaic_output": {
        "name": "光伏出力数据集",
        "description": "光伏发电出力数据，包含辐照度和温度因素",
        "record_count": 800,
        "fields": ["timestamp", "irradiance", "ambient_temp", "module_temp", "output_power"],
    },
    "wind_power_output": {
        "name": "风电出力数据集",
        "description": "风力发电出力数据，包含风速风向和温度因素",
        "record_count": 600,
        "fields": ["timestamp", "wind_speed", "wind_direction", "temperature", "output_power"],
    },
}


# ==================== 数据生成函数 ====================

def _generate_timestamps(
    count: int,
    start_time: Optional[datetime] = None,
    interval_minutes: int = 15,
) -> list[str]:
    """
    生成时间戳序列

    Args:
        count: 时间戳数量
        start_time: 起始时间（默认为2025-01-01 00:00:00 UTC）
        interval_minutes: 时间间隔（分钟）

    Returns:
        ISO格式时间戳列表
    """
    if start_time is None:
        start_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    return [
        (start_time + timedelta(minutes=i * interval_minutes)).isoformat()
        for i in range(count)
    ]


def _clamp(value: float, min_val: float, max_val: float) -> float:
    """将值限制在指定范围内"""
    return max(min_val, min(max_val, value))


def generate_load_forecast_dataset(
    count: int = 1000,
    export_format: Optional[str] = None,
) -> dict:
    """
    生成负荷预测数据集

    数据特征:
    - 温度: -10 ~ 40 ℃，带季节性周期（正弦函数 + 随机扰动）
    - 湿度: 20 ~ 95 %，与温度负相关
    - 风速: 0 ~ 25 m/s，服从 Weibull 分布近似
    - 太阳辐照度: 0 ~ 1200 W/m²，白天有日照时非零
    - 负荷: 500 ~ 5000 MW，与温度和时间相关

    Args:
        count: 记录数量
        export_format: 导出格式 ("csv" / "json" / None)

    Returns:
        数据集字典，包含 records 和 metadata
    """
    timestamps = _generate_timestamps(count, interval_minutes=15)
    records = []

    for i in range(count):
        # 时间特征（用于周期性）
        hour = (i * 15 / 60) % 24
        day_of_year = (i * 15 / 60 / 24) % 365

        # 温度: 季节性 + 日变化 + 随机噪声
        seasonal = 15 + 20 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
        daily_var = 5 * math.sin(2 * math.pi * (hour - 6) / 24)
        temperature = _clamp(
            seasonal + daily_var + random.gauss(0, 2),
            -10.0, 40.0,
        )

        # 湿度: 与温度负相关
        base_humidity = 70 - 0.8 * temperature
        humidity = _clamp(base_humidity + random.gauss(0, 8), 20.0, 95.0)

        # 风速: Weibull 分布近似
        wind_speed = _clamp(random.weibullvariate(5.0, 2.0), 0.0, 25.0)

        # 太阳辐照度: 白天非零，中午最大
        if 6 <= hour <= 18:
            solar_factor = math.sin(math.pi * (hour - 6) / 12)
            solar_irradiance = _clamp(
                1000 * solar_factor * random.uniform(0.5, 1.0) + random.gauss(0, 30),
                0.0, 1200.0,
            )
        else:
            solar_irradiance = 0.0

        # 负荷: 基础负荷 + 温度效应 + 日负荷曲线
        base_load = 2000
        temp_effect = 50 * abs(temperature - 20)  # 偏离舒适区增加负荷
        peak_hour_factor = 1.0 + 0.3 * math.sin(math.pi * (hour - 8) / 8) if 8 <= hour <= 16 else 0.85
        load_mw = _clamp(
            (base_load + temp_effect) * peak_hour_factor + random.gauss(0, 100),
            500.0, 5000.0,
        )

        records.append({
            "timestamp": timestamps[i],
            "temperature": round(temperature, 2),
            "humidity": round(humidity, 2),
            "wind_speed": round(wind_speed, 2),
            "solar_irradiance": round(solar_irradiance, 2),
            "load_mw": round(load_mw, 2),
        })

    result = {
        "dataset": "load_forecast",
        "name": "负荷预测数据集",
        "record_count": len(records),
        "fields": ["timestamp", "temperature", "humidity", "wind_speed", "solar_irradiance", "load_mw"],
        "value_ranges": {
            "temperature": {"min": -10, "max": 40, "unit": "℃"},
            "humidity": {"min": 20, "max": 95, "unit": "%"},
            "wind_speed": {"min": 0, "max": 25, "unit": "m/s"},
            "solar_irradiance": {"min": 0, "max": 1200, "unit": "W/m²"},
            "load_mw": {"min": 500, "max": 5000, "unit": "MW"},
        },
        "records": records,
    }

    if export_format:
        result["export"] = _export_data(records, export_format, "load_forecast")

    logger.info(f"Generated load_forecast dataset: {len(records)} records")
    return result


def generate_electricity_price_dataset(
    count: int = 500,
    export_format: Optional[str] = None,
) -> dict:
    """
    生成电价数据集

    数据特征:
    - 实时电价: 200 ~ 800 元/MWh，有峰谷波动
    - 预测电价: 基于实时电价 + 随机偏差
    - 供需比: 0.8 ~ 1.3，影响电价

    Args:
        count: 记录数量
        export_format: 导出格式

    Returns:
        数据集字典
    """
    timestamps = _generate_timestamps(count, interval_minutes=30)
    records = []

    for i in range(count):
        hour = (i * 30 / 60) % 24

        # 供需比: 基础值 + 波动
        supply_demand_ratio = _clamp(1.0 + 0.15 * math.sin(2 * math.pi * (hour - 10) / 24) + random.gauss(0, 0.05), 0.8, 1.3)

        # 实时电价: 基础电价 * 负荷系数 * 供需效应
        base_price = 400
        peak_factor = 1.0 + 0.5 * math.sin(math.pi * (hour - 8) / 8) if 8 <= hour <= 20 else 0.7
        supply_effect = 1.0 / supply_demand_ratio
        realtime_price = _clamp(
            base_price * peak_factor * supply_effect + random.gauss(0, 30),
            200.0, 800.0,
        )

        # 预测电价: 实时电价 + 系统性偏差 + 随机误差
        forecast_price = _clamp(
            realtime_price * (1 + random.gauss(0, 0.03)),
            200.0, 800.0,
        )

        records.append({
            "timestamp": timestamps[i],
            "realtime_price": round(realtime_price, 2),
            "forecast_price": round(forecast_price, 2),
            "supply_demand_ratio": round(supply_demand_ratio, 4),
        })

    result = {
        "dataset": "electricity_price",
        "name": "电价数据集",
        "record_count": len(records),
        "fields": ["timestamp", "realtime_price", "forecast_price", "supply_demand_ratio"],
        "value_ranges": {
            "realtime_price": {"min": 200, "max": 800, "unit": "元/MWh"},
            "forecast_price": {"min": 200, "max": 800, "unit": "元/MWh"},
            "supply_demand_ratio": {"min": 0.8, "max": 1.3, "unit": ""},
        },
        "records": records,
    }

    if export_format:
        result["export"] = _export_data(records, export_format, "electricity_price")

    logger.info(f"Generated electricity_price dataset: {len(records)} records")
    return result


def generate_photovoltaic_output_dataset(
    count: int = 800,
    export_format: Optional[str] = None,
) -> dict:
    """
    生成光伏出力数据集

    数据特征:
    - 辐照度: 0 ~ 1200 W/m²，白天有日照时非零
    - 环境温度: -5 ~ 40 ℃
    - 组件温度: 环境温度 + 辐照度加热效应
    - 出力值: 0 ~ 50 MW，与辐照度和温度相关

    Args:
        count: 记录数量
        export_format: 导出格式

    Returns:
        数据集字典
    """
    timestamps = _generate_timestamps(count, interval_minutes=15)
    records = []

    for i in range(count):
        hour = (i * 15 / 60) % 24
        day_of_year = (i * 15 / 60 / 24) % 365

        # 环境温度
        seasonal = 15 + 15 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
        daily_var = 4 * math.sin(2 * math.pi * (hour - 6) / 24)
        ambient_temp = _clamp(seasonal + daily_var + random.gauss(0, 2), -5.0, 40.0)

        # 辐照度
        if 6 <= hour <= 18:
            solar_factor = math.sin(math.pi * (hour - 6) / 12)
            cloud_factor = random.uniform(0.3, 1.0)
            irradiance = _clamp(1000 * solar_factor * cloud_factor + random.gauss(0, 20), 0.0, 1200.0)
        else:
            irradiance = 0.0

        # 组件温度: 环境温度 + NOCT 效应
        module_temp = ambient_temp + irradiance * 0.03 + random.gauss(0, 1)

        # 出力值: P = P_stc * (G/G_stc) * (1 + γ * (T_module - T_stc))
        # P_stc = 50 MW, G_stc = 1000 W/m², T_stc = 25℃, γ = -0.004/℃
        if irradiance > 0:
            temp_coeff = -0.004
            output_power = 50 * (irradiance / 1000) * (1 + temp_coeff * (module_temp - 25))
            output_power = _clamp(output_power * random.uniform(0.9, 1.05), 0.0, 50.0)
        else:
            output_power = 0.0

        records.append({
            "timestamp": timestamps[i],
            "irradiance": round(irradiance, 2),
            "ambient_temp": round(ambient_temp, 2),
            "module_temp": round(module_temp, 2),
            "output_power": round(output_power, 3),
        })

    result = {
        "dataset": "photovoltaic_output",
        "name": "光伏出力数据集",
        "record_count": len(records),
        "fields": ["timestamp", "irradiance", "ambient_temp", "module_temp", "output_power"],
        "value_ranges": {
            "irradiance": {"min": 0, "max": 1200, "unit": "W/m²"},
            "ambient_temp": {"min": -5, "max": 40, "unit": "℃"},
            "module_temp": {"min": -5, "max": 65, "unit": "℃"},
            "output_power": {"min": 0, "max": 50, "unit": "MW"},
        },
        "records": records,
    }

    if export_format:
        result["export"] = _export_data(records, export_format, "photovoltaic_output")

    logger.info(f"Generated photovoltaic_output dataset: {len(records)} records")
    return result


def generate_wind_power_output_dataset(
    count: int = 600,
    export_format: Optional[str] = None,
) -> dict:
    """
    生成风电出力数据集

    数据特征:
    - 风速: 0 ~ 25 m/s，服从 Weibull 分布
    - 风向: 0 ~ 360°，有主导风向
    - 温度: -10 ~ 35 ℃
    - 出力值: 0 ~ 100 MW，与风速相关（含切入/额定/切出风速）

    Args:
        count: 记录数量
        export_format: 导出格式

    Returns:
        数据集字典
    """
    timestamps = _generate_timestamps(count, interval_minutes=20)
    records = []

    for i in range(count):
        hour = (i * 20 / 60) % 24
        day_of_year = (i * 20 / 60 / 24) % 365

        # 风速: Weibull 分布
        wind_speed = _clamp(random.weibullvariate(6.0, 2.0), 0.0, 25.0)

        # 风向: 主导风向 (225° 即西南风) + 正态扰动
        wind_direction = (225 + random.gauss(0, 40)) % 360

        # 温度
        seasonal = 12 + 18 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
        temperature = _clamp(seasonal + random.gauss(0, 3), -10.0, 35.0)

        # 出力值: 风机功率曲线
        cut_in_speed = 3.0     # 切入风速 m/s
        rated_speed = 12.0     # 额定风速 m/s
        cut_out_speed = 25.0   # 切出风速 m/s
        rated_power = 100.0    # 额定功率 MW

        if wind_speed < cut_in_speed or wind_speed >= cut_out_speed:
            output_power = 0.0
        elif wind_speed < rated_speed:
            # 立方关系
            output_power = rated_power * ((wind_speed - cut_in_speed) / (rated_speed - cut_in_speed)) ** 3
            output_power *= random.uniform(0.9, 1.0)
        else:
            output_power = rated_power * random.uniform(0.95, 1.0)

        output_power = round(_clamp(output_power, 0.0, 100.0), 3)

        records.append({
            "timestamp": timestamps[i],
            "wind_speed": round(wind_speed, 2),
            "wind_direction": round(wind_direction, 2),
            "temperature": round(temperature, 2),
            "output_power": output_power,
        })

    result = {
        "dataset": "wind_power_output",
        "name": "风电出力数据集",
        "record_count": len(records),
        "fields": ["timestamp", "wind_speed", "wind_direction", "temperature", "output_power"],
        "value_ranges": {
            "wind_speed": {"min": 0, "max": 25, "unit": "m/s"},
            "wind_direction": {"min": 0, "max": 360, "unit": "°"},
            "temperature": {"min": -10, "max": 35, "unit": "℃"},
            "output_power": {"min": 0, "max": 100, "unit": "MW"},
        },
        "records": records,
    }

    if export_format:
        result["export"] = _export_data(records, export_format, "wind_power_output")

    logger.info(f"Generated wind_power_output dataset: {len(records)} records")
    return result


# ==================== 数据集生成入口 ====================

_DATASET_GENERATORS = {
    "load_forecast": generate_load_forecast_dataset,
    "electricity_price": generate_electricity_price_dataset,
    "photovoltaic_output": generate_photovoltaic_output_dataset,
    "wind_power_output": generate_wind_power_output_dataset,
}


def generate_dataset(
    dataset_name: str,
    count: Optional[int] = None,
    export_format: Optional[str] = None,
) -> dict:
    """
    生成指定的隐私计算演示数据集

    Args:
        dataset_name: 数据集名称
            - "load_forecast": 负荷预测数据集（默认1000条）
            - "electricity_price": 电价数据集（默认500条）
            - "photovoltaic_output": 光伏出力数据集（默认800条）
            - "wind_power_output": 风电出力数据集（默认600条）
        count: 记录数量（None 使用默认值）
        export_format: 导出格式 ("csv" / "json" / None)

    Returns:
        数据集字典

    Raises:
        ValueError: 数据集名称不存在
    """
    if dataset_name not in _DATASET_GENERATORS:
        raise ValueError(
            f"未知数据集: {dataset_name}，可用: {list(_DATASET_GENERATORS.keys())}"
        )

    generator = _DATASET_GENERATORS[dataset_name]
    kwargs = {}
    if count is not None:
        kwargs["count"] = count
    if export_format is not None:
        kwargs["export_format"] = export_format

    return generator(**kwargs)


def list_datasets() -> list[dict]:
    """
    列出所有可用的演示数据集

    Returns:
        数据集信息列表
    """
    return [
        {
            "id": ds_id,
            "name": config["name"],
            "description": config["description"],
            "record_count": config["record_count"],
            "fields": config["fields"],
        }
        for ds_id, config in DATASET_CONFIGS.items()
    ]


def generate_all_datasets(export_format: Optional[str] = None) -> dict:
    """
    生成所有演示数据集

    Args:
        export_format: 导出格式

    Returns:
        所有数据集的字典
    """
    results = {}
    for ds_name in _DATASET_GENERATORS:
        results[ds_name] = generate_dataset(ds_name, export_format=export_format)
        # 不在汇总中包含完整 records，节省内存
        results[ds_name].pop("records", None)

    logger.info(f"Generated all {len(results)} demo datasets")
    return {
        "datasets": results,
        "total_records": sum(DATASET_CONFIGS[k]["record_count"] for k in DATASET_CONFIGS),
    }


# ==================== 导出辅助 ====================

def _export_data(records: list[dict], fmt: str, dataset_name: str) -> dict:
    """
    将记录导出为指定格式的字符串

    Args:
        records: 记录列表
        fmt: 导出格式 ("csv" / "json")
        dataset_name: 数据集名称

    Returns:
        包含格式和内容的字典
    """
    if not records:
        return {"format": fmt, "content": "", "error": "无数据"}

    if fmt == "csv":
        import io
        output = io.StringIO()
        fields = list(records[0].keys())
        output.write(",".join(fields) + "\n")
        for record in records:
            output.write(",".join(str(record[f]) for f in fields) + "\n")
        content = output.getvalue()
    elif fmt == "json":
        import json
        content = json.dumps(records, ensure_ascii=False, indent=2)
    else:
        return {"format": fmt, "content": "", "error": f"不支持的格式: {fmt}"}

    return {
        "format": fmt,
        "filename": f"{dataset_name}.{fmt}",
        "size_bytes": len(content.encode("utf-8")),
        "record_count": len(records),
        "content": content,
    }
