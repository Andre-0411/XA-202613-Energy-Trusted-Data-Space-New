/**
 * 安全设置页面
 * 
 * 包含：
 * - MFA 多因素认证设置
 * - 密码修改
 * - 登录设备管理
 * - 安全日志
 */
import React, { useState, useEffect } from 'react';
import { Card, Tabs, MessagePlugin, Loading } from 'tdesign-react';
import { LockOnIcon, DesktopIcon, TimeIcon } from 'tdesign-icons-react';

import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import MfaSettings from '@/components/security/MfaSettings';
import request from '@/api/request';

const SecuritySettingsPage: React.FC = () => {
  const breadcrumbs: BreadcrumbItem[] = [
    homeBreadcrumb,
    { label: '安全中心' },
    { label: '安全设置' },
  ];

  const [activeTab, setActiveTab] = useState('mfa');

  return (
    <PageContainer>
      <PageHeader title="安全设置" breadcrumbs={breadcrumbs} />
      
      <Tabs
        value={activeTab}
        onChange={setActiveTab}
        theme="card"
        className="bg-white rounded-lg"
      >
        <Tabs.TabPanel value="mfa" label={
          <div className="flex items-center gap-2">
            <LockOnIcon />
            <span>多因素认证</span>
          </div>
        }>
          <div className="p-6">
            <MfaSettings />
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="devices" label={
          <div className="flex items-center gap-2">
            <DesktopIcon />
            <span>登录设备</span>
          </div>
        }>
          <div className="p-6">
            <LoginDevicesSection />
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="logs" label={
          <div className="flex items-center gap-2">
            <TimeIcon />
            <span>安全日志</span>
          </div>
        }>
          <div className="p-6">
            <SecurityLogsSection />
          </div>
        </Tabs.TabPanel>
      </Tabs>
    </PageContainer>
  );
};

// 登录设备管理组件
const LoginDevicesSection: React.FC = () => {
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    try {
      const res: any = await request.get('/auth/devices');
      const data = res?.data || res;
      setDevices(data?.items || data || []);
    } catch (error) {
      // 如果API不存在，显示空状态
      setDevices([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeDevice = async (deviceId: string) => {
    try {
      await request.delete(`/auth/devices/${deviceId}`);
      MessagePlugin.success('设备已移除');
      fetchDevices();
    } catch (error: any) {
      MessagePlugin.error('移除失败：' + (error?.message || '请重试'));
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loading />
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">已登录设备</h3>
      {devices.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <DesktopIcon size="48px" className="mx-auto mb-4 text-gray-300" />
          <p>暂无已登录设备记录</p>
          <p className="text-sm mt-1">设备管理功能需要后端支持</p>
        </div>
      ) : (
        <div className="space-y-3">
          {devices.map((device: any) => (
            <Card key={device.id} className="flex items-center justify-between">
              <div>
                <p className="font-medium">{device.name || '未知设备'}</p>
                <p className="text-sm text-gray-500">
                  {device.os} · {device.browser} · {device.ip}
                </p>
                <p className="text-xs text-gray-400">
                  最后活跃：{new Date(device.last_active).toLocaleString('zh-CN')}
                </p>
              </div>
              <button
                className="text-red-500 hover:text-red-700 text-sm"
                onClick={() => handleRevokeDevice(device.id)}
              >
                移除
              </button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

// 安全日志组件
const SecurityLogsSection: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  useEffect(() => {
    fetchLogs();
  }, [page]);

  const fetchLogs = async () => {
    try {
      const res: any = await request.get('/audit-logs/', {
        params: {
          page,
          page_size: 20,
          category: 'security',
        }
      });
      const data = res?.data || res;
      setLogs(data?.items || data || []);
    } catch (error) {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  const getEventLabel = (event: string) => {
    const labels: Record<string, string> = {
      'login_success': '登录成功',
      'login_failed': '登录失败',
      'logout': '退出登录',
      'password_change': '修改密码',
      'mfa_enable': '启用MFA',
      'mfa_disable': '禁用MFA',
      'mfa_verify': 'MFA验证',
    };
    return labels[event] || event;
  };

  const getEventColor = (event: string) => {
    if (event.includes('success') || event.includes('enable')) return 'text-green-600';
    if (event.includes('failed') || event.includes('disable')) return 'text-red-600';
    return 'text-gray-600';
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loading />
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">安全事件日志</h3>
      {logs.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <TimeIcon size="48px" className="mx-auto mb-4 text-gray-300" />
          <p>暂无安全事件记录</p>
        </div>
      ) : (
        <div className="space-y-2">
          {logs.map((log: any, index: number) => (
            <div key={index} className="flex items-center justify-between py-3 border-b last:border-0">
              <div>
                <span className={`font-medium ${getEventColor(log.event_type)}`}>
                  {getEventLabel(log.event_type)}
                </span>
                <span className="text-gray-500 ml-2">{log.details || ''}</span>
              </div>
              <div className="text-sm text-gray-400">
                {new Date(log.created_at).toLocaleString('zh-CN')}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SecuritySettingsPage;
