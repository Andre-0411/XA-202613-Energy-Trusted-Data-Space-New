/**
 * 机构认证页面
 * 机构类型选择、认证材料上传、认证状态查看、审核进度追踪
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Select, Tag, Tooltip, Dialog, Textarea, MessagePlugin, Steps, Radio } from 'tdesign-react';
import {
  AddIcon, EditIcon, BrowseIcon, UploadIcon, CheckCircleIcon,
  TimeIcon, CloseCircleIcon, FileIcon, UserIcon, RefreshIcon,
  BuildingIcon,
} from 'tdesign-icons-react';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import { PageContainer, PageSection, StatGrid, StatCard } from '@/components/common';

/* ========== 类型定义 ========== */
interface CertificationMaterial {
  id: string;
  name: string;
  type: string;
  status: 'pending' | 'uploaded' | 'verified' | 'rejected';
  fileName?: string;
  uploadTime?: string;
  rejectReason?: string;
}

interface CertificationRecord {
  id: string;
  orgName: string;
  orgType: 'enterprise' | 'government' | 'institution';
  status: 'draft' | 'submitted' | 'reviewing' | 'approved' | 'rejected';
  submitTime?: string;
  reviewTime?: string;
  reviewer?: string;
  rejectReason?: string;
  materials: CertificationMaterial[];
  currentStep: number;
}

/* ========== 机构类型配置 ========== */
const ORG_TYPES = [
  { value: 'enterprise', label: '企业', icon: <BuildingIcon />, description: '工商注册的企业法人', color: '#2196f3' },
  { value: 'government', label: '政府机关', icon: <BuildingIcon />, description: '各级政府及下属机构', color: '#4caf50' },
  { value: 'institution', label: '事业单位', icon: <BuildingIcon />, description: '事业单位及社会组织', color: '#ff9800' },
];

/* ========== 认证材料配置 ========== */
const REQUIRED_MATERIALS: Record<string, { name: string; type: string; description: string }[]> = {
  enterprise: [
    { name: '营业执照', type: 'business_license', description: '有效期内的营业执照副本扫描件' },
    { name: '信用报告', type: 'credit_report', description: '近6个月的企业信用报告' },
    { name: '法人身份证', type: 'legal_id', description: '法定代表人身份证正反面' },
    { name: '授权委托书', type: 'authorization', description: '经办人授权委托书（非法人办理时）' },
  ],
  government: [
    { name: '组织机构代码证', type: 'org_code', description: '统一社会信用代码证书' },
    { name: '介绍信', type: 'introduction', description: '单位介绍信或工作证明' },
    { name: '经办人身份证', type: 'handler_id', description: '经办人身份证正反面' },
  ],
  institution: [
    { name: '事业单位法人证书', type: 'inst_license', description: '有效的事业单位法人证书' },
    { name: '信用报告', type: 'credit_report', description: '近6个月的信用报告' },
    { name: '法定代表人身份证', type: 'legal_id', description: '法定代表人身份证正反面' },
  ],
};

/* ========== 模拟认证记录 ========== */
const MOCK_CERTIFICATIONS: CertificationRecord[] = [
  {
    id: 'cert-001',
    orgName: '南方电网能源数据科技有限公司',
    orgType: 'enterprise',
    status: 'approved',
    submitTime: '2026-04-15 10:30:00',
    reviewTime: '2026-04-18 14:20:00',
    reviewer: '系统管理员',
    currentStep: 4,
    materials: [
      { id: 'm-1', name: '营业执照', type: 'business_license', status: 'verified', fileName: '营业执照.pdf', uploadTime: '2026-04-15 10:25:00' },
      { id: 'm-2', name: '信用报告', type: 'credit_report', status: 'verified', fileName: '信用报告.pdf', uploadTime: '2026-04-15 10:26:00' },
      { id: 'm-3', name: '法人身份证', type: 'legal_id', status: 'verified', fileName: '法人身份证.jpg', uploadTime: '2026-04-15 10:27:00' },
    ],
  },
  {
    id: 'cert-002',
    orgName: '广东能源交易中心',
    orgType: 'institution',
    status: 'reviewing',
    submitTime: '2026-05-20 09:00:00',
    currentStep: 2,
    materials: [
      { id: 'm-4', name: '事业单位法人证书', type: 'inst_license', status: 'uploaded', fileName: '法人证书.pdf', uploadTime: '2026-05-20 08:55:00' },
      { id: 'm-5', name: '信用报告', type: 'credit_report', status: 'uploaded', fileName: '信用报告.pdf', uploadTime: '2026-05-20 08:56:00' },
      { id: 'm-6', name: '法定代表人身份证', type: 'legal_id', status: 'pending' },
    ],
  },
  {
    id: 'cert-003',
    orgName: '深圳新能源科技集团',
    orgType: 'enterprise',
    status: 'rejected',
    submitTime: '2026-05-10 14:00:00',
    reviewTime: '2026-05-12 16:30:00',
    reviewer: '审核员A',
    rejectReason: '营业执照已过期，请上传最新版本',
    currentStep: 2,
    materials: [
      { id: 'm-7', name: '营业执照', type: 'business_license', status: 'rejected', fileName: '营业执照_旧.pdf', uploadTime: '2026-05-10 13:55:00', rejectReason: '营业执照已过期' },
      { id: 'm-8', name: '信用报告', type: 'credit_report', status: 'uploaded', fileName: '信用报告.pdf', uploadTime: '2026-05-10 13:56:00' },
      { id: 'm-9', name: '法人身份证', type: 'legal_id', status: 'uploaded', fileName: '法人身份证.jpg', uploadTime: '2026-05-10 13:57:00' },
    ],
  },
];

