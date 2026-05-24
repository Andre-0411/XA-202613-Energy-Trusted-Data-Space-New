/**
 * MetadataDetails - 元数据详情对话框组件
 * 版本历史、血缘关系、分类规则对话框
 */
import React from 'react';
import { Button, Dialog, Tag } from 'tdesign-react';
import {
  FilterIcon,
} from 'tdesign-icons-react';
import type { MetadataRecord } from '@/types/api';

interface MetadataDetailsProps {
  // 版本历史
  versionsOpen: boolean;
  versionsData: MetadataRecord[];
  versionsLoading: boolean;
  onVersionsClose: () => void;

  // 血缘关系
  lineageOpen: boolean;
  lineageData: Record<string, unknown> | null;
  lineageLoading: boolean;
  onLineageClose: () => void;

  // 分类规则
  rulesOpen: boolean;
  classificationRules: any[];
  onRulesClose: () => void;
}

/** MetadataDetails 组件 */
const MetadataDetails: React.FC<MetadataDetailsProps> = ({
  versionsOpen,
  versionsData,
  versionsLoading,
  onVersionsClose,
  lineageOpen,
  lineageData,
  lineageLoading,
  onLineageClose,
  rulesOpen,
  classificationRules,
  onRulesClose,
}) => {
  return (
    <>
      {/* 版本历史弹窗 */}
      <Dialog
        header="版本历史"
        visible={versionsOpen}
        onClose={onVersionsClose}
        footer={false}
        destroyOnClose
      >
        <div className="py-2">
          {versionsLoading ? (
            <div className="text-center text-gray-400 py-8">加载中...</div>
          ) : versionsData.length === 0 ? (
            <div className="text-center text-gray-400 py-8">暂无版本记录</div>
          ) : (
            <div className="flex flex-col gap-2">
              {versionsData.map((ver, idx) => (
                <div key={ver.id} className="rounded-lg border border-gray-200 p-3">
                  <div className="flex justify-between items-center">
                    <span className="font-medium text-sm">
                      版本 {versionsData.length - idx}: {ver.schema_version}
                    </span>
                    <span className="text-xs text-gray-400">
                      {new Date(ver.created_at).toLocaleString('zh-CN')}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500 mt-1 block">
                    标准: {ver.standard} | 字段数: {ver.fields?.length ?? 0}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="flex justify-end pt-3 border-t border-gray-100">
          <Button onClick={onVersionsClose}>关闭</Button>
        </div>
      </Dialog>

      {/* 血缘关系弹窗 */}
      <Dialog
        header="血缘关系"
        visible={lineageOpen}
        onClose={onLineageClose}
        footer={false}
        destroyOnClose
      >
        <div className="py-2">
          {lineageLoading ? (
            <div className="text-center text-gray-400 py-8">加载中...</div>
          ) : lineageData ? (
            <div className="rounded-lg border border-gray-200 p-4">
              <pre className="text-xs text-gray-600 whitespace-pre-wrap break-words m-0">
                {JSON.stringify(lineageData, null, 2)}
              </pre>
            </div>
          ) : (
            <div className="text-center text-gray-400 py-8">暂无血缘关系数据</div>
          )}
        </div>
        <div className="flex justify-end pt-3 border-t border-gray-100">
          <Button onClick={onLineageClose}>关闭</Button>
        </div>
      </Dialog>

      {/* 分类规则弹窗 */}
      <Dialog
        header="数据分类规则"
        visible={rulesOpen}
        onClose={onRulesClose}
        footer={false}
        destroyOnClose
      >
        <div className="py-2">
          <p className="text-sm text-gray-600 mb-4">
            系统内置的自动分类规则，基于关键词匹配和字段分析进行数据分类分级。
          </p>
          {Array.isArray(classificationRules) && classificationRules.length > 0 ? (
            <div className="overflow-auto max-h-96">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0 z-10">
                  <tr>
                    <th className="px-3 py-2 text-left font-bold">规则ID</th>
                    <th className="px-3 py-2 text-left font-bold">规则名称</th>
                    <th className="px-3 py-2 text-left font-bold">分类</th>
                    <th className="px-3 py-2 text-left font-bold">敏感级别</th>
                    <th className="px-3 py-2 text-left font-bold">关键词</th>
                    <th className="px-3 py-2 text-left font-bold">优先级</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {(classificationRules as any[]).map((rule) => (
                    <tr key={rule.rule_id} className="hover:bg-gray-50">
                      <td className="px-3 py-2">
                        <Tag variant="outline" size="small">{rule.rule_id}</Tag>
                      </td>
                      <td className="px-3 py-2">{rule.name}</td>
                      <td className="px-3 py-2">{rule.category}</td>
                      <td className="px-3 py-2">
                        <Tag
                          size="small"
                          theme={rule.sensitivity_level <= 2 ? 'danger' : rule.sensitivity_level === 3 ? 'warning' : 'success'}
                        >
                          {rule.sensitivity_level}级
                        </Tag>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1">
                          {rule.keywords?.slice(0, 3).map((kw: string) => (
                            <Tag key={kw} variant="outline" size="small">{kw}</Tag>
                          ))}
                          {(rule.keywords?.length || 0) > 3 && (
                            <Tag size="small">+{rule.keywords.length - 3}</Tag>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2">{rule.priority}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center text-gray-400 py-8">
              <FilterIcon size="32px" style={{ color: '#d1d5db' }} />
              <p className="mt-2">暂无分类规则数据</p>
            </div>
          )}
        </div>
        <div className="flex justify-end pt-3 border-t border-gray-100">
          <Button onClick={onRulesClose}>关闭</Button>
        </div>
      </Dialog>
    </>
  );
};

export default MetadataDetails;
