/**
 * PartnersSection - 合作伙伴生态区域
 */
import React from 'react';
import { Tag } from 'tdesign-react';

/* ===== 合作伙伴 ===== */
const PARTNERS = [
  { name: '南方电网', abbr: 'CSG', color: '#1976d2' },
  { name: '国家电网', abbr: 'SGCC', color: '#d32f2f' },
  { name: '华为', abbr: 'HW', color: '#ed6c02' },
  { name: '腾讯云', abbr: 'TC', color: '#0288d1' },
  { name: '阿里云', abbr: 'AC', color: '#ff6a00' },
  { name: '中科院', abbr: 'CAS', color: '#2e7d32' },
  { name: '清华大学', abbr: 'THU', color: '#7b1fa2' },
  { name: '中国电科', abbr: 'CETC', color: '#00897b' },
];

/* ============================================================
 * PartnersSection 主组件
 * ============================================================ */
const PartnersSection: React.FC = () => {
  return (
    <section className="py-12 md:py-16">
      <div className="max-w-7xl mx-auto px-4">
        <div className="text-center mb-10">
          <Tag>生态伙伴</Tag>
          <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mt-2">合作伙伴生态</h3>
          <p className="text-sm text-gray-600 mt-2 max-w-xl mx-auto">
            联合电网企业、科研院所、云服务商等多方力量，共建能源数据可信流通基础设施
          </p>
        </div>

        <div
          className="rounded-xl bg-white border border-gray-200 shadow-sm p-6 md:p-8"
          style={{ backgroundColor: 'rgba(248, 251, 255, 0.5)' }}
        >
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-4 gap-6 justify-items-center">
            {PARTNERS.map((partner) => (
              <div
                key={partner.name}
                className="flex flex-col items-center gap-2 p-4 rounded-lg cursor-pointer transition-all duration-300 hover:-translate-y-0.5 group"
              >
                <div
                  className="w-16 h-16 rounded-2xl flex items-center justify-center border-2 border-gray-200 transition-all duration-300 group-hover:border-current group-hover:shadow-md"
                  style={{ color: partner.color }}
                >
                  <h3 className="text-lg font-bold">{partner.abbr}</h3>
                </div>
                <span className="text-xs text-gray-600">{partner.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default PartnersSection;
