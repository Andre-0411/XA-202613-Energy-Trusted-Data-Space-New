r"""
Schema 补丁脚本 - 添加 28 个缺失的 schema 类
在服务器上运行: cd D:\Andre\project\energy-trusted-data-space\backend && python ..\patch_schemas.py
"""
import os
import sys

PATCHES = {
    # ==================== subscription.py ====================
    "app/schemas/subscription.py": {
        "old_review": '''class DataSubscriptionReview(BaseModel):
    """审核订阅申请"""
    status: str = Field(description="审核结果: approved/rejected")
    expires_at: Optional[str] = Field(default=None, description="过期时间")''',
        "new_review": '''class DataSubscriptionReview(BaseModel):
    """审核订阅申请"""
    action: str = Field(description="审核动作: approve/reject")
    comment: Optional[str] = Field(default=None, description="审核意见")
    contract_id: Optional[str] = Field(default=None, description="关联合约 ID")
    subscription_config: Optional[dict] = Field(default=None, description="订阅配置")
    status: Optional[str] = Field(default=None, description="审核结果（兼容字段）")
    expires_at: Optional[str] = Field(default=None, description="过期时间")''',
        "old_delivery_end": '''# 重建引用
DataSubscriptionResponse.model_rebuild()''',
        "new_delivery_end": '''# 别名: DeliveryInfo 用于交付信息查询端点
DeliveryInfo = DataDeliveryResponse


# 重建引用
DataSubscriptionResponse.model_rebuild()''',
    },

    # ==================== contract.py ====================
    "app/schemas/contract.py": {
        "old_sign": '''class ContractSign(BaseModel):
    """签署合约"""
    blockchain_enabled: bool = Field(default=False, description="是否上链存证")''',
        "new_sign": '''class ContractApproval(BaseModel):
    """审批合约"""
    action: str = Field(description="审批动作: approve/reject")
    comment: Optional[str] = Field(default=None, description="审批意见")


class ContractSign(BaseModel):
    """签署合约"""
    signature_data: str = Field(default="", description="签名数据（SM2）")
    blockchain_enabled: bool = Field(default=False, description="是否上链存证")''',
        "old_pricing_gap": '''    effective_date: Optional[str] = Field(default=None, description="生效日期 ISO 8601")
    expiration_date: Optional[str] = Field(default=None, description="到期日期 ISO 8601")


class ContractUpdate(BaseModel):''',
        "new_pricing_gap": '''    effective_date: Optional[str] = Field(default=None, description="生效日期 ISO 8601")
    expiration_date: Optional[str] = Field(default=None, description="到期日期 ISO 8601")


class PricingConfig(BaseModel):
    """定价值配置"""
    pricing_model: str = Field(default="fixed", description="定价模式: fixed/subscription/per_usage/tiered")
    price: float = Field(default=0.0, description="价格")
    currency: str = Field(default="CNY", description="货币")
    billing_cycle: Optional[str] = Field(default=None, description="计费周期: monthly/quarterly/yearly")
    config: dict = Field(default_factory=dict, description="扩展配置")


class ContractAmendment(BaseModel):
    """合约变更/终止申请"""
    amendment_type: str = Field(default="change", description="变更类型: change/terminate")
    reason: str = Field(description="变更原因")
    changes: dict = Field(default_factory=dict, description="变更内容")


class AmendmentReview(BaseModel):
    """审核合约变更"""
    action: str = Field(description="审核动作: approve/reject")
    comment: Optional[str] = Field(default=None, description="审核意见")


class ContractUpdate(BaseModel):''',
    },

    # ==================== demand.py ====================
    "app/schemas/demand.py": {
        "old_demand_gap": '''class DemandPublish(BaseModel):
    """发布需求"""
    pass  # 只需改变状态，无额外参数


class DemandResponse(BaseModel):''',
        "new_demand_gap": '''class DemandPublish(BaseModel):
    """发布需求"""
    pass  # 只需改变状态，无额外参数


class DemandStatusUpdate(BaseModel):
    """更新需求状态"""
    status: str = Field(description="目标状态: open/closed/suspended")


class RiskAssessment(BaseModel):
    """安全风险评估"""
    risk_level: str = Field(default="medium", description="风险等级: low/medium/high/critical")
    assessment_result: dict = Field(default_factory=dict, description="评估结果")
    mitigation_measures: list = Field(default_factory=list, description="缓解措施")
    comment: Optional[str] = Field(default=None, description="评估备注")


class DemandResponse(BaseModel):''',
    },

    # ==================== product.py ====================
    "app/schemas/product.py": {
        # ProjectMemberAdd alias
        "old_member": '''class ProjectMemberCreate(BaseModel):
    """添加项目成员"""
    user_id: str = Field(description="用户 ID")
    role: str = Field(default="member", description="角色: owner/admin/developer/tester/member")''',
        "new_member": '''class ProjectMemberCreate(BaseModel):
    """添加项目成员"""
    user_id: str = Field(description="用户 ID")
    role: str = Field(default="member", description="角色: owner/admin/developer/tester/member")


# 别名: ProjectMemberAdd 与 ProjectMemberCreate 语义一致
ProjectMemberAdd = ProjectMemberCreate


class DataSourceConfig(BaseModel):
    """项目数据源配置"""
    data_sources: list = Field(default_factory=list, description="数据源列表")
    config: dict = Field(default_factory=dict, description="配置参数")''',

        # ComputeEngineConfig + ProductAcceptance alias
        "old_update_end": '''class DataProductUpdate(BaseModel):
    """更新数据产品"""
    name: Optional[str] = Field(default=None, description="产品名称")
    description: Optional[str] = Field(default=None, description="产品描述")
    product_type: Optional[str] = Field(default=None, description="产品类型")
    compute_engine: Optional[str] = Field(default=None, description="计算引擎")
    version: Optional[str] = Field(default=None, description="版本号")
    technical_spec: Optional[dict] = Field(default=None, description="技术规格")
    pricing: Optional[dict] = Field(default=None, description="定价信息")
    delivery_config: Optional[dict] = Field(default=None, description="交付配置")
    compliance_docs: Optional[list] = Field(default=None, description="合规文档")
    control_protocol: Optional[dict] = Field(default=None, description="管控协议")
    status: Optional[str] = Field(default=None, description="状态")''',
        "new_update_end": '''class DataProductUpdate(BaseModel):
    """更新数据产品"""
    name: Optional[str] = Field(default=None, description="产品名称")
    description: Optional[str] = Field(default=None, description="产品描述")
    product_type: Optional[str] = Field(default=None, description="产品类型")
    compute_engine: Optional[str] = Field(default=None, description="计算引擎")
    version: Optional[str] = Field(default=None, description="版本号")
    technical_spec: Optional[dict] = Field(default=None, description="技术规格")
    pricing: Optional[dict] = Field(default=None, description="定价信息")
    delivery_config: Optional[dict] = Field(default=None, description="交付配置")
    compliance_docs: Optional[list] = Field(default=None, description="合规文档")
    control_protocol: Optional[dict] = Field(default=None, description="管控协议")
    status: Optional[str] = Field(default=None, description="状态")


class ComputeEngineConfig(BaseModel):
    """计算引擎配置"""
    engine_type: str = Field(description="引擎类型: sql/python/spark/flink/custom")
    engine_config: dict = Field(default_factory=dict, description="引擎参数")
    resource_limits: dict = Field(default_factory=dict, description="资源限制")''',

        # ProductAcceptance + status field
        "old_acceptance": '''class ProductAcceptanceCreate(BaseModel):
    """创建产品验收"""
    product_id: str = Field(description="产品 ID")
    acceptor_id: str = Field(description="验收人 ID")
    test_result: dict = Field(default_factory=dict, description="测试结果")
    comment: Optional[str] = Field(default=None, description="验收意见")''',
        "new_acceptance": '''class ProductAcceptanceCreate(BaseModel):
    """创建产品验收"""
    product_id: str = Field(description="产品 ID")
    acceptor_id: str = Field(description="验收人 ID")
    test_result: dict = Field(default_factory=dict, description="测试结果")
    status: Optional[str] = Field(default=None, description="验收状态")
    comment: Optional[str] = Field(default=None, description="验收意见")


# 别名: ProductAcceptance 与 ProductAcceptanceCreate 语义一致
ProductAcceptance = ProductAcceptanceCreate''',

        # ProductPublishRequest alias
        "old_publish_create": '''class ProductPublishCreate(BaseModel):
    """创建产品上架申请"""
    product_id: str = Field(description="产品 ID")
    review_deadline: Optional[str] = Field(default=None, description="审核截止时间")
    control_protocol: dict = Field(default_factory=dict, description="管控协议")
    compliance_docs: list = Field(default_factory=list, description="合规文档")
    pricing_config: dict = Field(default_factory=dict, description="定价配置")''',
        "new_publish_create": '''class ProductPublishCreate(BaseModel):
    """创建产品上架申请"""
    product_id: str = Field(description="产品 ID")
    review_deadline: Optional[str] = Field(default=None, description="审核截止时间")
    control_protocol: dict = Field(default_factory=dict, description="管控协议")
    compliance_docs: list = Field(default_factory=list, description="合规文档")
    pricing_config: dict = Field(default_factory=dict, description="定价配置")


# 别名: ProductPublishRequest 与 ProductPublishCreate 语义一致
ProductPublishRequest = ProductPublishCreate''',

        # ProductPublishReview action fields
        "old_publish_review": '''class ProductPublishReview(BaseModel):
    """审核产品上架"""
    status: str = Field(description="审核结果: approved/rejected")
    review_comment: Optional[str] = Field(default=None, description="审核意见")''',
        "new_publish_review": '''class ProductPublishReview(BaseModel):
    """审核产品上架"""
    action: str = Field(description="审核动作: approve/reject")
    comment: Optional[str] = Field(default=None, description="审核意见")
    status: Optional[str] = Field(default=None, description="审核结果: approved/rejected（兼容字段）")
    review_comment: Optional[str] = Field(default=None, description="审核意见（兼容字段）")''',

        # ProductPublishResponse alias + UnpublishRequest + UnpublishReview
        "old_publish_resp_end": '''class ProductPublishRequestResponse(BaseModel):
    """产品上架申请响应"""
    id: str = Field(description="申请 ID")
    product_id: str = Field(description="产品 ID")
    applicant_id: str = Field(description="申请人 ID")
    organization_id: str = Field(description="组织 ID")
    review_deadline: Optional[str] = Field(default=None)
    control_protocol: dict = Field(default_factory=dict)
    compliance_docs: list = Field(default_factory=list)
    pricing_config: dict = Field(default_factory=dict)
    status: str = Field(description="状态")
    reviewer_id: Optional[str] = Field(default=None)
    review_comment: Optional[str] = Field(default=None)
    reviewed_at: Optional[str] = Field(default=None)
    published_at: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")''',
        "new_publish_resp_end": '''class ProductPublishRequestResponse(BaseModel):
    """产品上架申请响应"""
    id: str = Field(description="申请 ID")
    product_id: str = Field(description="产品 ID")
    applicant_id: str = Field(description="申请人 ID")
    organization_id: str = Field(description="组织 ID")
    review_deadline: Optional[str] = Field(default=None)
    control_protocol: dict = Field(default_factory=dict)
    compliance_docs: list = Field(default_factory=list)
    pricing_config: dict = Field(default_factory=dict)
    status: str = Field(description="状态")
    reviewer_id: Optional[str] = Field(default=None)
    review_comment: Optional[str] = Field(default=None)
    reviewed_at: Optional[str] = Field(default=None)
    published_at: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


# 别名: ProductPublishResponse 与 ProductPublishRequestResponse 语义一致
ProductPublishResponse = ProductPublishRequestResponse


class UnpublishRequest(BaseModel):
    """产品下架申请"""
    product_id: str = Field(description="产品 ID")
    reason: Optional[str] = Field(default=None, description="下架理由")


class UnpublishReview(BaseModel):
    """审核产品下架"""
    action: str = Field(description="审核动作: approve/reject")
    comment: Optional[str] = Field(default=None, description="审核意见")''',

        # ProductSubscriptionReview action fields
        "old_sub_review": '''class ProductSubscriptionReview(BaseModel):
    """审核产品订阅"""
    status: str = Field(description="审核结果: approved/rejected")
    expires_at: Optional[str] = Field(default=None, description="过期时间")''',
        "new_sub_review": '''class ProductSubscriptionReview(BaseModel):
    """审核产品订阅"""
    action: str = Field(description="审核动作: approve/reject")
    comment: Optional[str] = Field(default=None, description="审核意见")
    status: Optional[str] = Field(default=None, description="审核结果（兼容字段）")
    expires_at: Optional[str] = Field(default=None, description="过期时间")''',

        # UnpublishResponse end -> add ProductMarketItem + ContractFiling + ProductDeliveryInfo + ControlProtocolConfig + ComplianceDocUpload
        "old_unpublish_end": '''class ProductUnpublishResponse(BaseModel):
    """产品下架申请响应"""
    id: str = Field(description="申请 ID")
    product_id: str = Field(description="产品 ID")
    applicant_id: str = Field(description="申请人 ID")
    reason: Optional[str] = Field(default=None)
    status: str = Field(description="状态")
    reviewer_id: Optional[str] = Field(default=None)
    review_comment: Optional[str] = Field(default=None)
    reviewed_at: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")''',
        "new_unpublish_end": '''class ProductUnpublishResponse(BaseModel):
    """产品下架申请响应"""
    id: str = Field(description="申请 ID")
    product_id: str = Field(description="产品 ID")
    applicant_id: str = Field(description="申请人 ID")
    reason: Optional[str] = Field(default=None)
    status: str = Field(description="状态")
    reviewer_id: Optional[str] = Field(default=None)
    review_comment: Optional[str] = Field(default=None)
    reviewed_at: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")


class ProductMarketItem(BaseModel):
    """产品市场列表项"""
    id: str = Field(description="产品 ID")
    name: str = Field(description="产品名称")
    description: Optional[str] = Field(default=None, description="产品描述")
    product_type: str = Field(description="产品类型")
    organization_id: str = Field(description="所属组织 ID")
    organization_name: Optional[str] = Field(default=None, description="组织名称")
    pricing: dict = Field(default_factory=dict, description="定价信息")
    rating: float = Field(default=0.0, description="评分")
    subscriber_count: int = Field(default=0, description="订阅数")
    published_at: Optional[str] = Field(default=None, description="上架时间")
    tags: list = Field(default_factory=list, description="标签")


class ContractFiling(BaseModel):
    """合约备案"""
    contract_id: str = Field(description="合约 ID")


class ProductDeliveryInfo(BaseModel):
    """产品交付信息"""
    subscription_id: str = Field(description="订阅 ID")
    delivery_type: str = Field(description="交付类型")
    delivery_config: dict = Field(default_factory=dict, description="交付配置")
    access_token: Optional[str] = Field(default=None, description="访问令牌")
    access_url: Optional[str] = Field(default=None, description="访问 URL")
    status: str = Field(default="pending", description="交付状态")
    last_delivered_at: Optional[str] = Field(default=None, description="最后交付时间")


class ControlProtocolConfig(BaseModel):
    """管控协议配置"""
    protocol_type: str = Field(default="default", description="协议类型")
    rules: dict = Field(default_factory=dict, description="协议规则")
    description: Optional[str] = Field(default=None, description="协议描述")


class ComplianceDocUpload(BaseModel):
    """合规材料上传"""
    docs: List[dict] = Field(default_factory=list, description="合规文档列表")''',
    },

    # ==================== connector.py (文件库部分) ====================
    "app/schemas/connector.py": {
        "old_end": '''    security_scan_result: dict = Field(default_factory=dict)
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")''',
        "new_end": '''    security_scan_result: dict = Field(default_factory=dict)
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


# ==================== 连接器文件库 ====================

class ConnectorFileResponse(BaseModel):
    """连接器文件响应"""
    id: str = Field(description="文件 ID")
    connector_id: str = Field(description="连接器 ID")
    file_name: str = Field(description="文件名")
    file_path: str = Field(description="文件路径")
    file_size: Optional[int] = Field(default=None, description="文件大小")
    file_type: Optional[str] = Field(default=None, description="文件类型")
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")


class FileSetCreate(BaseModel):
    """创建文件集"""
    name: str = Field(description="文件集名称")
    description: Optional[str] = Field(default=None, description="描述")
    file_ids: List[str] = Field(default_factory=list, description="文件 ID 列表")


class FileSetResponse(BaseModel):
    """文件集响应"""
    id: str = Field(description="文件集 ID")
    connector_id: str = Field(description="连接器 ID")
    name: str = Field(description="名称")
    description: Optional[str] = Field(default=None)
    file_ids: List[str] = Field(default_factory=list)
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")


class ApiProxyCreate(BaseModel):
    """创建 API 代理"""
    name: str = Field(description="API 名称")
    target_url: str = Field(description="目标 URL")
    http_method: str = Field(default="GET", description="HTTP 方法")
    headers: dict = Field(default_factory=dict, description="请求头")
    auth_config: dict = Field(default_factory=dict, description="认证配置")


class ApiProxyResponse(BaseModel):
    """API 代理响应"""
    id: str = Field(description="API ID")
    connector_id: str = Field(description="连接器 ID")
    name: str = Field(description="名称")
    target_url: str = Field(description="目标 URL")
    http_method: str = Field(description="HTTP 方法")
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")


class ApiProxyTestResult(BaseModel):
    """API 代理测试结果"""
    success: bool = Field(description="是否成功")
    status_code: Optional[int] = Field(default=None, description="HTTP 状态码")
    response_time_ms: Optional[float] = Field(default=None, description="响应时间(ms)")
    error_message: Optional[str] = Field(default=None, description="错误信息")''',
    },

    # ==================== workflow.py ====================
    "app/schemas/workflow.py": {
        "old_action": '''class ApprovalAction(BaseModel):
    """审批操作"""
    action: str = Field(description="操作: approve/reject")
    comment: Optional[str] = Field(default=None, description="审批意见")''',
        "new_action": '''class ApprovalAction(BaseModel):
    """审批操作"""
    action: str = Field(description="操作: approve/reject")
    comment: Optional[str] = Field(default=None, description="审批意见")


class WorkflowApproval(BaseModel):
    """审批通过"""
    comment: Optional[str] = Field(default=None, description="审批意见")


class WorkflowRejection(BaseModel):
    """审批拒绝"""
    comment: Optional[str] = Field(default=None, description="拒绝原因")''',
    },
}


