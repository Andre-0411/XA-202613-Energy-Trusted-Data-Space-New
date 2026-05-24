/**
 * 合约详情页面
 */
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Tag, Tabs, Button } from 'tdesign-react';
import { ArrowLeftIcon } from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import { getContract, listAmendments, verifyContractOnChain } from '@/api/contractManage';

const statusThemeMap: Record<string, 'success' | 'warning' | 'danger' | 'default' | 'primary'> = {
  draft: 'default',
  pending_review: 'warning',
  active: 'success',
  expired: 'danger',
  terminated: 'danger',
};

const contractTypeMap: Record<string, string> = {
  data_subscription: '数据订阅',
  product_subscription: '产品订阅',
  joint_compute: '联合计算',
  custom: '自定义',
};

export default function ContractDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState('0');

  const { data, isLoading } = useQuery({
    queryKey: ['contract-manage', id],
    queryFn: () => getContract(id!),
    enabled: !!id,
  });

  const { data: amendmentsData } = useQuery({
    queryKey: ['contract-amendments', id],
    queryFn: () => listAmendments(id!),
    enabled: !!id,
  });

  const { data: verifyData } = useQuery({
    queryKey: ['contract-verify', id],
    queryFn: () => verifyContractOnChain(id!),
    enabled: !!id && !!data?.data?.blockchain_tx_hash,
  });

  const contract = data?.data;

  if (isLoading) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center py-20 text-gray-500">加载中...</div>
      </PageContainer>
    );
  }

  if (!contract) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center py-20 text-gray-500">合约不存在</div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title={contract.title}
        subtitle={`编号: ${contract.contract_no} | 类型: ${contractTypeMap[contract.contract_type] || contract.contract_type}`}
        breadcrumbs={[
          homeBreadcrumb,
          { label: 'TDS管理', href: '/dashboard/tds' },
          { label: '合约管理', href: '/dashboard/tds/contracts' },
          { label: contract.title },
        ]}
        action={
          <Button
            variant="outline"
            icon={<ArrowLeftIcon />}
            onClick={() => navigate('/dashboard/tds/contracts')}
          >
            返回
          </Button>
        }
      />

      <Tabs value={tabValue} onChange={(val) => setTabValue(String(val))}>
        <Tabs.TabPanel value="0" label="基本信息">
          <PageSection className="mt-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <span className="text-xs text-gray-500 block mb-1">状态</span>
                <Tag theme={statusThemeMap[contract.status] || 'default'}>{contract.status}</Tag>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">甲方机构</span>
                <p className="text-sm text-gray-700">{contract.party_a_org_id}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">乙方机构</span>
                <p className="text-sm text-gray-700">{contract.party_b_org_id}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">生效日期</span>
                <p className="text-sm text-gray-700">{contract.effective_date ? new Date(contract.effective_date).toLocaleDateString('zh-CN') : '未设定'}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">到期日期</span>
                <p className="text-sm text-gray-700">{contract.expiration_date ? new Date(contract.expiration_date).toLocaleDateString('zh-CN') : '未设定'}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">创建时间</span>
                <p className="text-sm text-gray-700">{new Date(contract.created_at).toLocaleString('zh-CN')}</p>
              </div>
              <div className="col-span-2">
                <span className="text-xs text-gray-500 block mb-1">合约内容</span>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{contract.content}</p>
              </div>
            </div>
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="1" label="合约条款">
          <PageSection className="mt-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <span className="text-xs text-gray-500 block mb-1">条款</span>
                <pre className="text-xs text-gray-700 mt-1 whitespace-pre-wrap font-mono">
                  {contract.terms ? JSON.stringify(contract.terms, null, 2) : '无'}
                </pre>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-1">定价</span>
                <pre className="text-xs text-gray-700 mt-1 whitespace-pre-wrap font-mono">
                  {contract.pricing ? JSON.stringify(contract.pricing, null, 2) : '无'}
                </pre>
              </div>
              {contract.related_subscription_id && (
                <div>
                  <span className="text-xs text-gray-500 block mb-1">关联订阅ID</span>
                  <p className="text-sm text-gray-700">{contract.related_subscription_id}</p>
                </div>
              )}
              {contract.related_product_id && (
                <div>
                  <span className="text-xs text-gray-500 block mb-1">关联产品ID</span>
                  <p className="text-sm text-gray-700">{contract.related_product_id}</p>
                </div>
              )}
            </div>
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="2" label="修订记录">
          <PageSection className="mt-2">
            {amendmentsData?.data?.items?.length ? (
              <div className="flex flex-col gap-4">
                {amendmentsData.data.items.map((amendment: any) => (
                  <div key={amendment.id} className="rounded-lg border border-gray-200 p-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-gray-800">修订 #{amendment.amendment_no}</h3>
                      <Tag theme={amendment.status === 'approved' ? 'success' : amendment.status === 'rejected' ? 'danger' : 'warning'}>
                        {amendment.status}
                      </Tag>
                    </div>
                    <p className="text-xs text-gray-600 mt-1">{amendment.reason}</p>
                    <span className="text-xs text-gray-400">
                      {new Date(amendment.created_at).toLocaleString('zh-CN')}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">暂无修订记录</p>
            )}
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="3" label="链上存证">
          <PageSection className="mt-2">
            {contract.blockchain_tx_hash ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <span className="text-xs text-gray-500 block mb-1">交易哈希</span>
                  <p className="text-xs text-gray-700 font-mono break-all">{contract.blockchain_tx_hash}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500 block mb-1">合约地址</span>
                  <p className="text-xs text-gray-700 font-mono break-all">{contract.blockchain_contract_address || '-'}</p>
                </div>
                {verifyData?.data && (
                  <>
                    <div>
                      <span className="text-xs text-gray-500 block mb-1">验证状态</span>
                      <Tag theme={verifyData.data.verified ? 'success' : 'danger'}>
                        {verifyData.data.verified ? '已验证' : '验证失败'}
                      </Tag>
                    </div>
                    <div>
                      <span className="text-xs text-gray-500 block mb-1">区块号</span>
                      <p className="text-sm text-gray-700">{verifyData.data.block_number}</p>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-500">该合约尚未进行链上存证</p>
            )}
          </PageSection>
        </Tabs.TabPanel>
      </Tabs>
    </PageContainer>
  );
}
