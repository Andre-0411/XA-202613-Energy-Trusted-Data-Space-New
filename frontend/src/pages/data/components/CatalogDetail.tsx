/**
 * CatalogDetail - 数据目录详情对话框组件
 * 申请访问、评分反馈、数据预览、自动分类、完整性验证对话框
 */
import React from 'react';
import { Button, Dialog, Textarea, Tag } from 'tdesign-react';
import {
  CheckCircleIcon, StarIcon, FolderOpenIcon, ShieldErrorFilledIcon,
} from 'tdesign-icons-react';
import type { DataCatalogItem } from '@/types/api';

interface CatalogDetailProps {
  // 申请访问
  applyTarget: DataCatalogItem | null;
  applyReason: string;
  onApplyReasonChange: (val: string) => void;
  onApplySubmit: () => void;
  onApplyClose: () => void;
  applyPending: boolean;

  // 评分反馈
  feedbackTarget: DataCatalogItem | null;
  feedbackRating: number;
  feedbackComment: string;
  onFeedbackRatingChange: (rating: number) => void;
  onFeedbackCommentChange: (val: string) => void;
  onFeedbackSubmit: () => void;
  onFeedbackClose: () => void;
  feedbackPending: boolean;

  // 数据预览
  previewData: Record<string, unknown> | null;
  onPreviewClose: () => void;

  // 自动分类
  classifyDialogOpen: boolean;
  classifyResult: any;
  onClassifyClose: () => void;

  // 完整性验证
  verifyDialogOpen: boolean;
  verifyResult: any;
  onVerifyClose: () => void;
}

