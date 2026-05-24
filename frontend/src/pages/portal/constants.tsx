/**
 * LandingPage 共享数据常量
 */
import React from 'react';
import {
  FlashlightIcon,
  SunnyIcon,
  ThunderIcon,
  ServerIcon,
  InstitutionIcon,
  PlantumlIcon,
  HardDiskStorageIcon,
  CloudIcon,
  LinkIcon,
  UsergroupIcon,
  LockOnIcon,
  VerifiedIcon,
  ApiIcon,
  RocketIcon,
  DashboardIcon,
} from 'tdesign-icons-react';

/* ===== 导航菜单 ===== */
export const NAV_ITEMS = [
  { label: '首页', href: '#hero' },
  { label: '平台状态', href: '#status' },
  { label: 'Live Demo', href: '#demo' },
  { label: '数据服务', href: '#products' },
  { label: '应用场景', href: '#scenarios' },
  { label: '平台架构', href: '#architecture' },
  { label: '关于我们', href: '#about' },
];

/* ===== 数据产品 ===== */
export const DATA_PRODUCTS = [
  {
    icon: <FlashlightIcon />,
    title: '电网运行数据',
    desc: '输变电设备运行状态、负荷数据、电网拓扑、调度指令等核心电网数据',
    count: '42项',
    color: '#1976d2',
  },
  {
    icon: <SunnyIcon />,
    title: '新能源数据',
    desc: '风电/光伏发电功率预测、气象数据、消纳分析、并网运行数据',
    count: '28项',
    color: '#2e7d32',
  },
  {
    icon: <ThunderIcon />,
    title: '气象环境数据',
    desc: '风速风向、辐照度、温度湿度、降水预报、极端天气预警',
    count: '18项',
    color: '#0288d1',
  },
  {
    icon: <ServerIcon />,
    title: '设备状态数据',
    desc: '变压器、开关柜、换流阀等设备的运行参数、缺陷记录、检修数据',
    count: '25项',
    color: '#ed6c02',
  },
  {
    icon: <InstitutionIcon />,
    title: '电力市场数据',
    desc: '电价行情、交易量、市场供需、结算数据、碳排放配额',
    count: '15项',
    color: '#7b1fa2',
  },
  {
    icon: <PlantumlIcon />,
    title: '碳管理数据',
    desc: '碳排放核算、碳足迹追踪、绿证交易、碳中和路径分析',
    count: '21项',
    color: '#00897b',
  },
];

/* ===== 应用场景 ===== */
export const SCENARIOS = [
  {
    title: '新能源智能消纳',
    desc: '融合电网实时运行、气象预测、发电企业数据，构建"选址-并网-调控"全流程服务，提升新能源消纳率。',
    metrics: [
      { label: '装机用户数提升', value: '30%' },
      { label: '弃光率降低', value: '1%' },
      { label: '电压合格率提升', value: '10%' },
    ],
    color: '#2e7d32',
    icon: <SunnyIcon />,
  },
  {
    title: '设备智能运维',
    desc: '汇聚设备运行、缺陷记录、环境信息，为制造商提供真实运行反馈与协同研发支持。',
    metrics: [
      { label: '年节省成本', value: '1000万+' },
      { label: '设备故障率降低', value: '56%' },
      { label: '运维效率提升', value: '40%' },
    ],
    color: '#ed6c02',
    icon: <ServerIcon />,
  },
  {
    title: '电力数据赋能普惠金融',
    desc: '基于用电行为构建企业信用画像模型，将电表读数转化为信用读数，服务金融机构信贷决策。',
    metrics: [
      { label: '服务企业', value: '1000+' },
      { label: '授信金额', value: '16亿+' },
      { label: '不良率降低', value: '35%' },
    ],
    color: '#1976d2',
    icon: <InstitutionIcon />,
  },
  {
    title: '虚拟电厂协同调度',
    desc: '聚合分布式电源、储能、可控负荷，参与电网调峰调频和电力市场交易，实现源网荷储协同优化。',
    metrics: [
      { label: '调度响应时间', value: '<500ms' },
      { label: '消纳率提升', value: '≥3%' },
      { label: '参与方数量', value: '50+' },
    ],
    color: '#7b1fa2',
    icon: <FlashlightIcon />,
  },
];

