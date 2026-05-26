/**
 * MFA 多因素认证设置页面
 * 
 * 使用独立的 MfaSettings 组件，所有功能调用真实后端API
 */
import React from 'react';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import MfaSettings from '@/components/security/MfaSettings';

const MfaSetupPage: React.FC = () => {
  const breadcrumbs: BreadcrumbItem[] = [
    homeBreadcrumb,
    { label: '安全设置' },
    { label: 'MFA 设置' },
  ];

  return (
    <PageContainer>
      <PageHeader title="MFA 多因素认证设置" breadcrumbs={breadcrumbs} />
      <div className="max-w-3xl mx-auto">
        <MfaSettings />
      </div>
    </PageContainer>
  );
};

export default MfaSetupPage;
