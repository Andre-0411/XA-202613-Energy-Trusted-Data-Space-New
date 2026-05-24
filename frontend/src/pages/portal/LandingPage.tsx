/**
 * 门户首页（Landing Page）
 * 参考南方能源可信数据空间 data.csg.cn 设计
 * 区域：导航栏 / Hero / 数据产品 / 应用场景 / 架构展示 / 合作伙伴 / Footer
 *
 * 重构后：主组件负责导航栏、数据获取、布局编排；
 * 核心区域已拆分为 6 个子组件。
 */
import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Button, Tag } from 'tdesign-react';
import {
  FlashlightIcon, CheckCircleIcon, ForwardIcon,
  MenuIcon, CloseIcon,
} from 'tdesign-icons-react';
import { getPublicDashboard } from '@/api/ops';
import { useNavigate } from 'react-router-dom';

/* 子组件 */
import HeroSection from './components/HeroSection';
import StatusSection from './components/StatusSection';
import ProductsSection from './components/ProductsSection';
import ScenariosSection from './components/ScenariosSection';
import ArchitectureSection from './components/ArchitectureSection';
import PartnersSection from './components/PartnersSection';

/* ===== 导航菜单 ===== */
const NAV_ITEMS = [
  { label: '首页', href: '#hero' },
  { label: '平台状态', href: '#status' },
  { label: 'Live Demo', href: '#demo' },
  { label: '数据服务', href: '#products' },
  { label: '应用场景', href: '#scenarios' },
  { label: '平台架构', href: '#architecture' },
  { label: '关于我们', href: '#about' },
];

