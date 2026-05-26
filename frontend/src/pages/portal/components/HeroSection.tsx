/**
 * HeroSection - LandingPage Hero主视觉区域
 * 深蓝渐变背景 + 主标题 + 副标题 + 统计卡片 + CTA按钮 + 微光粒子效果
 * 改进：粒子用useMemo固定、接入后端真实数据、添加平台特性标签
 */
import React, { useState, useEffect, useMemo } from 'react';
import { Button, Tag } from 'tdesign-react';
import { useNavigate } from 'react-router-dom';
import { ForwardIcon, PlayIcon } from 'tdesign-icons-react';

/* ===== 固定粒子数据（避免每次渲染随机） ===== */
const PARTICLES = Array.from({ length: 30 }, (_, i) => ({
  id: i,
  width: (i * 7 % 4) + 2,
  left: (i * 13.7) % 100,
  top: (i * 23.3) % 100,
  duration: (i * 3 % 10) + 5,
  delay: (i * 1.7) % 5,
}));

/* ============================================================
 * HeroSection 主组件
 * ============================================================ */
const HeroSection: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<{ assets: string; transactions: string; orgs: string; evidences: string }>({
    assets: '---', transactions: '---', orgs: '---', evidences: '---',
  });

  useEffect(() => {
    fetch('/api/v1/portal/stats')
      .then(r => r.json())
      .then(d => {
        setStats({
          assets: (d.data_assets_total ?? 0).toLocaleString() + '+',
          transactions: (d.transactions_total ?? 0).toLocaleString(),
          orgs: (d.organizations_total ?? 0).toLocaleString() + '+',
          evidences: (d.evidences_total ?? 0).toLocaleString() + '+',
        });
      })
      .catch(() => {});
  }, []);

  const STATS = [
    { value: stats.assets, label: '数据资产' },
    { value: stats.transactions, label: '交易笔数' },
    { value: stats.orgs, label: '接入机构' },
    { value: stats.evidences, label: '存证数量' },
  ];

  const FEATURES = ['区块链存证', '隐私计算', '国密算法', '智能合约', '联邦学习', 'AI Agent'];

  return (
    <section
      id="hero"
      className="relative min-h-screen flex items-center overflow-hidden"
      style={{ background: 'linear-gradient(135deg, #0A1628 0%, #165DFF 100%)' }}
    >
      {/* 微光粒子效果（固定位置，不闪烁） */}
      <div className="absolute inset-0 overflow-hidden">
        {PARTICLES.map((p) => (
          <div
            key={p.id}
            className="absolute rounded-full"
            style={{
              width: p.width + 'px',
              height: p.width + 'px',
              left: p.left + '%',
              top: p.top + '%',
              background: 'rgba(255,255,255,0.3)',
              animation: `particle ${p.duration}s linear infinite`,
              animationDelay: p.delay + 's',
            }}
          />
        ))}
        <style>{`
          @keyframes particle {
            0% { transform: translateY(0) translateX(0); opacity: 0; }
            20% { opacity: 0.6; }
            80% { opacity: 0.6; }
            100% { transform: translateY(-100vh) translateX(50px); opacity: 0; }
          }
        `}</style>
      </div>

      {/* 网格背景 */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: 'linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)',
          backgroundSize: '60px 60px',
        }}
      />

      <div className="relative z-10 max-w-7xl mx-auto px-4 py-20 w-full">
        <div className="text-center">
          {/* 平台特性标签 */}
          <div className="flex flex-wrap gap-2 justify-center mb-6">
            {FEATURES.map(f => (
              <Tag key={f} variant="outline" className="border-white/30 text-white/80 text-xs">{f}</Tag>
            ))}
          </div>

          {/* 主标题 */}
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-6">
            能源可信数据空间
          </h1>

          {/* 副标题 */}
          <p className="text-xl md:text-2xl text-blue-200 mb-10 max-w-3xl mx-auto">
            基于区块链与隐私计算的能源数据安全流通平台
          </p>

          {/* 统计数字卡片（接入真实数据） */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-12">
            {STATS.map((stat) => (
              <div key={stat.label} className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20 hover:bg-white/15 transition-all">
                <div className="text-3xl md:text-4xl font-bold text-white mb-2">{stat.value}</div>
                <div className="text-blue-200 text-sm">{stat.label}</div>
              </div>
            ))}
          </div>

          {/* CTA按钮 */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button
              theme="primary" size="large" icon={<ForwardIcon />}
              className="bg-white text-blue-600 font-bold px-8 py-4 text-lg hover:bg-white/90 hover:-translate-y-0.5 transition-all"
              onClick={() => navigate('/login')}
            >
              立即体验
            </Button>
            <Button
              variant="outline" size="large" icon={<PlayIcon />}
              className="border-white/40 text-white px-8 py-4 text-lg hover:border-white hover:bg-white/10"
              onClick={() => document.getElementById('products')?.scrollIntoView({ behavior: 'smooth' })}
            >
              了解更多
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
