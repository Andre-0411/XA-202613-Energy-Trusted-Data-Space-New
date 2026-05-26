"""
MQTT 数据流 API
实时数据采集、设备管理、统计查询
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.schemas.common import ApiResponse
from app.schemas.mqtt_data import (
    DeviceInfo, DeviceDataRecord, CollectStatistics, AlarmRecord,
    SimulatorStatus, DataFetchRequest, DeviceDataStatistics, MqttStreamResponse,
)
from app.services.mqtt_collector import mqtt_collector
from app.services.mqtt_data_store import mqtt_data_store
from app.services.mqtt_simulator import mqtt_simulator

router = APIRouter()


@router.post("/start", response_model=ApiResponse)
async def start_collection():
    """启动 MQTT 数据采集"""
    result = await mqtt_collector.start_collection()
    return ApiResponse(data=result)


@router.post("/stop", response_model=ApiResponse)
async def stop_collection():
    """停止 MQTT 数据采集"""
    result = await mqtt_collector.stop_collection()
    return ApiResponse(data=result)


@router.get("/status", response_model=ApiResponse[SimulatorStatus])
async def get_status():
    """获取采集状态"""
    collector_status = await mqtt_collector.get_collection_status()
    simulator_status = await mqtt_simulator.get_status()

    return ApiResponse(data={
        "collector": collector_status,
        "simulator": simulator_status,
        "running": collector_status.get("running", False),
        "connected": simulator_status.get("connected", False),
        "mode": simulator_status.get("mode", "memory"),
        "device_count": collector_status.get("device_count", 0),
    })


@router.get("/devices", response_model=ApiResponse)
async def list_devices(
    enterprise: Optional[str] = Query(None, description="按企业过滤"),
    device_type: Optional[str] = Query(None, description="按设备类型过滤"),
):
    """获取设备列表"""
    devices = await mqtt_collector.get_devices_by_enterprise(enterprise)

    # 按设备类型过滤
    if device_type:
        devices = [d for d in devices if d.get("type") == device_type]

    return ApiResponse(data={
        "devices": devices,
        "total": len(devices),
        "enterprises": list(set(d.get("enterprise") for d in devices)),
    })


@router.get("/devices/{device_did}", response_model=ApiResponse)
async def get_device_info(device_did: str):
    """获取设备详情"""
    device = await mqtt_data_store.get_device_info(device_did)
    if not device:
        return ApiResponse(code=2001, message="设备未找到", data=None)

    latest_data = await mqtt_data_store.get_device_latest(device_did)

    return ApiResponse(data={
        "device": device,
        "latest_data": latest_data,
    })


@router.get("/devices/{device_did}/data", response_model=ApiResponse)
async def get_device_data(
    device_did: str,
    data_type: Optional[str] = Query(None, description="数据类型"),
    start_time: Optional[str] = Query(None, description="开始时间"),
    end_time: Optional[str] = Query(None, description="结束时间"),
    limit: int = Query(100, ge=1, le=1000, description="返回条数"),
):
    """获取设备历史数据"""
    data = await mqtt_collector.get_device_data(
        device_did=device_did,
        data_type=data_type,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )

    return ApiResponse(data={
        "device_did": device_did,
        "records": data,
        "total": len(data),
    })


@router.get("/devices/{device_did}/statistics", response_model=ApiResponse)
async def get_device_statistics(
    device_did: str,
    data_type: str = Query(..., description="数据类型"),
    start_time: Optional[str] = Query(None, description="开始时间"),
    end_time: Optional[str] = Query(None, description="结束时间"),
):
    """获取设备数据统计"""
    stats = await mqtt_data_store.get_data_statistics(
        device_did=device_did,
        data_type=data_type,
        start_time=start_time,
        end_time=end_time,
    )

    return ApiResponse(data=stats)


@router.get("/statistics", response_model=ApiResponse)
async def get_collection_statistics():
    """获取采集统计信息"""
    try:
        data_store_stats = await mqtt_data_store.get_statistics()
        enterprise_stats = await mqtt_collector.get_enterprise_statistics()
        return ApiResponse(data={
            "data_store": data_store_stats,
            "enterprises": enterprise_stats,
        })
    except Exception as e:
        logger.warning(f"MQTT statistics error: {e}")
        return ApiResponse(data={
            "data_store": {"device_count": 0, "online_count": 0, "total_records": 0, "total_alarms": 0},
            "enterprises": {},
        })


@router.get("/realtime", response_model=ApiResponse)
async def get_realtime_data(
    limit_per_device: int = Query(10, ge=1, le=100, description="每设备返回条数"),
):
    """获取实时数据快照"""
    data = await mqtt_collector.get_realtime_data(limit_per_device)
    return ApiResponse(data=data)


@router.get("/alarms", response_model=ApiResponse)
async def list_alarms(
    device_did: Optional[str] = Query(None, description="设备 DID"),
    alarm_type: Optional[str] = Query(None, description="告警类型"),
    limit: int = Query(100, ge=1, le=1000, description="返回条数"),
):
    """获取告警列表"""
    alarms = await mqtt_data_store.get_alarms(
        device_did=device_did,
        alarm_type=alarm_type,
        limit=limit,
    )

    return ApiResponse(data={
        "alarms": alarms,
        "total": len(alarms),
    })


@router.post("/alarms/inject", response_model=ApiResponse)
async def inject_alarm(
    device_did: str = Query(..., description="设备 DID"),
    alarm_type: str = Query(..., description="告警类型"),
    message: str = Query(..., description="告警消息"),
    severity: str = Query("warning", description="严重程度"),
):
    """手动注入告警"""
    result = await mqtt_simulator.inject_alarm(
        device_did=device_did,
        alarm_type=alarm_type,
        message=message,
        severity=severity,
    )

    return ApiResponse(data=result)


@router.get("/enterprises", response_model=ApiResponse)
async def list_enterprises():
    """获取企业列表及统计"""
    stats = await mqtt_collector.get_enterprise_statistics()

    enterprises = []
    for name, data in stats.items():
        enterprises.append({
            "name": name,
            "device_count": data.get("device_count", 0),
            "online_count": data.get("online_count", 0),
            "total_capacity_kw": data.get("total_capacity_kw", 0),
            "device_types": data.get("device_types", {}),
        })

    return ApiResponse(data={
        "enterprises": enterprises,
        "total": len(enterprises),
    })


@router.get("/overview", response_model=ApiResponse[MqttStreamResponse])
async def get_overview():
    """获取采集概览"""
    devices = await mqtt_data_store.get_devices()
    stats = await mqtt_data_store.get_statistics()
    alarms = await mqtt_data_store.get_alarms(limit=10)

    # 获取每个设备最新数据
    recent_data = []
    for device in devices[:5]:  # 只取前5个设备
        latest = await mqtt_data_store.get_device_latest(device["did"])
        if latest:
            for data_type, record in latest.items():
                recent_data.append(record)

    return ApiResponse(data={
        "devices": devices,
        "statistics": stats,
        "recent_data": recent_data,
        "alarms": alarms,
    })
