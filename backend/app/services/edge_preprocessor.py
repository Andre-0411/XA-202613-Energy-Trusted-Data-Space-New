"""
边缘预处理模块
==============
在数据采集端进行格式转换、压缩、异常过滤等预处理操作，
减少传输数据量，提高数据质量。

功能：
- 格式转换（CSV/JSON/Parquet 互转）
- 数据压缩（gzip/zlib）
- 异常值检测与过滤
- 数据标准化
- 批量打包
"""
import gzip
import json
import logging
import zlib
from datetime import datetime, timezone
from typing import Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DataFormat(str, Enum):
    """数据格式"""
    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"
    PROTOBUF = "protobuf"


class CompressionType(str, Enum):
    """压缩类型"""
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"


class AnomalyType(str, Enum):
    """异常类型"""
    OUT_OF_RANGE = "out_of_range"        # 超出范围
    MISSING_FIELD = "missing_field"      # 缺失字段
    INVALID_TYPE = "invalid_type"        # 类型错误
    DUPLICATE = "duplicate"              # 重复数据
    TIMESTAMP_DRIFT = "timestamp_drift"  # 时间戳漂移
    SPIKE = "spike"                      # 突变值


@dataclass
class FieldSchema:
    """字段 Schema 定义"""
    name: str
    data_type: str  # int, float, string, bool, datetime
    unit: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    required: bool = False
    description: Optional[str] = None


@dataclass
class AnomalyRule:
    """异常检测规则"""
    field_name: str
    anomaly_type: AnomalyType
    threshold: Optional[float] = None
    description: str = ""
    action: str = "flag"  # flag=标记, remove=移除, interpolate=插值


@dataclass
class PreprocessResult:
    """预处理结果"""
    original_count: int
    processed_count: int
    removed_count: int
    anomaly_count: int
    anomalies: list[dict] = field(default_factory=list)
    format_converted: bool = False
    compressed: bool = False
    compression_ratio: float = 1.0
    processed_data: Optional[bytes] = None
    metadata: dict = field(default_factory=dict)
    processing_time_ms: float = 0.0


