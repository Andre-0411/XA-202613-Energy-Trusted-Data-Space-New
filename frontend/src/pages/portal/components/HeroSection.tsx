/**
 * HeroSection - LandingPage Hero主视觉区域
 * 包含：Hero主视觉 + 背景效果 + 技术亮点条 + 三大核心服务
 */
import React, { useState, useEffect, useRef } from 'react';
import { Button, Tag, Tooltip } from 'tdesign-react';
import { useNavigate } from 'react-router-dom';
import {
  FlashlightIcon, HardDiskStorageIcon, CloudIcon, LinkIcon,
  UsergroupIcon, LockOnIcon, VerifiedIcon, ApiIcon,
  RocketIcon, DashboardIcon, ForwardIcon, PlayIcon,
} from 'tdesign-icons-react';

/* ===== 五中心数据（用于圆环装饰） ===== */
const CENTERS = [
  { icon: <HardDiskStorageIcon />, title: '数据资源中心', color: '#1976d2', path: '/dashboard/data/sources' },
  { icon: <CloudIcon />, title: '可信计算中心', color: '#2e7d32', path: '/dashboard/compute/tasks' },
  { icon: <LinkIcon />, title: '区块链存证中心', color: '#ed6c02', path: '/dashboard/blockchain/assets' },
  { icon: <UsergroupIcon />, title: '运营管理中心', color: '#7b1fa2', path: '/dashboard/ops/users' },
  { icon: <LockOnIcon />, title: '安全管控中心', color: '#d32f2f', path: '/dashboard/security/policies' },
];

/* ===== 技术亮点 ===== */
const TECH_HIGHLIGHTS = [
  { icon: <VerifiedIcon />, label: '可信计算', desc: 'MPC / TEE / FL / HE', color: '#1976d2' },
  { icon: <LinkIcon />, label: '区块链存证', desc: 'FISCO BCOS 联盟链', color: '#ed6c02' },
  { icon: <LockOnIcon />, label: '国密安全', desc: 'SM2/SM3/SM4/SM9', color: '#d32f2f' },
  { icon: <ApiIcon />, label: '标准API', desc: 'RESTful + WebSocket', color: '#2e7d32' },
  { icon: <RocketIcon />, label: 'AI Agent', desc: 'DeepSeek + LangChain', color: '#7b1fa2' },
  { icon: <DashboardIcon />, label: '数据治理', desc: '元数据 + 血缘 + 质量', color: '#0288d1' },
];

/* ===== 快速入口 ===== */
const QUICK_ENTRIES = [
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

/* ===== 统计数据 ===== */
const STATS = [
  { value: 160, suffix: '+', label: '数据资源接入' },
  { value: 149, suffix: '项', label: '电网数据开放' },
  { value: 125, suffix: '个', label: '应用场景规划' },
  { value: 190, suffix: '+', label: '生态主体入驻' },
];

/* ===== 动画计数器 Hook ===== */
function useCountUp(end: number, duration: number = 2000) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const started = useRef(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started.current) {
          started.current = true;
          const start = performance.now();
          const animate = (now: number) => {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setCount(Math.round(eased * end));
            if (progress < 1) requestAnimationFrame(animate);
          };
          requestAnimationFrame(animate);
        }
      },
      { threshold: 0.3 },
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [end, duration]);

  return { count, ref };
}

/* ===== 计数器组件 ===== */
const AnimatedStat: React.FC<{ value: number; suffix: string; label: string }> = ({ value, suffix, label }) => {
  const { count, ref } = useCountUp(value);
  return (
    <div ref={ref} className="text-center">
      <span className="text-3xl font-extrabold text-gray-900">{count}{suffix}</span>
      <span className="text-xs text-gray-600 block mt-1">{label}</span>
    </div>
  );
};

/* ===== 滚动辅助 ===== */
const scrollToSection = (id: string) => {
  const el = document.getElementById(id.replace('#', ''));
  el?.scrollIntoView({ behavior: 'smooth' });
};

/* ============================================================
 * HeroSection 主组件
 * ============================================================ */