/* ========== 状态配置 ========== */
const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  draft: { label: '草稿', color: 'default', icon: <EditIcon /> },
  submitted: { label: '已提交', color: 'primary', icon: <UploadIcon /> },
  reviewing: { label: '审核中', color: 'warning', icon: <TimeIcon /> },
  approved: { label: '已通过', color: 'success', icon: <CheckCircleIcon /> },
  rejected: { label: '已拒绝', color: 'danger', icon: <CloseCircleIcon /> },
};

const MATERIAL_STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  pending: { label: '待上传', color: 'default' },
  uploaded: { label: '已上传', color: 'primary' },
  verified: { label: '已验证', color: 'success' },
  rejected: { label: '已拒绝', color: 'danger' },
};

/* ========== OrgCertificationPage 主组件 ========== */
const OrgCertificationPage: React.FC = () => {
  const [certifications] = useState<CertificationRecord[]>(MOCK_CERTIFICATIONS);
  const [createOpen, setCreateOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedCert, setSelectedCert] = useState<CertificationRecord | null>(null);

  // 新建认证表单
  const [orgName, setOrgName] = useState('');
  const [orgType, setOrgType] = useState<string>('enterprise');
  const [contactName, setContactName] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [uploadedMaterials, setUploadedMaterials] = useState<Record<string, File | null>>({});

  // 统计数据
  const stats = useMemo(() => ({
    total: certifications.length,
    approved: certifications.filter(c => c.status === 'approved').length,
    reviewing: certifications.filter(c => c.status === 'reviewing').length,
    rejected: certifications.filter(c => c.status === 'rejected').length,
  }), [certifications]);

  // 面包屑
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '门户管理' }, { label: '机构认证' }],
    [],
  );

  // 操作按钮
  const headerActions: PageAction[] = useMemo(
    () => [
      { label: '新建认证申请', icon: <AddIcon />, onClick: () => setCreateOpen(true), variant: 'contained', color: 'primary' },
    ],
    [],
  );

  // 查看详情
  const handleViewDetail = useCallback((cert: CertificationRecord) => {
    setSelectedCert(cert);
    setDetailOpen(true);
  }, []);

  // 文件上传 - 使用真实文件选择
  const handleFileUpload = useCallback((materialType: string) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.doc,.docx,.jpg,.jpeg,.png';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        setUploadedMaterials(prev => ({ ...prev, [materialType]: file }));
        MessagePlugin.success(`${materialType} 已选择: ${file.name}`);
      }
    };
    input.click();
  }, []);

  // 提交认证申请
  const handleSubmit = useCallback(() => {
    if (!orgName.trim()) {
      MessagePlugin.warning('请输入机构名称');
      return;
    }
    MessagePlugin.success('认证申请已提交，请等待审核');
    setCreateOpen(false);
    setOrgName('');
    setContactName('');
    setContactPhone('');
    setContactEmail('');
    setUploadedMaterials({});
  }, [orgName]);

  // 渲染审核步骤
  const renderSteps = (cert: CertificationRecord) => {
    const steps = [
      { title: '填写信息', content: '填写机构基本信息' },
      { title: '上传材料', content: '上传认证所需材料' },
      { title: '提交审核', content: '等待管理员审核' },
      { title: '审核完成', content: '认证完成' },
    ];

    return (
      <Steps current={cert.currentStep} style={{ marginBottom: 24 }}>
        {steps.map((step, index) => (
          <Steps.StepItem key={index} title={step.title} content={step.content} />
        ))}
      </Steps>
    );
  };

  return (
    <PageContainer>
      <PageHeader
        title="机构认证"
        subtitle="提交机构认证申请，获取数据空间访问权限"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => MessagePlugin.info('已刷新'), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="总申请数" value={stats.total} icon={<FileIcon />} gradient="blue" unit="" />
        <StatCard title="已通过" value={stats.approved} icon={<CheckCircleIcon />} gradient="green" unit="" />
        <StatCard title="审核中" value={stats.reviewing} icon={<TimeIcon />} gradient="orange" unit="" />
        <StatCard title="已拒绝" value={stats.rejected} icon={<CloseCircleIcon />} gradient="red" unit="" />
      </StatGrid>

      {/* 认证申请列表 */}
      <PageSection title="认证申请记录" titleIcon={<FileIcon />}>
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 sticky top-0 z-10">
              <tr>
                <th className="px-4 py-3 text-left font-bold">机构名称</th>
                <th className="px-4 py-3 text-left font-bold">机构类型</th>
                <th className="px-4 py-3 text-left font-bold">状态</th>
                <th className="px-4 py-3 text-left font-bold">提交时间</th>
                <th className="px-4 py-3 text-left font-bold">审核时间</th>
                <th className="px-4 py-3 text-center font-bold">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {certifications.map(cert => {
                const statusConf = STATUS_CONFIG[cert.status];
                const typeConf = ORG_TYPES.find(t => t.value === cert.orgType);
                return (
                  <tr key={cert.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3">
                      <span className="font-semibold text-gray-800">{cert.orgName}</span>
                    </td>
                    <td className="px-4 py-3">
                      <Tag variant="outline" size="small">{typeConf?.label || cert.orgType}</Tag>
                    </td>
                    <td className="px-4 py-3">
                      <Tag theme={statusConf.color as any} variant="light" size="small" icon={statusConf.icon}>
                        {statusConf.label}
                      </Tag>
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {cert.submitTime ? new Date(cert.submitTime).toLocaleString('zh-CN') : '-'}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {cert.reviewTime ? new Date(cert.reviewTime).toLocaleString('zh-CN') : '-'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <Tooltip content="查看详情">
                        <Button variant="text" theme="primary" icon={<BrowseIcon />} onClick={() => handleViewDetail(cert)} />
                      </Tooltip>
                      {cert.status === 'rejected' && (
                        <Tooltip content="重新提交">
                          <Button variant="text" theme="warning" icon={<RefreshIcon />} onClick={() => MessagePlugin.info('重新提交功能开发中')} />
                        </Tooltip>
                      )}
                    </td>
                  </tr>
                );
              })}
              {certifications.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-gray-400">暂无认证记录</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </PageSection>

      {/* 新建认证申请弹窗 */}
      <Dialog
        header="新建机构认证申请"
        visible={createOpen}
        onClose={() => setCreateOpen(false)}
        width={700}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setCreateOpen(false)}>取消</Button>
            <Button theme="primary" onClick={handleSubmit}>提交申请</Button>
          </div>
        }
      >
        <div className="flex flex-col gap-6 py-2">
          {/* 机构类型选择 */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-3 block">机构类型 *</label>
            <div className="grid grid-cols-3 gap-3">
              {ORG_TYPES.map(type => (
                <button
                  key={type.value}
                  className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${
                    orgType === type.value
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                  }`}
                  onClick={() => setOrgType(type.value)}
                >
                  <div className="text-2xl" style={{ color: type.color }}>{type.icon}</div>
                  <span className="font-medium text-sm">{type.label}</span>
                  <span className="text-xs text-gray-500 text-center">{type.description}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 基本信息 */}
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="text-sm text-gray-600 mb-1 block">机构名称 *</label>
              <Input value={orgName} onChange={setOrgName} placeholder="请输入机构全称" />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">联系人</label>
              <Input value={contactName} onChange={setContactName} placeholder="请输入联系人姓名" />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">联系电话</label>
              <Input value={contactPhone} onChange={setContactPhone} placeholder="请输入联系电话" />
            </div>
            <div className="col-span-2">
              <label className="text-sm text-gray-600 mb-1 block">联系邮箱</label>
              <Input value={contactEmail} onChange={setContactEmail} placeholder="请输入联系邮箱" />
            </div>
          </div>

          {/* 认证材料上传 */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-3 block">认证材料</label>
            <div className="space-y-3">
              {(REQUIRED_MATERIALS[orgType] || []).map(material => {
                const uploaded = uploadedMaterials[material.type];
                return (
                  <div key={material.type} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="flex items-center gap-3">
                      <FileIcon className="text-gray-400" />
                      <div>
                        <div className="text-sm font-medium text-gray-700">{material.name}</div>
                        <div className="text-xs text-gray-500">{material.description}</div>
                      </div>
                    </div>
                    {uploaded ? (
                      <div className="flex items-center gap-2">
                        <Tag theme="success" variant="light" size="small" icon={<CheckCircleIcon />}>已选择</Tag>
                        <Button variant="text" size="small" onClick={() => handleFileUpload(material.type)}>重新上传</Button>
                      </div>
                    ) : (
                      <Button variant="outline" size="small" icon={<UploadIcon />} onClick={() => handleFileUpload(material.type)}>
                        上传
                      </Button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </Dialog>

      {/* 认证详情弹窗 */}
      <Dialog
        header="认证申请详情"
        visible={detailOpen}
        onClose={() => setDetailOpen(false)}
        width={700}
        footer={
          <div className="flex justify-end">
            <Button onClick={() => setDetailOpen(false)}>关闭</Button>
          </div>
        }
      >
        {selectedCert && (
          <div className="flex flex-col gap-6 py-2">
            {/* 审核进度 */}
            {renderSteps(selectedCert)}

            {/* 基本信息 */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-xs text-gray-500">机构名称</span>
                <div className="text-sm font-medium mt-1">{selectedCert.orgName}</div>
              </div>
              <div>
                <span className="text-xs text-gray-500">机构类型</span>
                <div className="mt-1">
                  <Tag variant="outline" size="small">
                    {ORG_TYPES.find(t => t.value === selectedCert.orgType)?.label}
                  </Tag>
                </div>
              </div>
              <div>
                <span className="text-xs text-gray-500">状态</span>
                <div className="mt-1">
                  <Tag theme={STATUS_CONFIG[selectedCert.status].color as any} variant="light" size="small">
                    {STATUS_CONFIG[selectedCert.status].label}
                  </Tag>
                </div>
              </div>
              <div>
                <span className="text-xs text-gray-500">审核人</span>
                <div className="text-sm mt-1">{selectedCert.reviewer || '-'}</div>
              </div>
            </div>

            {/* 拒绝原因 */}
            {selectedCert.status === 'rejected' && selectedCert.rejectReason && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <CloseCircleIcon className="text-red-500" />
                  <span className="text-sm font-medium text-red-700">拒绝原因</span>
                </div>
                <p className="text-sm text-red-600 m-0">{selectedCert.rejectReason}</p>
              </div>
            )}

            {/* 认证材料 */}
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-3">认证材料</h4>
              <div className="space-y-2">
                {selectedCert.materials.map(mat => (
                  <div key={mat.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <FileIcon className="text-gray-400" />
                      <div>
                        <div className="text-sm font-medium">{mat.name}</div>
                        {mat.fileName && <div className="text-xs text-gray-500">{mat.fileName}</div>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Tag
                        theme={MATERIAL_STATUS_CONFIG[mat.status].color as any}
                        variant="light"
                        size="small"
                      >
                        {MATERIAL_STATUS_CONFIG[mat.status].label}
                      </Tag>
                      {mat.rejectReason && (
                        <Tooltip content={mat.rejectReason}>
                          <span className="text-xs text-red-500 cursor-help">原因</span>
                        </Tooltip>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 时间线 */}
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-3">操作记录</h4>
              <div className="space-y-3 ml-3 border-l-2 border-gray-200 pl-4">
                {selectedCert.submitTime && (
                  <div className="relative">
                    <div className="absolute -left-[21px] w-3 h-3 rounded-full bg-blue-500 border-2 border-white" />
                    <div className="text-sm"><span className="font-medium">提交申请</span></div>
                    <div className="text-xs text-gray-500">{new Date(selectedCert.submitTime).toLocaleString('zh-CN')}</div>
                  </div>
                )}
                {selectedCert.reviewTime && (
                  <div className="relative">
                    <div className={`absolute -left-[21px] w-3 h-3 rounded-full border-2 border-white ${
                      selectedCert.status === 'approved' ? 'bg-green-500' : 'bg-red-500'
                    }`} />
                    <div className="text-sm">
                      <span className="font-medium">
                        {selectedCert.status === 'approved' ? '审核通过' : '审核拒绝'}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500">{new Date(selectedCert.reviewTime).toLocaleString('zh-CN')}</div>
                    {selectedCert.reviewer && <div className="text-xs text-gray-500">审核人：{selectedCert.reviewer}</div>}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </Dialog>
    </PageContainer>
  );
};

export default OrgCertificationPage;