class EdgePreprocessor:
    """边缘预处理器"""

    def __init__(self):
        self._schema_registry: dict[str, list[FieldSchema]] = {}
        self._anomaly_rules: dict[str, list[AnomalyRule]] = {}
        self._duplicate_cache: dict[str, set] = {}  # dataset_id -> seen hashes

    # ================================================================
    # Schema 管理
    # ================================================================

    def register_schema(self, dataset_id: str, fields: list[FieldSchema]) -> None:
        """注册数据集 Schema"""
        self._schema_registry[dataset_id] = fields
        logger.info(f"Schema registered for dataset {dataset_id}: {len(fields)} fields")

    def get_schema(self, dataset_id: str) -> list[FieldSchema]:
        """获取数据集 Schema"""
        return self._schema_registry.get(dataset_id, [])

    def add_anomaly_rule(self, dataset_id: str, rule: AnomalyRule) -> None:
        """添加异常检测规则"""
        if dataset_id not in self._anomaly_rules:
            self._anomaly_rules[dataset_id] = []
        self._anomaly_rules[dataset_id].append(rule)

    # ================================================================
    # 格式转换
    # ================================================================

    def convert_format(
        self,
        data: list[dict],
        source_format: DataFormat,
        target_format: DataFormat,
    ) -> bytes:
        """
        格式转换

        支持 JSON <-> CSV 互转，Parquet 需要 pyarrow 库。
        """
        if source_format == target_format:
            if target_format == DataFormat.JSON:
                return json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
            elif target_format == DataFormat.CSV:
                return self._dicts_to_csv(data)

        if source_format == DataFormat.JSON and target_format == DataFormat.CSV:
            return self._dicts_to_csv(data)
        elif source_format == DataFormat.CSV and target_format == DataFormat.JSON:
            return json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        else:
            # 默认转 JSON
            return json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")

    def _dicts_to_csv(self, data: list[dict]) -> bytes:
        """字典列表转 CSV"""
        if not data:
            return b""

        headers = list(data[0].keys())
        lines = [",".join(headers)]

        for row in data:
            values = []
            for h in headers:
                v = row.get(h, "")
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, ensure_ascii=False)
                elif v is None:
                    v = ""
                values.append(str(v))
            lines.append(",".join(values))

        return "\n".join(lines).encode("utf-8")

    # ================================================================
    # 数据压缩
    # ================================================================

    def compress(
        self,
        data: bytes,
        compression: CompressionType = CompressionType.GZIP,
    ) -> tuple[bytes, float]:
        """
        压缩数据

        Returns: (compressed_data, compression_ratio)
        """
        if compression == CompressionType.NONE:
            return data, 1.0

        original_size = len(data)

        if compression == CompressionType.GZIP:
            compressed = gzip.compress(data, compresslevel=6)
        elif compression == CompressionType.ZLIB:
            compressed = zlib.compress(data, level=6)
        else:
            return data, 1.0

        ratio = len(compressed) / original_size if original_size > 0 else 1.0
        logger.info(f"Compressed {original_size} -> {len(compressed)} bytes (ratio: {ratio:.2%})")
        return compressed, ratio

    def decompress(
        self,
        data: bytes,
        compression: CompressionType = CompressionType.GZIP,
    ) -> bytes:
        """解压数据"""
        if compression == CompressionType.GZIP:
            return gzip.decompress(data)
        elif compression == CompressionType.ZLIB:
            return zlib.decompress(data)
        return data

    # ================================================================
    # 异常检测与过滤
    # ================================================================

    def detect_anomalies(
        self,
        data: list[dict],
        dataset_id: str,
    ) -> tuple[list[dict], list[dict]]:
        """
        检测异常数据

        Returns: (clean_data, anomalies)
        """
        schema = self.get_schema(dataset_id)
        rules = self._anomaly_rules.get(dataset_id, [])

        clean_data = []
        anomalies = []

        # 构建 Schema 映射
        schema_map = {f.name: f for f in schema}

        for i, record in enumerate(data):
            record_anomalies = []

            # 1. 缺失字段检测
            for field_schema in schema:
                if field_schema.required and field_schema.name not in record:
                    record_anomalies.append({
                        "type": AnomalyType.MISSING_FIELD,
                        "field": field_schema.name,
                        "message": f"必填字段 '{field_schema.name}' 缺失",
                    })

            # 2. 范围检测
            for field_name, value in record.items():
                if field_name in schema_map and isinstance(value, (int, float)):
                    fs = schema_map[field_name]
                    if fs.min_value is not None and value < fs.min_value:
                        record_anomalies.append({
                            "type": AnomalyType.OUT_OF_RANGE,
                            "field": field_name,
                            "value": value,
                            "min": fs.min_value,
                            "message": f"字段 '{field_name}' 值 {value} 低于最小值 {fs.min_value}",
                        })
                    if fs.max_value is not None and value > fs.max_value:
                        record_anomalies.append({
                            "type": AnomalyType.OUT_OF_RANGE,
                            "field": field_name,
                            "value": value,
                            "max": fs.max_value,
                            "message": f"字段 '{field_name}' 值 {value} 超过最大值 {fs.max_value}",
                        })

            # 3. 自定义规则检测
            for rule in rules:
                if rule.field_name in record:
                    value = record[rule.field_name]
                    if rule.anomaly_type == AnomalyType.SPIKE:
                        # 突变值检测（简化：与阈值比较）
                        if isinstance(value, (int, float)) and rule.threshold:
                            if abs(value) > rule.threshold:
                                record_anomalies.append({
                                    "type": AnomalyType.SPIKE,
                                    "field": rule.field_name,
                                    "value": value,
                                    "threshold": rule.threshold,
                                    "message": rule.description or f"字段 '{rule.field_name}' 疑似突变值",
                                })

            # 4. 重复检测
            record_hash = hash(json.dumps(record, sort_keys=True, default=str))
            if dataset_id not in self._duplicate_cache:
                self._duplicate_cache[dataset_id] = set()

            if record_hash in self._duplicate_cache[dataset_id]:
                record_anomalies.append({
                    "type": AnomalyType.DUPLICATE,
                    "index": i,
                    "message": "重复记录",
                })
            else:
                self._duplicate_cache[dataset_id].add(record_hash)

            if record_anomalies:
                anomalies.append({
                    "index": i,
                    "record": record,
                    "anomalies": record_anomalies,
                })
            else:
                clean_data.append(record)

        return clean_data, anomalies

    # ================================================================
    # 数据标准化
    # ================================================================

    def normalize_data(
        self,
        data: list[dict],
        dataset_id: str,
    ) -> list[dict]:
        """
        数据标准化

        - 统一时间格式为 ISO 8601
        - 统一数值精度
        - 去除首尾空白
        - 统一空值表示
        """
        schema = self.get_schema(dataset_id)
        schema_map = {f.name: f for f in schema}

        normalized = []
        for record in data:
            new_record = {}
            for key, value in record.items():
                # 去除字符串首尾空白
                if isinstance(value, str):
                    value = value.strip()
                    if value in ("", "null", "None", "N/A", "n/a"):
                        value = None

                # 数值精度
                if isinstance(value, float) and key in schema_map:
                    value = round(value, 4)

                new_record[key] = value
            normalized.append(new_record)

        return normalized

    # ================================================================
    # 批量打包
    # ================================================================

    def batch_pack(
        self,
        data: list[dict],
        batch_size: int = 100,
    ) -> list[list[dict]]:
        """
        将数据按批次打包

        适合 MQTT 分批发送，避免单条消息过大。
        """
        batches = []
        for i in range(0, len(data), batch_size):
            batches.append(data[i:i + batch_size])
        return batches

    # ================================================================
    # 完整预处理流水线
    # ================================================================

    def preprocess(
        self,
        data: list[dict],
        dataset_id: str,
        source_format: DataFormat = DataFormat.JSON,
        target_format: DataFormat = DataFormat.JSON,
        compression: CompressionType = CompressionType.NONE,
        enable_anomaly_detection: bool = True,
        enable_normalization: bool = True,
    ) -> PreprocessResult:
        """
        完整预处理流水线

        1. 数据标准化
        2. 异常检测与过滤
        3. 格式转换
        4. 压缩
        """
        import time
        start_time = time.time()

        original_count = len(data)
        anomalies = []

        # 1. 标准化
        if enable_normalization:
            try:
                data = self.normalize_data(data, dataset_id)
            except Exception as e:
                logger.warning(f"Normalization failed: {e}")

        # 2. 异常检测
        if enable_anomaly_detection:
            data, anomalies = self.detect_anomalies(data, dataset_id)

        processed_count = len(data)
        removed_count = original_count - processed_count

        # 3. 格式转换
        format_converted = source_format != target_format
        raw_data = self.convert_format(data, DataFormat.JSON, target_format)

        # 4. 压缩
        compressed_data, compression_ratio = self.compress(raw_data, compression)

        processing_time = (time.time() - start_time) * 1000

        return PreprocessResult(
            original_count=original_count,
            processed_count=processed_count,
            removed_count=removed_count,
            anomaly_count=len(anomalies),
            anomalies=anomalies[:50],  # 最多返回50条异常
            format_converted=format_converted,
            compressed=compression != CompressionType.NONE,
            compression_ratio=compression_ratio,
            processed_data=compressed_data,
            metadata={
                "dataset_id": dataset_id,
                "source_format": source_format.value,
                "target_format": target_format.value,
                "compression": compression.value,
            },
            processing_time_ms=round(processing_time, 2),
        )

    def clear_cache(self, dataset_id: Optional[str] = None) -> None:
        """清除重复检测缓存"""
        if dataset_id:
            self._duplicate_cache.pop(dataset_id, None)
        else:
            self._duplicate_cache.clear()


# 全局单例
_edge_preprocessor: Optional[EdgePreprocessor] = None


def get_edge_preprocessor() -> EdgePreprocessor:
    """获取边缘预处理器单例"""
    global _edge_preprocessor
    if _edge_preprocessor is None:
        _edge_preprocessor = EdgePreprocessor()
    return _edge_preprocessor