def apply_patches():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, "backend")
    
    if not os.path.exists(os.path.join(backend_dir, "app", "schemas")):
        print("ERROR: 请在项目根目录运行此脚本 (包含 backend/app/schemas/ 的目录)")
        sys.exit(1)
    
    total_patched = 0
    total_skipped = 0
    
    for rel_path, patches in PATCHES.items():
        file_path = os.path.join(backend_dir, rel_path)
        if not os.path.exists(file_path):
            print(f"  SKIP: {rel_path} (文件不存在)")
            total_skipped += 1
            continue
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        file_patched = 0
        for patch_name, old_str in patches.items():
            if not patch_name.startswith("old_"):
                continue
            new_key = patch_name.replace("old_", "new_")
            new_str = patches.get(new_key)
            if not new_str:
                continue
            
            # 跳过: 新内容已存在 (幂等性)
            if new_str in content:
                continue
            
            if old_str in content:
                content = content.replace(old_str, new_str)
                file_patched += 1
        
        # connector.py 特殊处理: 如果模式匹配失败但文件库类不存在, 追加到末尾
        if rel_path == "app/schemas/connector.py" and file_patched == 0:
            if "ConnectorFileResponse" not in content:
                # 确保 List 已导入
                if "List" not in content:
                    content = content.replace(
                        "from typing import Optional, Any",
                        "from typing import Optional, Any, List"
                    )
                content += CONNECTOR_FILE_LIBRARY
                file_patched = 1
                print(f"  APPENDED: connector file library classes to {rel_path}")
        
        if file_patched > 0:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  PATCHED: {rel_path} ({file_patched} patches applied)")
            total_patched += 1
        else:
            print(f"  SKIP: {rel_path} (already patched or no match)")
            total_skipped += 1
    
    print(f"\nDone: {total_patched} files patched, {total_skipped} skipped")


