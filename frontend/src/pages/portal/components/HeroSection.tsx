/**
 * HeroSection - LandingPage Hero主视觉区域
 * 深蓝渐变背景 + 主标题 + 副标题 + 统计卡片 + CTA按钮 + 微光粒子效果
 */
import React from 'react';
import { Button } from 'tdesign-react';
import { useNavigate } from 'react-router-dom';
import { ForwardIcon, PlayIcon } from 'tdesign-icons-react';

/* ===== 统计数据 ===== */
const STATS = [
  { value: '12,580+', label: '数据资产' },
  { value: '3,260+', label: '交易笔数' },
  { value: '156+', label: '接入机构' },
  { value: '89,000+', label: '存证数量' },
];

/* ============================================================
 * HeroSection 主组件
 * ============================================================ */
const HeroSection: React.FC = () => {
  const navigate = useNavigate();

  return (
    <section
      id="hero"
      className="relative min-h-screen flex items-center overflow-hidden"
      style={{ background: 'linear-gradient(135deg, #0A1628 0%, #165DFF 100%)' }}
    >
      {/* 微光粒子效果 */}
      <div className="absolute inset-0 overflow-hidden">
        {Array.from({ length: 30 }).map((_, i) => (
          <div
            key={i}
            className="absolute rounded-full"
            style={{
              width: Math.random() * 4 + 2 + 'px',
              height: Math.random() * 4 + 2 + 'px',
              left: Math.random() * 100 + '%',
              top: Math.random() * 100 + '%',
              background: 'rgba(255,255,255,0.3)',
              animation: `particle ${Math.random() * 10 + 5}s linear infinite`,
              animationDelay: Math.random() * 5 + 's',
            }}
          />
        ))}
        <style>{`
          @keyframes particle {
            0% { transform: translateY(0) translateX(0); opacity: 0; }
            20% { opacity: 0.6; }
            80% { opacity: 0.6; }
            100% { transform: translateY(-100vh) translateX(${Math.random() > 0.5 ? '' : '-'}${Math.random() * 100}px); opacity: 0; }
          }
        `}</style>
      </div>

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

      <div className="relative z-10 max-w-7xl mx-auto px-4 py-20 w-full">
        <div className="text-center">
          {/* 主标题 */}
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-6">
            能源可信数据空间
          </h1>
          
          {/* 副标题 */}
          <p className="text-xl md:text-2xl text-blue-200 mb-10 max-w-3xl mx-auto">
            基于区块链与隐私计算的能源数据安全流通平台
          </p>

          {/* 统计数字卡片 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-12">
            {STATS.map((stat) => (
              <div
                key={stat.label}
                className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20"
              >
                <div className="text-3xl md:text-4xl font-bold text-white mb-2">
                  {stat.value}
                </div>
                <div className="text-blue-200 text-sm">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>

          {/* CTA按钮 */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button
              theme="primary"
              size="large"
              icon={<ForwardIcon />}
              className="bg-white text-blue-600 font-bold px-8 py-4 text-lg hover:bg-white/90 hover:-translate-y-0.5 transition-all"
              onClick={() => navigate('/login')}
            >
              立即体验
            </Button>
            <Button
              variant="outline"
              size="large"
              icon={<PlayIcon />}
              className="border-white/40 text-white px-8 py-4 text-lg hover:border-white hover:bg-white/10"
              onClick={() => {
                const el = document.getElementById('products');
                el?.scrollIntoView({ behavior: 'smooth' });
              }}
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