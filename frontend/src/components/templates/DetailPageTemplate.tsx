/**
 * DetailPageTemplate 标准详情页模板
 * 组合 PageHeader + 信息网格 + Tab 内容，
 * 提供统一的详情页布局。
 */
import React, { useState } from 'react';
import PageHeader, { BreadcrumbItem, PageAction } from '../PageHeader';

export interface DetailPageTemplateProps {
  /** 页面标题 */
  title: string;
  /** 页面副标题 */
  subtitle?: string;
  /** 面包屑导航 */
  breadcrumbs: BreadcrumbItem[];
  /** 页面操作按钮 */
  actions?: PageAction[];

  /** 详情信息列表 */
  infoItems: Array<{
    label: string;
    value: React.ReactNode;
    icon?: React.ReactNode;
  }>;

  /** Tab 页签列表 */
  tabs?: Array<{
    key: string;
    label: string;
    content: React.ReactNode;
  }>;

  /** 自定义内容（放在信息区下方、Tab 上方） */
  children?: React.ReactNode;
}

/**
 * DetailPageTemplate 组件
 * 标准详情页布局：页头 → 信息网格 → [自定义内容] → Tab 内容
 */
const DetailPageTemplate: React.FC<DetailPageTemplateProps> = ({
  title,
  subtitle,
  breadcrumbs,
  actions,
  infoItems,
  tabs,
  children,
}) => {
  const [activeTab, setActiveTab] = useState<string>(
    tabs && tabs.length > 0 ? tabs[0].key : '',
  );

  return (
    <div>
      {/* 页头 */}
      <PageHeader
        title={title}
        subtitle={subtitle}
        breadcrumbs={breadcrumbs}
        actions={actions}
      />

      {/* 详情信息网格 */}
      {infoItems.length > 0 && (
        <div
          className="rounded-xl bg-white p-5 sm:p-6 mb-6"
          style={{ border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {infoItems.map((item, idx) => (
              <div key={`info-${idx}`} className="flex items-start gap-3">
                {item.icon && (
                  <div
                    className="flex items-center justify-center rounded-lg shrink-0"
                    style={{
                      width: 40,
                      height: 40,
                      background: '#f0f5ff',
                      color: '#1677ff',
                    }}
                  >
                    {item.icon}
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <span className="text-xs text-gray-500 block mb-1">
                    {item.label}
                  </span>
                  <span className="text-sm font-medium text-gray-900 block truncate">
                    {item.value ?? '-'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 自定义内容 */}
      {children}

      {/* Tab 页签 */}
      {tabs && tabs.length > 0 && (
        <div
          className="rounded-xl bg-white overflow-hidden"
          style={{ border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}
        >
          {/* Tab 头 */}
          <div
            className="flex items-center border-b border-gray-200 px-5"
            style={{ gap: 0 }}
          >
            {tabs.map((tab) => {
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  type="button"
                  className={`
                    relative px-4 py-3 text-sm font-medium bg-transparent border-none cursor-pointer
                    transition-colors duration-200
                    ${isActive ? 'text-blue-600' : 'text-gray-500 hover:text-gray-700'}
                  `}
                  onClick={() => setActiveTab(tab.key)}
                >
                  {tab.label}
                  {/* 底部激活指示条 */}
                  {isActive && (
                    <span
                      className="absolute left-0 right-0 bottom-0"
                      style={{
                        height: 2,
                        background: '#1677ff',
                        borderRadius: 1,
                      }}
                    />
                  )}
                </button>
              );
            })}
          </div>

          {/* Tab 内容 */}
          <div className="p-5 sm:p-6">
            {tabs.map((tab) => (
              <div
                key={tab.key}
                style={{ display: activeTab === tab.key ? 'block' : 'none' }}
              >
                {tab.content}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DetailPageTemplate;