/* ===== 五中心架构 ===== */
export const CENTERS = [
  {
    icon: <HardDiskStorageIcon />,
    title: '数据资源中心',
    desc: '数据采集接入、分类分级、元数据管理、数据质量控制、数据目录发布',
    color: '#1976d2',
    path: '/dashboard/data/sources',
  },
  {
    icon: <CloudIcon />,
    title: '可信计算中心',
    desc: '联邦学习、安全多方计算、可信执行环境、同态加密、差分隐私',
    color: '#2e7d32',
    path: '/dashboard/compute/tasks',
  },
  {
    icon: <LinkIcon />,
    title: '区块链存证中心',
    desc: '数据资产确权、全流程操作存证、智能合约结算、链上溯源',
    color: '#ed6c02',
    path: '/dashboard/blockchain/assets',
  },
  {
    icon: <UsergroupIcon />,
    title: '运营管理中心',
    desc: '用户管理、服务目录、计费管理、合规审计、运营监控',
    color: '#7b1fa2',
    path: '/dashboard/ops/users',
  },
  {
    icon: <LockOnIcon />,
    title: '安全管控中心',
    desc: 'DID身份认证、VC凭证管理、密钥管理、零知识证明、国密算法',
    color: '#d32f2f',
    path: '/dashboard/security/policies',
  },
];

/* ===== 技术亮点 ===== */
export const TECH_HIGHLIGHTS = [
  { icon: <VerifiedIcon />, label: '可信计算', desc: 'MPC / TEE / FL / HE', color: '#1976d2' },
  { icon: <LinkIcon />, label: '区块链存证', desc: 'FISCO BCOS 联盟链', color: '#ed6c02' },
  { icon: <LockOnIcon />, label: '国密安全', desc: 'SM2/SM3/SM4/SM9', color: '#d32f2f' },
  { icon: <ApiIcon />, label: '标准API', desc: 'RESTful + WebSocket', color: '#2e7d32' },
  { icon: <RocketIcon />, label: 'AI Agent', desc: 'DeepSeek + LangChain', color: '#7b1fa2' },
  { icon: <DashboardIcon />, label: '数据治理', desc: '元数据 + 血缘 + 质量', color: '#0288d1' },
];

/* ===== 合作伙伴 ===== */
export const PARTNERS = [
  { name: '南方电网', abbr: 'CSG', color: '#1976d2' },
  { name: '国家电网', abbr: 'SGCC', color: '#d32f2f' },
  { name: '华为', abbr: 'HW', color: '#ed6c02' },
  { name: '腾讯云', abbr: 'TC', color: '#0288d1' },
  { name: '阿里云', abbr: 'AC', color: '#ff6a00' },
  { name: '中科院', abbr: 'CAS', color: '#2e7d32' },
  { name: '清华大学', abbr: 'THU', color: '#7b1fa2' },
  { name: '中国电科', abbr: 'CETC', color: '#00897b' },
];

/* ===== 快速入口 ===== */
export const QUICK_ENTRIES = [
  {
    icon: <HardDiskStorageIcon />,
    title: '数据资源',
    desc: '浏览160+数据资产目录，即插即用，支持联邦学习与安全多方计算',
    path: '/dashboard/data/catalog',
    color: '#1976d2',
    gradient: 'linear-gradient(135deg, #1976d2, #0d47a1)',
  },
  {
    icon: <CloudIcon />,
    title: '计算服务',
    desc: '发起隐私计算任务，TEE可信执行、联邦训练、同态加密一站完成',
    path: '/dashboard/compute/tasks',
    color: '#2e7d32',
    gradient: 'linear-gradient(135deg, #2e7d32, #1b5e20)',
  },
  {
    icon: <LinkIcon />,
    title: '区块链存证',
    desc: '数据资产确权、操作全流程链上存证，智能合约自动结算',
    path: '/dashboard/blockchain/assets',
    color: '#ed6c02',
    gradient: 'linear-gradient(135deg, #ed6c02, #e65100)',
  },
];

/* ===== 新闻动态 ===== */
export const NEWS_ITEMS = [
  {
    id: 2,
    title: '南方电网数据资产登记突破1000项',
    date: '2026-02-20',
    category: '业务动态',
    summary: '平台累计完成数据资产登记1023项，涵盖电网运行、新能源、气象环境等六大品类。',
  },
  {
    id: 3,
    title: '首笔基于区块链的电力数据交易完成结算',
    date: '2026-03-08',
    category: '技术突破',
    summary: '通过智能合约实现数据交易自动结算，结算时间从3天缩短至5分钟内，交易成本降低80%。',
  },
  {
    id: 4,
    title: '平台通过等保三级与国密算法双重认证',
    date: '2026-03-22',
    category: '安全合规',
    summary: '能源可信数据空间顺利通过信息安全等级保护三级认证及国密算法合规性评估，安全能力获权威认可。',
  },
];

/* ===== 统计数据 ===== */
export const STATS = [
  { value: 160, suffix: '+', label: '数据资源接入' },
  { value: 149, suffix: '项', label: '电网数据开放' },
  { value: 125, suffix: '个', label: '应用场景规划' },
  { value: 190, suffix: '+', label: '生态主体入驻' },
];