const HeroSection: React.FC = () => {
  const navigate = useNavigate();

  return (
    <>
      {/* ===== Hero 区域 ===== */}
      <section
        id="hero"
        className="relative min-h-screen md:min-h-[92vh] flex items-center overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #0a1628 0%, #0d2137 30%, #0d47a1 70%, #1565c0 100%)' }}
      >
        {/* 背景光晕 */}
        <div
          className="absolute inset-0"
          style={{
            background: `
              radial-gradient(ellipse 80% 50% at 50% -20%, rgba(25, 118, 210, 0.3), transparent),
              radial-gradient(ellipse 60% 40% at 80% 50%, rgba(46, 125, 50, 0.15), transparent),
              radial-gradient(ellipse 40% 30% at 20% 80%, rgba(2, 136, 209, 0.2), transparent)
            `,
          }}
        />
        {/* 网格背景 */}
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
            `,
            backgroundSize: '60px 60px',
          }}
        />

        <div className="relative z-10 max-w-7xl mx-auto px-4 pt-20 md:pt-24 pb-12 md:pb-16 w-full">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-center">
            <div className="md:col-span-7">
              <h1 className="font-extrabold text-white leading-tight mb-4 text-4xl sm:text-5xl md:text-6xl">
                能源可信数据空间
              </h1>
              <h4 className="text-white/70 font-normal mb-4 text-xl md:text-2xl">
                Energy Trusted Data Space
              </h4>
              <p className="text-white/80 text-sm md:text-base mb-4 max-w-xl">
                基于隐私计算、区块链、国密算法构建的能源行业数据共享与流通基础设施。
                实现&quot;数据可用不可见、可控可计量、可溯可审计&quot;，推动能源数据要素价值释放。
              </p>
              <p className="text-white/60 text-sm mb-6">连接数据供需 · 共创协同价值</p>
              <div className="flex flex-col sm:flex-row gap-3">
                <Button
                  theme="primary"
                  size="large"
                  icon={<ForwardIcon />}
                  className="bg-white text-blue-600 font-bold px-6 py-3 text-base hover:bg-white/90 hover:-translate-y-0.5 transition-all"
                  onClick={() => navigate('/login')}
                >
                  立即体验
                </Button>
                <Button
                  variant="outline"
                  size="large"
                  icon={<PlayIcon />}
                  className="border-white/40 text-white px-6 py-3 text-base hover:border-white hover:bg-white/10"
                  onClick={() => scrollToSection('#architecture')}
                >
                  了解架构
                </Button>
              </div>
            </div>

            {/* 右侧装饰圆环 */}
            <div className="hidden md:flex md:col-span-5 justify-center">
              <div className="relative w-[380px] h-[380px]">
                <div
                  className="absolute inset-0 rounded-full"
                  style={{ border: '2px solid rgba(66,165,245,0.2)', animation: 'spin 20s linear infinite' }}
                />
                <div className="absolute inset-8 rounded-full" style={{ border: '2px solid rgba(46,125,50,0.15)' }} />
                <div className="absolute inset-16 rounded-full" style={{ border: '2px solid rgba(2,136,209,0.1)' }} />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="flex flex-col items-center gap-1">
                    <FlashlightIcon className="text-blue-400 text-3xl" />
                    <span className="text-xs text-white/60">可信 · 安全 · 高效</span>
                  </div>
                </div>
                {CENTERS.map((c, i) => {
                  const angle = (i * 72 - 90) * (Math.PI / 180);
                  const r = 160;
                  const x = 190 + r * Math.cos(angle) - 24;
                  const y = 190 + r * Math.sin(angle) - 24;
                  return (
                    <Tooltip key={c.title} content={c.title} placement="top">
                      <div
                        className="absolute w-12 h-12 rounded-full flex items-center justify-center cursor-pointer transition-all duration-300 hover:scale-125"
                        style={{ left: x, top: y, backgroundColor: `${c.color}33`, color: c.color, border: `2px solid ${c.color}66` }}
                        onClick={() => navigate(c.path)}
                      >
                        {c.icon}
                      </div>
                    </Tooltip>
                  );
                })}
                <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
              </div>
            </div>
          </div>

          {/* 底部统计计数器 */}
          <div className="mt-10 md:mt-16">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 justify-items-center">
              {STATS.map((s) => (
                <div key={s.label}>
                  <AnimatedStat value={s.value} suffix={s.suffix} label={s.label} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ===== 技术亮点条 ===== */}
      <div className="max-w-7xl mx-auto px-4 -mt-8 relative z-10">
        <div
          className="rounded-xl bg-white border border-gray-200 shadow-md p-4 md:p-6"
          style={{ background: 'linear-gradient(135deg, #fff 0%, #f8fbff 100%)' }}
        >
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-4">
            {TECH_HIGHLIGHTS.map((h) => (
              <div key={h.label} className="flex flex-col items-center gap-1">
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center text-lg"
                  style={{ backgroundColor: `${h.color}15`, color: h.color }}
                >
                  {h.icon}
                </div>
                <span className="text-xs text-gray-700 font-medium">{h.label}</span>
                <span className="text-xs text-gray-500 text-center">{h.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ===== 三大核心服务 ===== */}
      <section className="py-12 md:py-16">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-10">
            <Tag>快速开始</Tag>
            <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mt-2">三大核心服务</h3>
            <p className="text-sm text-gray-600 mt-2 max-w-xl mx-auto">
              数据资源浏览、隐私计算服务、区块链存证，一站式满足您的数据需求
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {QUICK_ENTRIES.map((entry) => (
              <div
                key={entry.title}
                className="rounded-xl bg-white border border-gray-200 cursor-pointer transition-all duration-300 relative overflow-hidden group hover:-translate-y-2 hover:shadow-lg"
                style={{ borderColor: `${entry.color}26` }}
                onClick={() => navigate(entry.path)}
              >
                <div className="absolute top-0 left-0 right-0 h-1" style={{ background: entry.gradient }} />
                <div className="p-6">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center text-xl mb-4 transition-all duration-300 group-hover:text-white"
                    style={{ backgroundColor: `${entry.color}18`, color: entry.color }}
                  >
                    {entry.icon}
                  </div>
                  <h2 className="text-xl font-semibold text-gray-800 mb-2">{entry.title}</h2>
                  <span className="text-sm text-gray-600 block mb-4">{entry.desc}</span>
                  <Button
                    variant="outline"
                    size="large"
                    icon={<ForwardIcon />}
                    style={{ borderColor: entry.color, color: entry.color }}
                    className="font-semibold hover:text-white"
                  >
                    立即访问
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
};

export default HeroSection;