# connector.py 文件库追加内容 (兜底方案)
CONNECTOR_FILE_LIBRARY = """


# ==================== 连接器文件库 ====================

class ConnectorFileResponse(BaseModel):
    \"\"\"连接器文件响应\"\"\"
    id: str = Field(description="文件 ID")
    connector_id: str = Field(description="连接器 ID")
    file_name: str = Field(description="文件名")
    file_path: str = Field(description="文件路径")
    file_size: Optional[int] = Field(default=None, description="文件大小")
    file_type: Optional[str] = Field(default=None, description="文件类型")
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")


class FileSetCreate(BaseModel):
    \"\"\"创建文件集\"\"\"
    name: str = Field(description="文件集名称")
    description: Optional[str] = Field(default=None, description="描述")
    file_ids: List[str] = Field(default_factory=list, description="文件 ID 列表")


class FileSetResponse(BaseModel):
    \"\"\"文件集响应\"\"\"
    id: str = Field(description="文件集 ID")
    connector_id: str = Field(description="连接器 ID")
    name: str = Field(description="名称")
    description: Optional[str] = Field(default=None)
    file_ids: List[str] = Field(default_factory=list)
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")


class ApiProxyCreate(BaseModel):
    \"\"\"创建 API 代理\"\"\"
    name: str = Field(description="API 名称")
    target_url: str = Field(description="目标 URL")
    http_method: str = Field(default="GET", description="HTTP 方法")
    headers: dict = Field(default_factory=dict, description="请求头")
    auth_config: dict = Field(default_factory=dict, description="认证配置")


class ApiProxyResponse(BaseModel):
    \"\"\"API 代理响应\"\"\"
    id: str = Field(description="API ID")
    connector_id: str = Field(description="连接器 ID")
    name: str = Field(description="名称")
    target_url: str = Field(description="目标 URL")
    http_method: str = Field(description="HTTP 方法")
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")


class ApiProxyTestResult(BaseModel):
    \"\"\"API 代理测试结果\"\"\"
    success: bool = Field(description="是否成功")
    status_code: Optional[int] = Field(default=None, description="HTTP 状态码")
    response_time_ms: Optional[float] = Field(default=None, description="响应时间(ms)")
    error_message: Optional[str] = Field(default=None, description="错误信息")
"""


if __name__ == "__main__":
    apply_patches()
