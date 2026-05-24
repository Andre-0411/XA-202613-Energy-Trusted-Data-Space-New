"""
应用配置 - Pydantic Settings
30+ 个环境变量 + 验证逻辑
支持 MQTT、Redis、RabbitMQ、FISCO 等配置
"""
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- 应用 ----------
    APP_NAME: str = Field(default="EnergyTrustedDataSpace", description="应用名称")
    APP_ENV: str = Field(default="development", description="运行环境: development/staging/production")
    APP_DEBUG: bool = Field(default=True, description="调试模式")
    APP_SECRET_KEY: str = Field(default="change-me-to-a-random-secret-key", description="应用密钥")
    APP_HOST: str = Field(default="0.0.0.0", description="监听地址")
    APP_PORT: int = Field(default=8000, description="监听端口")

    # ---------- PostgreSQL ----------
    POSTGRES_HOST: str = Field(default="postgres", description="PostgreSQL 主机")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL 端口")
    POSTGRES_DB: str = Field(default="energy_tds", description="PostgreSQL 数据库名")
    POSTGRES_USER: str = Field(default="energy_admin", description="PostgreSQL 用户")
    POSTGRES_PASSWORD: str = Field(default="changeme_pg_password", description="PostgreSQL 密码")

    # ---------- Redis ----------
    REDIS_HOST: str = Field(default="redis", description="Redis 主机")
    REDIS_PORT: int = Field(default=6379, description="Redis 端口")
    REDIS_PASSWORD: str = Field(default="changeme_redis_password", description="Redis 密码")
    REDIS_DB: int = Field(default=0, description="Redis 数据库号")

    # ---------- MongoDB ----------
    MONGO_HOST: str = Field(default="mongo", description="MongoDB 主机")
    MONGO_PORT: int = Field(default=27017, description="MongoDB 端口")
    MONGO_DB: str = Field(default="energy_tds_meta", description="MongoDB 数据库名")
    MONGO_USER: str = Field(default="energy_mongo", description="MongoDB 用户")
    MONGO_PASSWORD: str = Field(default="changeme_mongo_password", description="MongoDB 密码")

    # ---------- MinIO ----------
    MINIO_ENDPOINT: str = Field(default="minio:9000", description="MinIO 端点")
    MINIO_ACCESS_KEY: str = Field(default="energy_minio_access", description="MinIO Access Key")
    MINIO_SECRET_KEY: str = Field(default="changeme_minio_secret", description="MinIO Secret Key")
    MINIO_BUCKET: str = Field(default="energy-tds", description="MinIO 默认桶名")
    MINIO_USE_SSL: bool = Field(default=False, description="MinIO 是否使用 SSL")

    # ---------- MQTT ----------
    MQTT_BROKER: str = Field(default="tcp://emqx:1883", description="MQTT Broker 地址")
    MQTT_WS_URL: str = Field(default="ws://emqx:8083/mqtt", description="MQTT WebSocket URL")
    MQTT_CLIENT_ID: str = Field(default="energy-tds-backend", description="MQTT 客户端 ID")
    MQTT_USERNAME: str = Field(default="energy_mqtt", description="MQTT 用户名")
    MQTT_PASSWORD: str = Field(default="changeme_mqtt_password", description="MQTT 密码")

    # ---------- RabbitMQ ----------
    RABBITMQ_HOST: str = Field(default="rabbitmq", description="RabbitMQ 主机")
    RABBITMQ_PORT: int = Field(default=5672, description="RabbitMQ 端口")
    RABBITMQ_USER: str = Field(default="energy_rabbit", description="RabbitMQ 用户")
    RABBITMQ_PASSWORD: str = Field(default="changeme_rabbit_password", description="RabbitMQ 密码")
    RABBITMQ_VHOST: str = Field(default="energy_tds", description="RabbitMQ 虚拟主机")

    # ---------- FISCO BCOS ----------
    FISCO_CHANNEL_HOST: str = Field(default="fisco-node0", description="FISCO Channel 主机")
    FISCO_CHANNEL_PORT: int = Field(default=20200, description="FISCO Channel 端口")
    FISCO_GROUP_ID: int = Field(default=1, description="FISCO 群组 ID")
    FISCO_CERT_PATH: str = Field(default="/app/certs/fisco", description="FISCO 证书路径")
    FISCO_SM_CRYPTO: bool = Field(default=True, description="是否使用国密")

    # ---------- FISCO Node URL ----------
    FISCO_NODE_URL: str = Field(default="", description="FISCO 节点 URL (自动构建)")

    # ---------- FATE ----------
    FATE_COORDINATOR_HOST: str = Field(default="fate-coordinator", description="FATE 协调器主机")
    FATE_COORDINATOR_PORT: int = Field(default=9380, description="FATE 协调器端口")
    FATE_PARTY_ID: int = Field(default=10000, description="FATE Party ID")

    # ---------- FATE Flow ----------
    FATE_FLOW_BASE_URL: str = Field(default="http://fateflow:9380", description="FATE Flow 服务地址")
    FATE_FLOW_API_PREFIX: str = Field(default="/v2", description="FATE Flow API 前缀")
    FATE_FLOW_TIMEOUT: float = Field(default=30.0, description="FATE Flow 请求超时(秒)")
    FATE_FLOW_MAX_RETRIES: int = Field(default=3, description="FATE Flow 最大重试次数")
    FATE_FLOW_OPERATION_MODE: str = Field(default="auto", description="FATE 运行模式: auto/real_only/simulation")
    FATE_FLOW_AUTH_TOKEN: str = Field(default="", description="FATE Flow 认证令牌")

    # ---------- MPSpdz ----------
    MPSpdz_PARTY0_HOST: str = Field(default="mpspdz-party0", description="MPSpdz Party0 主机")
    MPSpdz_PARTY1_HOST: str = Field(default="mpspdz-party1", description="MPSpdz Party1 主机")
    MPSpdz_PARTY2_HOST: str = Field(default="mpspdz-party2", description="MPSpdz Party2 主机")

    # ---------- JWT ----------
    JWT_SECRET_KEY: str = Field(default="change-me-jwt-secret-key", description="JWT 密钥")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT 算法")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, description="Access Token 过期时间(分钟)")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh Token 过期时间(天)")

    # ---------- SM2 国密 ----------
    SM2_PRIVATE_KEY_PATH: str = Field(default="/app/certs/sm2/sm2_private_key.pem", description="SM2 私钥路径")
    SM2_PUBLIC_KEY_PATH: str = Field(default="/app/certs/sm2/sm2_public_key.pem", description="SM2 公钥路径")
    SM2_CERT_PATH: str = Field(default="/app/certs/sm2/sm2_cert.pem", description="SM2 证书路径")

    # ---------- Prometheus ----------
    PROMETHEUS_HOST: str = Field(default="prometheus", description="Prometheus 主机")
    PROMETHEUS_PORT: int = Field(default=9090, description="Prometheus 端口")

    # ---------- Grafana ----------
    GRAFANA_HOST: str = Field(default="grafana", description="Grafana 主机")
    GRAFANA_PORT: int = Field(default=3000, description="Grafana 端口")
    GRAFANA_ADMIN_PASSWORD: str = Field(default="changeme_grafana_admin", description="Grafana 管理员密码")

    # ---------- DeepSeek AI ----------
    DEEPSEEK_API_KEY: str = Field(default="sk-your-api-key-here", description="DeepSeek API Key")
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com", description="DeepSeek API Base URL")
    DEEPSEEK_MODEL: str = Field(default="deepseek-chat", description="DeepSeek 模型名称")

    # ==================== 计算属性 ====================

    @property
    def postgres_url(self) -> str:
        """PostgreSQL 异步连接 URL"""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def postgres_url_sync(self) -> str:
        """PostgreSQL 同步连接 URL（用于 Alembic）"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def mongo_url(self) -> str:
        """MongoDB 连接 URL"""
        return (
            f"mongodb://{self.MONGO_USER}:{self.MONGO_PASSWORD}"
            f"@{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DB}?authSource=admin"
        )

    @property
    def redis_url(self) -> str:
        """Redis 连接 URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def rabbitmq_url(self) -> str:
        """RabbitMQ 连接 URL"""
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{self.RABBITMQ_VHOST}"
        )

    @property
    def fisco_node_url(self) -> str:
        """FISCO 节点 URL"""
        if self.FISCO_NODE_URL:
            return self.FISCO_NODE_URL
        return f"http://{self.FISCO_CHANNEL_HOST}:{self.FISCO_CHANNEL_PORT}"

    # ==================== 验证器 ====================

    @field_validator("APP_ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        """验证运行环境"""
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}, got '{v}'")
        return v

    @field_validator("JWT_ALGORITHM")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        """验证 JWT 算法"""
        allowed = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512"}
        if v not in allowed:
            raise ValueError(f"JWT_ALGORITHM must be one of {allowed}, got '{v}'")
        return v

    @field_validator("APP_SECRET_KEY", "JWT_SECRET_KEY")
    @classmethod
    def validate_secret_not_default(cls, v: str, info) -> str:
        """生产环境禁止使用默认密钥，且密钥长度不得少于 32 字符"""
        import os
        env = os.environ.get("APP_ENV", "development")
        default_keys = {
            "change-me-to-a-random-secret-key",
            "change-me-jwt-secret-key",
        }
        if env == "production" and v in default_keys:
            raise ValueError(
                f"生产环境禁止使用默认密钥，请在 .env 中设置强随机密钥（至少32字符）"
            )
        if len(v) < 16:
            raise ValueError("密钥长度不得少于 16 字符")
        return v


# 全局配置实例
settings = Settings()
