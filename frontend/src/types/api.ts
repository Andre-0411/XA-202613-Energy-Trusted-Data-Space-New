// API Types for Energy Trusted Data Space

// ==================== Common ====================

export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface PaginatedRequest {
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// ==================== Auth ====================

export interface LoginRequest {
  username: string;
  password: string;
}

export interface DIDLoginRequest {
  did: string;
  signature: string;
  challenge: string;
}

export interface CertificateLoginRequest {
  certificate: string;
  password: string;
}

export interface MfaVerifyRequest {
  code: string;
  user_id: string;
  session_id?: string;
}

export interface SessionInfo {
  session_id: string;
  user_id: string;
  ip_address: string;
  user_agent: string;
  created_at: string;
  expires_at: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserInfo;
  /** MFA verification result */
  verified?: boolean;
  message?: string;
}

export interface UserInfo {
  user_id: string;
  username: string;
  email: string;
  role: string;
  organization_id: string;
  phone?: string;
  status?: string;
  did?: string;
  department_id?: string;
  permissions?: string[];
}

// ==================== Compute ====================

export interface ComputeTask {
  id: string;
  name: string;
  task_type: string;
  status: string;
  scenario: string | null;
  initiator_id: string;
  organization_id: string;
  config: Record<string, unknown>;
  result: Record<string, unknown> | null;
  signature_threshold: number;
  created_at: string;
  updated_at: string;
}

export interface TaskSignature {
  id: string;
  task_id: string;
  signer_id: string;
  signer_did: string;
  signature: string;
  signed_at: string;
}

export interface DagDefinition {
  id: string;
  name: string;
  description: string | null;
  nodes: DagNode[];
  edges: DagEdge[];
  status: string;
  created_at: string;
  updated_at: string;
}

export interface DagNode {
  id: string;
  name: string;
  task_type: string;
  config: Record<string, unknown>;
}

export interface DagEdge {
  source: string;
  target: string;
  data_type: string;
}

export interface FlModel {
  id: string;
  name: string;
  algorithm: string;
  status: string;
  metrics: Record<string, number> | null;
  created_at: string;
}

export interface Sandbox {
  id: string;
  name: string;
  algorithm: string;
  status: string;
  config: Record<string, unknown>;
  result: Record<string, unknown> | null;
  created_at: string;
}

export interface CryptoResult {
  algorithm: string;
  operation: string;
  result: unknown;
}

// ==================== Compute Cluster ====================

export interface ClusterNode {
  id: string;
  name: string;
  host: string;
  port: number;
  node_type: 'cpu' | 'gpu' | 'tee' | 'fpga';
  status: 'online' | 'offline' | 'busy' | 'maintenance';
  cpu_cores: number;
  gpu_count: number;
  gpu_model: string | null;
  memory_total_gb: number;
  memory_used_gb: number;
  cpu_usage_percent: number;
  gpu_usage_percent: number;
  disk_usage_percent: number;
  network_in_mbps: number;
  network_out_mbps: number;
  running_tasks: number;
  max_tasks: number;
  last_heartbeat: string;
  registered_at: string;
  tags: string[];
  metadata: Record<string, unknown> | null;
}

export interface ClusterStatus {
  total_nodes: number;
  online_nodes: number;
  offline_nodes: number;
  busy_nodes: number;
  maintenance_nodes: number;
  total_cpu_cores: number;
  total_gpu_count: number;
  avg_cpu_usage: number;
  avg_gpu_usage: number;
  total_running_tasks: number;
  total_max_tasks: number;
  cluster_uptime_hours: number;
}

export interface RegisterNodeRequest {
  name: string;
  host: string;
  port: number;
  node_type: 'cpu' | 'gpu' | 'tee' | 'fpga';
  cpu_cores: number;
  gpu_count?: number;
  gpu_model?: string;
  memory_total_gb: number;
  max_tasks?: number;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface DispatchTaskRequest {
  task_id: string;
  node_id?: string;
  strategy?: 'round_robin' | 'least_loaded' | 'random' | 'gpu_preferred';
}

// ==================== Blockchain ====================

export interface NftAsset {
  id: string;
  token_id: string;
  asset_id: string;
  owner: string;
  token_uri: string;
  metadata_uri: string | null;
  metadata: Record<string, unknown>;
  tx_hash: string | null;
  status: string;
  created_at: string;
}

export interface Evidence {
  id: string;
  evidence_type: string;
  hash: string;
  evidence_hash: string;
  data: Record<string, unknown>;
  blockchain_tx: string | null;
  tx_hash: string | null;
  block_number: number | null;
  uploader_did: string;
  description: string | null;
  status: string;
  created_at: string;
}

export interface SmartContract {
  id: string;
  name: string;
  version: string;
  address: string;
  abi: Record<string, unknown> | unknown[];
  network: string;
  status: string;
  deployed_at: string;
  deploy_tx_hash?: string;
  description?: string;
  created_at: string;
}

export interface Settlement {
  id: string;
  asset_id: string;
  from_org: string;
  to_org: string;
  amount: number;
  service_id: string;
  status: string;
  tx_hash: string | null;
  created_at: string;
}

// ==================== Data ====================

export interface DataSource {
  id: string;
  name: string;
  code: string;
  source_type: string;
  protocol: string;
  connection_config: Record<string, unknown>;
  status: string;
  organization_id: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface DataAsset {
  id: string;
  name: string;
  asset_code: string;
  asset_type: string;
  category: string;
  sensitivity_level: string;
  source_id: string;
  organization_id: string;
  owner_org_id: string;
  description: string | null;
  metadata: Record<string, unknown>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface DataCatalogItem {
  id: string;
  name: string;
  description: string;
  category: string;
  owner_org: string;
  sensitivity_level: string;
  tags: string[];
  status: string;
  usage_count: number;
  rating: number;
  rating_count: number;
  created_at: string;
  updated_at: string;
}

export interface MetadataRecord {
  id: string;
  asset_id: string;
  standard: string;
  schema_version: string;
  fields: Record<string, unknown>[];
  status: string;
  previous_version_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Tag {
  id: string;
  name: string;
  dimension: string;
  color: string;
}

export interface QualityReport {
  id: string;
  asset_id: string;
  completeness: number;
  accuracy: number;
  consistency: number;
  timeliness: number;
  overall_score: number;
  grade: string;
  details: Record<string, unknown> | null;
  generated_at: string | null;
  created_at: string;
}

// ==================== Operations ====================

export interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  organization_id: string;
  status: string;
  phone: string | null;
  mfa_enabled: boolean;
  last_login_at: string | null;
  permissions: string[];
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  code: string;
  did: string | null;
  parent_id: string | null;
  level: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ServiceCatalog {
  id: string;
  name: string;
  category: string;
  description: string | null;
  pricing_model: string;
  pricing_config: Record<string, unknown>;
  billing_mode?: string;
  price?: number;
  billing_unit?: string;
  status: string;
  created_at: string;
}

export interface Subscription {
  id: string;
  user_id: string;
  service_id: string;
  service_name?: string;
  status: string;
  start_date: string;
  end_date: string | null;
  quota_used: number;
  approval_status: string;
  approved_by: string | null;
  approved_at?: string | null;
  rejected_reason?: string | null;
  created_at: string;
}

export interface BillingRecord {
  id: string;
  subscription_id: string;
  amount: number;
  billing_period: string;
  usage_detail: Record<string, unknown> | null;
  payment_status: string;
  tx_hash: string | null;
  created_at: string;
}

export interface BillingSummary {
  total_revenue: number;
  pending_payments: number;
  completed_payments: number;
  overdue_payments: number;
  billing_by_service: Record<string, number>;
  billing_by_month: Record<string, number>;
}

export interface AlertInfo {
  id: string;
  type: string;
  severity: string;
  title: string;
  message: string;
  source: string;
  status: string;
  acknowledged_by: string | null;
  fired_at: string;
  created_at: string;
}

export interface ComplianceReport {
  id: string;
  organization_id: string;
  report_type: string;
  period: string;
  findings: Record<string, unknown>;
  status: string;
  overall_score: number;
  compliance_score: number;
  generated_at: string | null;
  created_at: string;
}

export interface KpiDashboard {
  total_assets: number;
  total_compute_tasks: number;
  active_users: number;
  total_organizations: number;
  blockchain_transactions: number;
  security_incidents: number;
  avg_response_time_ms: number;
  uptime_percentage: number;
  data_quality_avg: number;
  compliance_score: number;
}

// ==================== Security ====================

export interface SecurityPolicy {
  id: string;
  name: string;
  policy_type: string;
  rules: Record<string, unknown>;
  priority: number;
  status: string;
  created_at: string;
}

export interface DidDocument {
  did: string;
  method: string;
  controller: string;
  status: string;
  document: Record<string, unknown>;
  created_at: string;
}

export interface VcRecord {
  id: string;
  vc_id: string;
  issuer_did: string;
  subject_did: string;
  vc_type: string;
  claims: Record<string, unknown>;
  status: string;
  issued_at: string;
  expires_at: string | null;
}

export interface KeyInfo {
  id: string;
  key_id: string;
  key_type: string;
  algorithm: string;
  hierarchy_level: string;
  purpose: string;
  parent_key_id: string | null;
  status: string;
  created_at: string;
}

export interface ThreatEvent {
  id: string;
  threat_type: string;
  severity: string;
  source: string | null;
  description: string;
  indicators: Record<string, unknown> | null;
  status: string;
  assigned_to: string | null;
  detected_at: string;
  resolved_at: string | null;
}

export interface ZkpProof {
  proof_id: string;
  proof_type: string;
  proof: Record<string, unknown>;
  public_signals?: string[];
  created_at: string;
}

// ==================== WebSocket ====================

export interface WsMessage {
  type: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

// ==================== Notifications ====================

export interface Notification {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
  created_at: string;
}

// ==================== Benchmark ====================

export interface BenchmarkResult {
  benchmark_id: string;
  status: string;
  algorithms: string[];
  iterations: number;
  data_size: number;
  participants: number;
  results: AlgorithmBenchmark[];
  started_at: string;
  completed_at: string;
  total_time_ms: number;
  error?: string;
}

export interface AlgorithmBenchmark {
  algorithm: string;
  algorithm_name: string;
  avg_time_ms: number;
  min_time_ms: number;
  max_time_ms: number;
  p50_time_ms: number;
  p95_time_ms: number;
  p99_time_ms: number;
  throughput: number;
  cpu_usage_percent: number;
  memory_usage_mb: number;
  task_count: number;
  success_rate: number;
  iterations: number;
}

export interface BenchmarkSummary {
  total_benchmarks: number;
  algorithms_tested: string[];
  latest_benchmark_id: string | null;
  latest_results: AlgorithmBenchmark[];
}

export interface BenchmarkTrendPoint {
  timestamp: string;
  algorithm: string;
  avg_time_ms: number;
  throughput: number;
  cpu_usage_percent: number;
  memory_usage_mb: number;
}

// ==================== Privacy Computing ====================

export interface PrivacyRouteResult {
  technology: string;
  technology_name: string;
  scenario: string;
  scenario_description: string;
  technology_info: PrivacyTechnology;
  config: Record<string, unknown>;
  alternatives: Array<{
    technology: string;
    technology_name: string;
    available: boolean;
  }>;
  reasoning: string;
  error?: string;
}

export interface PrivacyTechnology {
  technology: string;
  name: string;
  description: string;
  strengths: string[];
  weaknesses: string[];
  available: boolean;
}

export interface PrivacyScenario {
  scenario: string;
  description: string;
  recommended_technology: string;
  alternatives: string[];
  typical_algorithms: string[];
}

// ==================== 注册认证 ====================

export interface InviteCode {
  id: string;
  code: string;
  organization_id: string;
  created_by: string;
  max_uses: number;
  used_count: number;
  expires_at: string | null;
  status: string;
  created_at: string;
}

export interface OrganizationCertification {
  id: string;
  organization_id: string;
  certification_type: string;
  certification_data: Record<string, unknown>;
  status: string;
  reviewer_id: string | null;
  review_comment: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrganizationJoinRequest {
  id: string;
  user_id: string;
  organization_id: string;
  reason: string;
  status: string;
  reviewer_id: string | null;
  review_comment: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface CustomRole {
  id: string;
  name: string;
  description: string | null;
  permissions: string[];
  organization_id: string;
  created_by: string;
  status: string;
  created_at: string;
}

export interface UserRoleAssignment {
  id: string;
  user_id: string;
  role_id: string;
  assigned_by: string;
  assigned_at: string;
}

// ==================== 连接器管理 ====================

export interface Connector {
  id: string;
  name: string;
  connector_type: string;
  version: string;
  owner_id: string;
  organization_id: string;
  deployment_config: Record<string, unknown>;
  status: string;
  last_heartbeat_at: string | null;
  system_status: Record<string, unknown> | null;
  resource_usage: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ConnectorDataSource {
  id: string;
  connector_id: string;
  name: string;
  source_type: string;
  connection_config: Record<string, unknown>;
  refresh_schedule: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface MetadataDiscovery {
  id: string;
  connector_id: string;
  data_source_id: string;
  discovery_scope: Record<string, unknown>;
  result_summary: Record<string, unknown> | null;
  status: string;
  security_review_status: string;
  security_reviewer_id: string | null;
  created_at: string;
  updated_at: string;
}

// ==================== 数据目录注册 ====================

export interface CatalogRegistration {
  id: string;
  name: string;
  description: string;
  category: string;
  sensitivity_level: string;
  owner_id: string;
  organization_id: string;
  tags: string[];
  status: string;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ControlTemplate {
  id: string;
  catalog_id: string;
  template_type: string;
  rules: Record<string, unknown>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AccessScopeRule {
  id: string;
  catalog_id: string;
  rule_type: string;
  target_id: string;
  permissions: string[];
  conditions: Record<string, unknown> | null;
  status: string;
  created_at: string;
}

// ==================== 数据资源订阅 ====================

export interface DataSubscription {
  id: string;
  catalog_id: string;
  subscriber_id: string;
  subscriber_org_id: string;
  reason: string | null;
  subscription_config: Record<string, unknown> | null;
  status: string;
  reviewer_id: string | null;
  reviewed_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DataDelivery {
  id: string;
  subscription_id: string;
  delivery_type: string;
  delivery_config: Record<string, unknown>;
  access_token: string;
  download_count: number;
  status: string;
  created_at: string;
  updated_at: string;
}

// ==================== 数据产品 ====================

export interface ProductProject {
  id: string;
  name: string;
  project_type: string;
  description: string | null;
  owner_id: string;
  organization_id: string;
  data_sources: string[] | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectMember {
  id: string;
  project_id: string;
  user_id: string;
  role: string;
  joined_at: string;
}

export interface DataProduct {
  id: string;
  name: string;
  product_type: string;
  project_id: string | null;
  description: string | null;
  owner_id: string;
  organization_id: string;
  compute_engine: string | null;
  version: string;
  technical_spec: Record<string, unknown> | null;
  pricing: Record<string, unknown> | null;
  delivery_config: Record<string, unknown> | null;
  compliance_docs: Record<string, unknown> | null;
  control_protocol: Record<string, unknown> | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ProductAcceptance {
  id: string;
  product_id: string;
  acceptor_id: string;
  test_result: Record<string, unknown>;
  comment: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ProductPublishRequest {
  id: string;
  product_id: string;
  applicant_id: string;
  organization_id: string;
  review_deadline: string | null;
  control_protocol: Record<string, unknown> | null;
  compliance_docs: Record<string, unknown> | null;
  pricing_config: Record<string, unknown> | null;
  status: string;
  reviewer_id: string | null;
  review_comment: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductUnpublishRequest {
  id: string;
  product_id: string;
  applicant_id: string;
  reason: string;
  status: string;
  reviewer_id: string | null;
  review_comment: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductSubscription {
  id: string;
  product_id: string;
  subscriber_id: string;
  subscriber_org_id: string;
  reason: string | null;
  subscription_config: Record<string, unknown> | null;
  delivery_config: Record<string, unknown> | null;
  status: string;
  reviewer_id: string | null;
  reviewed_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductDelivery {
  id: string;
  product_subscription_id: string;
  delivery_type: string;
  delivery_config: Record<string, unknown>;
  access_token: string;
  download_count: number;
  status: string;
  created_at: string;
  updated_at: string;
}

// ==================== 需求管理 ====================

export interface Demand {
  id: string;
  title: string;
  demand_type: string;
  description: string;
  technical_requirements: Record<string, unknown> | null;
  budget_range: string | null;
  deadline: string | null;
  security_risk_assessment: Record<string, unknown> | null;
  publisher_id: string;
  organization_id: string;
  claimed_by_org: string | null;
  claimed_by_user: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface DemandClaim {
  id: string;
  demand_id: string;
  claimer_id: string;
  claimer_org_id: string;
  proposal: string;
  status: string;
  reviewer_id: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

// ==================== 合约管理 ====================

export interface Contract {
  id: string;
  contract_no: string;
  title: string;
  contract_type: 'data_subscription' | 'product_subscription' | 'joint_compute' | 'custom';
  party_a_org_id: string;
  party_a_user_id: string;
  party_b_org_id: string;
  party_b_user_id: string | null;
  related_subscription_id: string | null;
  related_product_id: string | null;
  content: string;
  terms: Record<string, unknown>;
  pricing: Record<string, unknown>;
  effective_date: string | null;
  expiration_date: string | null;
  blockchain_tx_hash: string | null;
  blockchain_contract_address: string | null;
  status: 'draft' | 'pending_review' | 'active' | 'expired' | 'terminated';
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ContractAmendment {
  id: string;
  contract_id: string;
  amendment_no: number;
  reason: string;
  changes: Record<string, unknown>;
  previous_terms: Record<string, unknown>;
  new_terms: Record<string, unknown>;
  approved_by: string | null;
  approved_at: string | null;
  status: 'pending' | 'approved' | 'rejected';
  created_by: string;
  created_at: string;
}

// ==================== 连接器文件管理 ====================

export interface ConnectorFile {
  id: string;
  connector_id: string;
  file_set_id: string | null;
  file_name: string;
  file_path: string;
  file_type: 'csv' | 'json' | 'xml' | 'pdf' | 'parquet' | 'xlsx';
  file_size_bytes: number;
  content_hash: string | null;
  row_count: number | null;
  column_schema: Record<string, unknown>[];
  metadata: Record<string, unknown>;
  status: string;
  uploaded_by: string;
  created_at: string;
}

export interface FileSet {
  id: string;
  name: string;
  description: string | null;
  organization_id: string;
  created_by: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ApiProxy {
  id: string;
  connector_id: string;
  name: string;
  description: string | null;
  target_url: string;
  http_method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  request_headers: Record<string, unknown>;
  request_params: Record<string, unknown>;
  request_body_template: string | null;
  response_mapping: Record<string, unknown>;
  auth_config: Record<string, unknown>;
  rate_limit: number;
  timeout_ms: number;
  retry_count: number;
  is_enabled: boolean;
  status: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

// ==================== 审批工作流 ====================

export interface ApprovalWorkflow {
  id: string;
  name: string;
  description: string | null;
  workflow_type: 'certification' | 'subscription' | 'product_publish' | 'product_unpublish' | 'demand_claim' | 'contract';
  organization_id: string | null;
  steps: Record<string, unknown>[];
  is_system: boolean;
  status: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ApprovalRecord {
  id: string;
  workflow_id: string;
  business_type: string;
  business_id: string;
  applicant_id: string;
  current_step: number;
  total_steps: number;
  approval_data: Record<string, unknown>;
  status: 'pending' | 'in_progress' | 'approved' | 'rejected' | 'cancelled';
  approved_by: string | null;
  approved_at: string | null;
  reject_reason: string | null;
  created_at: string;
  updated_at: string;
}
