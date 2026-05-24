/**
 * BackgroundEffects - 登录页左侧品牌面板背景动效
 * 六角形网格 + 粒子流动动画
 */
import React, { useEffect, useRef } from 'react';
import { FlashlightIcon } from 'tdesign-icons-react';

/* ============================================================
 * BackgroundEffects 主组件
 * ============================================================ */
const BackgroundEffects: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    const W = 600;
    const H = 900;
    canvas.width = W;
    canvas.height = H;

    interface Node { x: number; y: number; r: number; phase: number; speed: number; }
    const nodes: Node[] = [];
    const hexRadius = 26;
    const rows = 10;
    const cols = 5;
    const xSpacing = 90;
    const ySpacing = 78;
    const offsetX = (W - (cols - 1) * xSpacing) / 2;
    const offsetY = (H - (rows - 1) * ySpacing) / 2;

    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const x = offsetX + col * xSpacing + (row % 2 ? xSpacing / 2 : 0);
        const y = offsetY + row * ySpacing;
        nodes.push({ x, y, r: hexRadius, phase: Math.random() * Math.PI * 2, speed: 0.3 + Math.random() * 0.5 });
      }
    }

    interface Particle { sx: number; sy: number; tx: number; ty: number; t: number; speed: number; color: string; }
    const particles: Particle[] = [];
    const colors = ['#4fc3f7', '#29b6f6', '#00bcd4', '#26c6da', '#4dd0e1', '#80deea'];
    const spawnParticle = () => {
      if (particles.length > 25) return;
      const a = nodes[Math.floor(Math.random() * nodes.length)];
      const b = nodes[Math.floor(Math.random() * nodes.length)];
      if (a === b) return;
      particles.push({ sx: a.x, sy: a.y, tx: b.x, ty: b.y, t: 0, speed: 0.004 + Math.random() * 0.008, color: colors[Math.floor(Math.random() * colors.length)] });
    };

    const drawHex = (cx: number, cy: number, r: number, alpha: number) => {
      ctx.beginPath();
      for (let i = 0; i < 6; i++) {
        const angle = (Math.PI / 3) * i - Math.PI / 6;
        const px = cx + r * Math.cos(angle);
        const py = cy + r * Math.sin(angle);
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.strokeStyle = `rgba(79, 195, 247, ${0.12 + alpha * 0.2})`;
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.fillStyle = `rgba(79, 195, 247, ${0.02 + alpha * 0.04})`;
      ctx.fill();
    };

    const drawEdge = (n1: Node, n2: Node, alpha: number) => {
      ctx.beginPath();
      ctx.moveTo(n1.x, n1.y);
      ctx.lineTo(n2.x, n2.y);
      ctx.strokeStyle = `rgba(79, 195, 247, ${0.03 + alpha * 0.06})`;
      ctx.lineWidth = 0.5;
      ctx.stroke();
    };

    let time = 0;
    const animate = () => {
      time += 1;
      ctx.clearRect(0, 0, W, H);

      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < xSpacing * 1.5) {
            drawEdge(nodes[i], nodes[j], (Math.sin(time * 0.015 + nodes[i].phase) * 0.5 + 0.5) * 0.5);
          }
        }
      }

      for (const n of nodes) {
        const pulse = Math.sin(time * 0.02 * n.speed + n.phase) * 0.5 + 0.5;
        drawHex(n.x, n.y, n.r, pulse);
        ctx.beginPath();
        ctx.arc(n.x, n.y, 2 + pulse * 1.5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(79, 195, 247, ${0.25 + pulse * 0.4})`;
        ctx.fill();
      }

      if (time % 50 === 0) spawnParticle();
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.t += p.speed;
        if (p.t >= 1) { particles.splice(i, 1); continue; }
        const x = p.sx + (p.tx - p.sx) * p.t;
        const y = p.sy + (p.ty - p.sy) * p.t;
        const alpha = p.t < 0.1 ? p.t / 0.1 : p.t > 0.85 ? (1 - p.t) / 0.15 : 1;
        ctx.beginPath();
        ctx.arc(x, y, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = p.color.replace(')', `, ${alpha * 0.8})`).replace('rgb', 'rgba');
        ctx.fill();
      }

      animId = requestAnimationFrame(animate);
    };
    animate();
    return () => cancelAnimationFrame(animId);
  }, []);

  return (
    <div
      className="relative hidden h-full w-[42%] flex-col items-center justify-center overflow-hidden lg:flex"
      style={{ background: 'linear-gradient(180deg, #0a1628 0%, #0d2137 50%, #0b1929 100%)' }}
    >
      <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" style={{ opacity: 0.5 }} />

      {/* 品牌内容 */}
      <div className="relative z-10 flex flex-col items-center px-12 text-center">
        <div
          className="mb-8 flex h-16 w-16 items-center justify-center rounded-2xl shadow-2xl"
          style={{ background: 'linear-gradient(135deg, #1976d2, #42a5f5)', boxShadow: '0 8px 32px rgba(25,118,210,0.5)' }}
        >
          <FlashlightIcon className="text-3xl text-white" />
        </div>
        <h2 className="mb-3 text-2xl font-bold tracking-wide text-white">能源可信数据空间</h2>
        <p className="mb-10 text-sm leading-relaxed text-white/50">Energy Trusted Data Space</p>

        {/* 特性列表 */}
        <div className="flex flex-col gap-5 text-left">
          {[
            { icon: '🔐', title: '多方安全协同', desc: '隐私保护下的数据共享与协作' },
            { icon: '🔗', title: '区块链存证', desc: '不可篡改的数据流转记录' },
            { icon: '📊', title: '可信计算', desc: '联邦学习与安全多方计算' },
          ].map((item) => (
            <div key={item.title} className="flex items-start gap-3">
              <span className="mt-0.5 text-xl">{item.icon}</span>
              <div>
                <p className="text-sm font-medium text-white/80">{item.title}</p>
                <p className="text-xs text-white/40">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 底部版权 */}
      <div className="absolute bottom-8 z-10 text-center">
        <p className="text-xs text-white/30">&copy; {new Date().getFullYear()} Energy TDS. All Rights Reserved</p>
      </div>
    </div>
  );
};

export default BackgroundEffects;