/* ===== 新闻动态 ===== */
const NEWS_ITEMS = [
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

/* ===== 新闻轮播组件 ===== */
const NewsCarousel: React.FC = () => {
  const [activeIndex, setActiveIndex] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    timerRef.current = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % NEWS_ITEMS.length);
    }, 5000);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  const handleDotClick = (index: number) => {
    setActiveIndex(index);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % NEWS_ITEMS.length);
    }, 5000);
  };

  const activeNews = NEWS_ITEMS[activeIndex];

  return (
    <div className="rounded-xl bg-white border border-gray-200">
      <div className="p-4 md:p-6">
        <div className="flex items-center gap-1 mb-2">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: '#2e7d32', animation: 'pulse 2s infinite' }} />
          <span className="text-caption text-gray-500">最新动态</span>
        </div>
        <Tag>{activeNews.category}</Tag>
        <h3 className="text-base font-semibold text-gray-800 mt-2">{activeNews.title}</h3>
        <span className="text-xs text-gray-600 block mt-1">{activeNews.summary}</span>
        <div className="flex justify-between items-center mt-3">
          <span className="text-caption text-gray-500">{activeNews.date}</span>
          <div className="flex items-center gap-1">
            {NEWS_ITEMS.map((_, idx) => (
              <div
                key={idx}
                onClick={() => handleDotClick(idx)}
                className={`w-2 h-2 rounded-full cursor-pointer transition-colors ${
                  idx === activeIndex ? 'bg-blue-500' : 'bg-gray-300'
                }`}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

/* ===== 响应式 Hook ===== */
function useIsMobile(breakpoint: number = 768) {
  const [isMobile, setIsMobile] = useState(window.innerWidth < breakpoint);
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < breakpoint);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [breakpoint]);
  return isMobile;
}

/* ===== 滚动辅助 ===== */
const scrollToSection = (id: string) => {
  const el = document.getElementById(id.replace('#', ''));
  el?.scrollIntoView({ behavior: 'smooth' });
};

/* ============================================================
 * LandingPage 主组件
 * ============================================================ */
const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [dashboardData, setDashboardData] = useState<Record<string, unknown> | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);

  // 滚动检测
  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 60);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // 获取平台状态数据
  useEffect(() => {
    let mounted = true;
    setDashboardLoading(true);
    getPublicDashboard()
      .then((res) => { if (mounted) setDashboardData(res.data ?? null); })
      .catch(() => { /* 静默失败 */ })
      .finally(() => { if (mounted) setDashboardLoading(false); });
    return () => { mounted = false; };
  }, []);

  // 平台状态指标
  const platformMetrics = useMemo(() => {
    const d = dashboardData as Record<string, number> | null;
    return [
      { label: '在线节点', value: d?.online_nodes ?? 12, icon: <FlashlightIcon />, color: '#2e7d32' },
      { label: '今日计算任务', value: d?.today_tasks ?? 847, icon: <FlashlightIcon />, color: '#1976d2' },
      { label: '数据资产数', value: d?.total_assets ?? 1623, icon: <FlashlightIcon />, color: '#ed6c02' },
      { label: '系统可用率', value: `${d?.uptime ?? 99.97}%`, icon: <CheckCircleIcon />, color: '#00897b' },
    ];
  }, [dashboardData]);

  const navScrollTo = (href: string) => {
    scrollToSection(href);
    setMobileMenuOpen(false);
  };

  return (
    <div>
      {/* pulse keyframe */}
      <style>{`
        @keyframes pulse {
          0% { box-shadow: 0 0 0 0 rgba(46,125,50,0.4); }
          70% { box-shadow: 0 0 0 6px rgba(46,125,50,0); }
          100% { box-shadow: 0 0 0 0 rgba(46,125,50,0); }
        }
      `}</style>

      {/* ===== 顶部导航栏 ===== */}
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-shadow duration-300 ${scrolled ? 'bg-white shadow-md' : 'bg-transparent'}`}>
        <div className="max-w-7xl mx-auto px-4 md:px-6 flex items-center justify-between h-16">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => scrollToSection('#hero')}>
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white"><FlashlightIcon /></div>
            <h3 className={`text-base font-semibold ${scrolled ? 'text-gray-800' : 'text-white'}`}>能源可信数据空间</h3>
          </div>
          {!isMobile && (
            <div className="flex items-center gap-1">
              {NAV_ITEMS.map((item) => (
                <Button key={item.label} variant="text" onClick={() => navScrollTo(item.href)} className={scrolled ? 'text-gray-700 hover:bg-blue-50' : 'text-white/90 hover:bg-white/10'}>
                  {item.label}
                </Button>
              ))}
              <div className={`w-px h-6 mx-2 ${scrolled ? 'bg-gray-200' : 'bg-white/30'}`} />
              <Button variant="outline" onClick={() => navigate('/login')} className={scrolled ? 'border-blue-600 text-blue-600 hover:bg-blue-50' : 'border-white/50 text-white hover:bg-white/10 hover:border-white'}>登录</Button>
              <Button theme="primary" onClick={() => navigate('/login')} className={scrolled ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-white text-blue-600 hover:bg-white/90 font-semibold'}>免费试用</Button>
            </div>
          )}
          {isMobile && (
            <span className={`cursor-pointer rounded p-1 inline-flex items-center ${scrolled ? 'text-gray-700 hover:bg-gray-100' : 'text-white hover:bg-white/10'}`} onClick={() => setMobileMenuOpen(true)}>
              <MenuIcon />
            </span>
          )}
        </div>
      </nav>

      {/* 移动端抽屉 */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileMenuOpen(false)} />
          <div className="absolute right-0 top-0 bottom-0 w-72 bg-white shadow-xl p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-gray-800">菜单</h3>
              <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center" onClick={() => setMobileMenuOpen(false)}><CloseIcon /></span>
            </div>
            <div className="flex flex-col gap-1">
              {NAV_ITEMS.map((item) => (
                <div key={item.label} onClick={() => navScrollTo(item.href)} className="cursor-pointer rounded-lg px-4 py-3 text-gray-700 hover:bg-gray-100 transition-colors">{item.label}</div>
              ))}
            </div>
            <hr className="my-4 border-gray-200" />
            <div className="flex flex-col gap-2">
              <Button variant="outline" onClick={() => navigate('/login')}>登录</Button>
              <Button theme="primary" onClick={() => navigate('/login')}>免费试用</Button>
            </div>
          </div>
        </div>
      )}

      {/* ===== 核心区域（子组件） ===== */}
      <HeroSection />
      <StatusSection platformMetrics={platformMetrics} dashboardLoading={dashboardLoading} />
      <ProductsSection />
      <ScenariosSection />
      <PartnersSection />
      <ArchitectureSection />

      {/* ===== 新闻动态 ===== */}
      <section className="py-16 md:py-24 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-center">
            <div className="md:col-span-5">
              <Tag>新闻动态</Tag>
              <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mt-2">平台最新资讯</h3>
              <p className="text-sm text-gray-600 mt-2 mb-4">了解能源可信数据空间的最新发展动态、技术突破和行业合作进展。</p>
              <Button variant="outline" size="large" icon={<ForwardIcon />}>查看全部资讯</Button>
            </div>
            <div className="md:col-span-7"><NewsCarousel /></div>
          </div>
        </div>
      </section>

      {/* ===== 关于我们 ===== */}
      <section id="about" className="py-16 md:py-24 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10 items-start">
            <div>
              <Tag>关于我们</Tag>
              <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mt-2">构建能源数据信任基础设施</h3>
              <p className="text-sm text-gray-600 mt-4 mb-6">
                本平台面向新型电力系统建设需求，聚焦能源数据空间构建中的核心安全技术瓶颈，
                通过密码学、区块链、隐私计算、人工智能等技术的创新融合，实现电网能源领域数据空间的安全落地与高效应用。
              </p>
              <div className="flex flex-col gap-3">
                {[
                  '融合区块链、隐私计算、DID、AI Agent四大核心技术',
                  '覆盖电网调度、新能源消纳、虚拟电厂、电力市场四大场景',
                  '符合《数据安全法》《个人信息保护法》及电力行业标准',
                  '支持跨主体、跨区域、跨行业数据安全流通',
                ].map((item) => (
                  <div key={item} className="flex items-center gap-2">
                    <CheckCircleIcon className="text-green-500 text-lg flex-shrink-0" />
                    <span className="text-sm text-gray-600">{item}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-6">
                <h3 className="text-base font-semibold text-gray-800 mb-4">核心技术指标</h3>
                <div className="flex flex-col gap-5">
                  {[
                    { label: 'DID认证延迟', value: '<500ms', progress: 95 },
                    { label: '区块链TPS', value: '≥1000', progress: 85 },
                    { label: '联邦学习精度提升', value: '≥5%', progress: 75 },
                    { label: '结算时间', value: '<5分钟', progress: 90 },
                    { label: 'API响应P99', value: '<500ms', progress: 92 },
                  ].map((item) => (
                    <div key={item.label}>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm text-gray-600">{item.label}</span>
                        <span className="text-sm font-medium text-gray-800">{item.value}</span>
                      </div>
                      <div className="w-full h-2 bg-blue-50 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-600 rounded-full transition-all duration-500" style={{ width: `${item.progress}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== CTA 区域 ===== */}
      <section
        className="py-16 md:py-20 text-center text-white relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #0d47a1 0%, #1565c0 50%, #1976d2 100%)' }}
      >
        <div className="absolute inset-0" style={{ background: 'radial-gradient(circle at 70% 50%, rgba(255,255,255,0.08), transparent 60%)' }} />
        <div className="relative z-10 max-w-lg mx-auto px-4">
          <h3 className="text-2xl md:text-3xl font-bold mb-4">开启能源数据可信流通之旅</h3>
          <p className="text-white/80 text-sm mb-8">注册即可获得免费试用额度，体验完整的数据共享与计算能力。探索160余项数据资源、125个应用场景。</p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button theme="primary" size="large" icon={<ForwardIcon />} className="bg-white text-blue-600 font-bold px-8 py-3 text-lg hover:bg-white/90" onClick={() => navigate('/login')}>免费注册试用</Button>
            <Button variant="outline" size="large" className="border-white/50 text-white px-8 py-3 text-lg hover:border-white hover:bg-white/10" onClick={() => scrollToSection('#products')}>浏览数据目录</Button>
          </div>
        </div>
      </section>

      {/* ===== Footer ===== */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-8 mb-8">
            <div className="md:col-span-4">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white"><FlashlightIcon /></div>
                <span className="font-bold text-lg">能源可信数据空间</span>
              </div>
              <span className="text-sm text-gray-400 block">
                基于隐私计算、区块链、国密算法构建的能源行业数据共享与流通基础设施，推动能源数据要素价值释放。
              </span>
            </div>
            {[
              { title: '平台服务', items: ['数据服务', '计算服务', '存证服务', '安全服务'], onClick: () => scrollToSection('#products') },
              { title: '技术能力', items: ['联邦学习', '安全多方计算', '可信执行环境', '零知识证明'] },
              { title: '应用场景', items: ['新能源消纳', '设备运维', '普惠金融', '虚拟电厂'], onClick: () => scrollToSection('#scenarios') },
              { title: '关于我们', items: ['平台介绍', '技术架构', '合作生态', '联系我们'] },
            ].map((group) => (
              <div key={group.title} className="md:col-span-2">
                <span className="font-bold text-sm block mb-3">{group.title}</span>
                <div className="flex flex-col gap-2">
                  {group.items.map((item) => (
                    <span key={item} className="text-sm text-gray-400 cursor-pointer hover:text-white transition-colors" onClick={group.onClick}>{item}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <hr className="border-gray-700 mb-6" />
          <div className="flex flex-col md:flex-row justify-between items-center gap-3">
            <span className="text-xs text-gray-500">© 2024-2026 能源可信数据空间 Energy Trusted Data Space. All rights reserved.</span>
            <div className="flex items-center gap-4">
              {['隐私政策', '服务条款', 'API文档', '开发者中心'].map((item) => (
                <span key={item} className="text-xs text-gray-500 cursor-pointer hover:text-white transition-colors">{item}</span>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