/** CatalogDetail 组件 */
const CatalogDetail: React.FC<CatalogDetailProps> = ({
  applyTarget,
  applyReason,
  onApplyReasonChange,
  onApplySubmit,
  onApplyClose,
  applyPending,
  feedbackTarget,
  feedbackRating,
  feedbackComment,
  onFeedbackRatingChange,
  onFeedbackCommentChange,
  onFeedbackSubmit,
  onFeedbackClose,
  feedbackPending,
  previewData,
  onPreviewClose,
  classifyDialogOpen,
  classifyResult,
  onClassifyClose,
  verifyDialogOpen,
  verifyResult,
  onVerifyClose,
}) => {
  return (
    <>
      {/* 申请访问弹窗 */}
      <Dialog
        header={`申请访问 — ${applyTarget?.name ?? ''}`}
        visible={!!applyTarget}
        onClose={onApplyClose}
        width={520}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={onApplyClose}>取消</Button>
            <Button
              theme="primary"
              disabled={!applyReason.trim() || applyPending}
              loading={applyPending}
              onClick={onApplySubmit}
            >
              提交申请
            </Button>
          </div>
        }
        destroyOnClose
      >
        <div className="flex flex-col gap-4">
          <p className="text-sm text-gray-500">请填写申请理由，审批通过后方可访问该数据。</p>
          <Textarea
            value={applyReason}
            onChange={(val) => onApplyReasonChange(String(val))}
            placeholder="请输入申请理由"
            rows={3}
          />
        </div>
      </Dialog>

      {/* 评分反馈弹窗 */}
      <Dialog
        header={`评分反馈 — ${feedbackTarget?.name ?? ''}`}
        visible={!!feedbackTarget}
        onClose={onFeedbackClose}
        width={520}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={onFeedbackClose}>取消</Button>
            <Button
              theme="primary"
              disabled={feedbackRating === 0 || feedbackPending}
              loading={feedbackPending}
              onClick={onFeedbackSubmit}
            >
              提交反馈
            </Button>
          </div>
        }
        destroyOnClose
      >
        <div className="flex flex-col gap-4">
          <div>
            <p className="text-sm text-gray-600 mb-2">评分</p>
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map((star) => (
                <span
                  key={star}
                  className={`cursor-pointer text-2xl transition-colors ${star <= feedbackRating ? 'text-amber-400' : 'text-gray-300'}`}
                  onClick={() => onFeedbackRatingChange(star)}
                >
                  ★
                </span>
              ))}
            </div>
          </div>
          <div>
            <p className="text-sm text-gray-600 mb-1">评价内容</p>
            <Textarea
              value={feedbackComment}
              onChange={(val) => onFeedbackCommentChange(String(val))}
              placeholder="请输入评价内容"
              rows={3}
            />
          </div>
        </div>
      </Dialog>

      {/* 数据预览弹窗 */}
      <Dialog
        header="数据预览"
        visible={!!previewData}
        onClose={onPreviewClose}
        width={680}
        footer={
          <div className="flex justify-end">
            <Button onClick={onPreviewClose}>关闭</Button>
          </div>
        }
        destroyOnClose
      >
        <div className="rounded-lg bg-gray-50 p-4">
          <pre className="text-xs font-mono whitespace-pre-wrap break-all">
            {previewData ? JSON.stringify(previewData, null, 2) : ''}
          </pre>
        </div>
      </Dialog>

      {/* 自动分类分级弹窗 */}
      <Dialog
        header="自动分类分级"
        visible={classifyDialogOpen}
        onClose={onClassifyClose}
        width={520}
        footer={
          <div className="flex justify-end">
            <Button onClick={onClassifyClose}>关闭</Button>
          </div>
        }
        destroyOnClose
      >
        <div className="flex flex-col gap-4">
          <p className="text-sm text-gray-500">
            输入数据集信息，系统将自动识别分类和安全级别（SM3哈希指纹验证）。
          </p>
          {classifyResult ? (
            <div className="border border-gray-200 rounded-lg p-4">
              <h4 className="text-sm font-bold mb-2">分类结果</h4>
              <div className="flex gap-2 mb-2">
                <Tag variant="light" theme="primary">分类: {classifyResult.category}</Tag>
                <Tag variant="light" theme="warning">级别: {classifyResult.classification_level} - {classifyResult.sensitivity_label}</Tag>
              </div>
              <p className="text-sm">置信度: {(classifyResult.confidence * 100).toFixed(1)}%</p>
              {classifyResult.sm3_hash && (
                <p className="text-xs font-mono break-all text-gray-500 mt-1">
                  SM3指纹: {classifyResult.sm3_hash}
                </p>
              )}
              <p className="text-xs text-gray-500 mt-1">
                匹配规则: {classifyResult.matched_rules?.map((r: any) => r.rule_name).join(', ') || '无'}
              </p>
            </div>
          ) : (
            <p className="text-sm text-gray-400">点击分类项操作按钮触发自动分类</p>
          )}
        </div>
      </Dialog>

      {/* 完整性验证弹窗 */}
      <Dialog
        header="数据完整性验证"
        visible={verifyDialogOpen}
        onClose={onVerifyClose}
        width={520}
        footer={
          <div className="flex justify-end">
            <Button onClick={onVerifyClose}>关闭</Button>
          </div>
        }
        destroyOnClose
      >
        <div className="flex flex-col gap-4">
          <p className="text-sm text-gray-500">
            验证数据的SM3哈希指纹是否与预期一致。
          </p>
          {verifyResult ? (
            <div className={`border rounded-lg p-4 ${verifyResult.valid ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
              <div className="flex items-center gap-2">
                {verifyResult.valid ? (
                  <CheckCircleIcon size="20px" className="text-green-500" />
                ) : (
                  <ShieldErrorFilledIcon size="20px" className="text-red-500" />
                )}
                <span className="text-base font-bold">
                  {verifyResult.valid ? '验证通过 - 数据完整' : '验证失败 - 数据可能被篡改'}
                </span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-400">点击操作列中的验证按钮进行完整性验证</p>
          )}
        </div>
      </Dialog>
    </>
  );
};

export default CatalogDetail;
