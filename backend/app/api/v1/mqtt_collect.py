"""
MQTT 数据采集 API 端点
提供模拟器控制、设备查询、数据查询和统计功能
"""
from typing import Optional

from fastapi import APIRouter, Query

from app.schemas.common import ApiResponse
from app.services.mqtt_simulator import mqtt_simulator
from app.services.mqtt_data_store import mqtt_data_store

router = APIRouter()


@router.post("/simulator/start", response_model=ApiResponse)
async def start_simulator():
    """启动模拟器"""
    result = await mqtt_simulator.start()
    return ApiResponse(data=result)


@router.post("/simulator/stop", response_model=ApiResponse)
async def stop_simulator():
    """停止模拟器"""
    result = await mqtt_simulator.stop()
    return ApiResponse(data=result)


@router.get("/simulator/status", response_model=ApiResponse)
async def get_simulator_status():
    """获取模拟器状态"""
    status = await mqtt_simulator.get_status()
    return ApiResponse(data=status)


@router.get("/devices", response_model=ApiResponse)
async def list_devices():
    """获取已注册设备列表"""
    devices = await mqtt_data_store.get_devices()
    return ApiResponse(data=devices)


@router.get("/devices/{did}/latest", response_model=ApiResponse)
async def get_device_latest(did: str):
    """获取设备最新数据"""
    # 验证设备存在
    device_info = await mqtt_data_store.get_device_info(did)
    if not device_info:
        return ApiResponse(code=404, message=f"设备不存在: {did}", data=None)

    latest = await mqtt_data_store.get_device_latest(did)
    return ApiResponse(data={
        "device": device_info,
        "latest_data": latest,
    })


@router.get("/devices/{did}/history", response_model=ApiResponse)
async def get_device_history(
    did: str,
    data_type: Optional[str] = Query(None, description="数据类型"),
    start_time: Optional[str] = Query(None, description="开始时间(ISO格式)"),
    end_time: Optional[str] = Query(None, description="结束时间(ISO格式)"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
):
    """获取设备历史数据"""
    # 验证设备存在
    device_info = await mqtt_data_store.get_device_info(did)
    if not device_info:
        return ApiResponse(code=404, message=f"设备不存在: {did}", data=None)

    history = await mqtt_data_store.get_device_history(
        did, data_type, start_time, end_time, limit
    )
    return ApiResponse(data={
        "device": device_info,
        "history": history,
        "total": len(history),
    })


@router.get("/statistics", response_model=ApiResponse)
async def get_statistics():
    """获取采集统计信息"""
    stats = await mqtt_data_store.get_statistics()
    return ApiResponse(data=stats)


@router.post("/alarm/inject", response_model=ApiResponse)
async def inject_alarm(
    device_did: str = Query(..., description="设备DID"),
    alarm_type: str = Query(..., description="告警类型"),
    message: str = Query(..., description="告警消息"),
    severity: str = Query("warning", description="告警级别: info/warning/critical"),
):
    """手动注入告警"""
    result = await mqtt_simulator.inject_alarm(device_did, alarm_type, message, severity)
    if result["success"]:
        return ApiResponse(message=result["message"])
    else:
        return ApiResponse(code=400, message=result["message"], data=None)


@router.get("/alarms", response_model=ApiResponse)
async def list_alarms(
    device_did: Optional[str] = Query(None, description="设备DID"),
    alarm_type: Optional[str] = Query(None, description="告警类型"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
):
    """获取告警列表"""
    alarms = await mqtt_data_store.get_alarms(device_did, alarm_type, limit)
    return ApiResponse(data=alarms)


@router.get("/devices/{did}/statistics", response_model=ApiResponse)
async def get_device_statistics(
    did: str,
    data_type: str = Query(..., description="数据类型"),
    start_time: Optional[str] = Query(None, description="开始时间"),
    end_time: Optional[str] = Query(None, description="结束时间"),
):
    """获取设备数据统计"""
    # 验证设备存在
    device_info = await mqtt_data_store.get_device_info(did)
    if not device_info:
        return ApiResponse(code=404, message=f"设备不存在: {did}", data=None)

    stats = await mqtt_data_store.get_data_statistics(did, data_type, start_time, end_time)
    return ApiResponse(data={
        "device": device_info,
        "data_type": data_type,
        "statistics": stats,
    })