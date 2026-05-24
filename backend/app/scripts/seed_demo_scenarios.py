"""
四大业务场景演示数据脚本
========================
1. 电网调度优化演示
2. 新能源消纳管理演示
3. 虚拟电厂运营演示
4. 电力市场交易演示

用法：
    cd backend
    python -m app.scripts.seed_demo_scenarios
"""
import asyncio
import sys
import os
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ==================== 演示场景定义 ====================

DEMO_SCENARIOS = {
    "grid_dispatch": {
        "name": "电网调度优化演示",
        "description": "展示调度Agent如何进行负荷预测、新能源出力预测和经济调度优化",
        "agent_type": "dispatch",
        "conversations": [
            {
                "query": "请分析山东省未来24小时的电力负荷预测情况，并给出调度建议",
                "expected_response_contains": ["负荷预测", "峰荷", "谷荷", "调度建议"],
            },
            {
                "query": "当前风电出力850MW、光伏出力1200MW，预计下午光伏出力将下降，请给出优化调度方案",
                "expected_response_contains": ["储能", "削峰填谷", "新能源消纳"],
            },
            {
                "query": "分析近7天的计算任务执行情况，评估调度算法的优化效果",
                "expected_response_contains": ["计算任务", "FL", "优化效果"],
            },
        ],
    },
    "renewable_integration": {
        "name": "新能源消纳管理演示",
        "description": "展示调度Agent如何分析新能源消纳情况，提出弃风弃光优化方案",
        "agent_type": "dispatch",
        "conversations": [
            {
                "query": "分析当前新能源消纳率，风电渗透率和光伏渗透率分别是多少？",
                "expected_response_contains": ["消纳率", "渗透率", "弃风", "弃光"],
            },
            {
                "query": "今日风电预测出力1200MW，但负荷低谷只有2120MW，如何优化消纳？",
                "expected_response_contains": ["储能", "需求响应", "调峰"],
            },
        ],
    },
    "virtual_power_plant": {
        "name": "虚拟电厂运营演示",
        "description": "展示调度Agent如何聚合分布式资源参与电网调度和需求响应",
        "agent_type": "dispatch",
        "conversations": [
            {
                "query": "当前虚拟电厂聚合了哪些资源？储能容量、可调负荷和电动汽车分别有多少？",
                "expected_response_contains": ["储能", "可调负荷", "电动汽车", "聚合"],
            },
            {
                "query": "收到电网调度需求响应指令，需要削减负荷200MW，请制定执行方案",
                "expected_response_contains": ["需求响应", "削负荷", "执行方案"],
            },
        ],
    },
    "electricity_trading": {
        "name": "电力市场交易演示",
        "description": "展示交易Agent如何分析市场价格、制定报价策略和评估交易风险",
        "agent_type": "trade",
        "conversations": [
            {
                "query": "分析当前电力现货市场价格走势，峰谷价差是多少？",
                "expected_response_contains": ["价格", "峰谷", "价差"],
            },
            {
                "query": "我们是发电企业，明天有500MW电量需要在日前市场报价，请给出报价策略建议",
                "expected_response_contains": ["报价", "策略", "价格"],
            },
            {
                "query": "查看当前数据产品市场上有哪些电力交易相关的产品可以订阅？",
                "expected_response_contains": ["产品", "订阅", "市场"],
            },
        ],
    },
    "data_query": {
        "name": "数据查询演示",
        "description": "展示查询Agent如何用自然语言检索数据资产和元数据",
        "agent_type": "query",
        "conversations": [
            {
                "query": "搜索与风电相关的数据资产有哪些？",
                "expected_response_contains": ["数据资产", "风电"],
            },
            {
                "query": "当前系统中注册了哪些类型的数据源？使用了什么协议？",
                "expected_response_contains": ["数据源", "协议"],
            },
        ],
    },
    "security_patrol": {
        "name": "安全巡检演示",
        "description": "展示安全Agent如何检测威胁、分析安全态势和生成安全报告",
        "agent_type": "security",
        "conversations": [
            {
                "query": "分析当前系统安全威胁态势，有多少未解决的安全事件？",
                "expected_response_contains": ["威胁", "安全事件", "等级"],
            },
            {
                "query": "请生成一份安全态势报告，包含威胁统计和处置建议",
                "expected_response_contains": ["报告", "威胁", "建议"],
            },
        ],
    },
}


# ==================== 演示数据写入 ====================

async def seed_demo_conversations():
    """将演示对话写入数据库"""
    from app.database import init_db, close_db, AsyncSessionLocal
    from app.models.agent_conversation import AgentConversation

    print("=" * 60)
    print("  能源可信数据空间 — 四大业务场景演示数据")
    print("=" * 60)

    await init_db()

    demo_user_id = "demo_user_001"
    total_created = 0

    async with AsyncSessionLocal() as session:
        for scenario_key, scenario in DEMO_SCENARIOS.items():
            print(f"\n{'─' * 50}")
            print(f"  场景: {scenario['name']}")
            print(f"  说明: {scenario['description']}")
            print(f"  Agent: {scenario['agent_type']}")
            print(f"{'─' * 50}")

            for i, conv_data in enumerate(scenario["conversations"]):
                conv_id = f"{demo_user_id}:{scenario['agent_type']}:demo_{scenario_key}_{i}"

                # 检查是否已存在
                from sqlalchemy import select
                existing = await session.execute(
                    select(AgentConversation).where(
                        AgentConversation.conversation_id == conv_id
                    )
                )
                if existing.scalar_one_or_none():
                    print(f"  ⏭  对话已存在，跳过: {conv_data['query'][:40]}...")
                    continue

                # 创建演示对话
                now = datetime.now(timezone.utc)
                messages = [
                    {"role": "user", "content": conv_data["query"], "timestamp": now.isoformat()},
                    {
                        "role": "assistant",
                        "content": _generate_demo_response(scenario["agent_type"], conv_data),
                        "timestamp": (now + timedelta(seconds=3)).isoformat(),
                    },
                ]

                conv = AgentConversation(
                    user_id=demo_user_id,
                    agent_type=scenario["agent_type"],
                    conversation_id=conv_id,
                    messages=messages,
                    message_count=len(messages),
                )
                session.add(conv)
                total_created += 1

                print(f"  ✓ 对话 {i+1}: {conv_data['query'][:50]}...")

        await session.commit()

    print(f"\n{'=' * 60}")
    print(f"  演示数据创建完成！共创建 {total_created} 条对话记录")
    print(f"  演示用户ID: {demo_user_id}")
    print(f"{'=' * 60}")

    await close_db()


def _generate_demo_response(agent_type: str, conv_data: dict) -> str:
    """生成演示用的Agent回复（不需要真实LLM调用）"""
    responses = {
        "dispatch": {
  "负荷预测": """## 山东省24小时负荷预测分析

### 预测结果
| 时段 | 负荷(MW) | 特征 |
|------|----------|------|
| 峰荷(14:00-16:00) | 4,850 | 工业用电高峰 |
| 谷荷(03:00-05:00) | 2,120 | 夜间低谷 |
| 日均负荷 | 3,485 | 较昨日+2.3% |

### 新能源出力预测
- 风电：850MW（风速5-7m/s，中等出力）
- 光伏：1,200MW（晴天，峰值出力14:00）
- 新能源渗透率：37.2%

### 调度建议
1. **日前调度**：安排火电机组基荷运行，预留300MW调峰容量
2. **储能调度**：午间光伏富余时段充电300MWh，晚峰放电
3. **需求响应**：预通知可调负荷用户，准备200MW削峰能力
4. **安全约束**：注意鲁西断面潮流，控制联络线功率在限额内

> 预计通过优化调度可降低弃风率2.5%，节约发电成本约15万元/日""",

  "调度方案": """## 新能源出力下降应急调度方案

### 形势分析
- 当前风电：850MW，预计维持
- 当前光伏：1,200MW → 预计16:00降至600MW（下降600MW）
- 系统备用率需维持在5%以上

### 优化调度方案

**1. 储能充放电调整（优先级：高）**
- 13:00-15:00：储能充电200MW，消纳光伏富余
- 16:00-19:00：储能放电150MW，补光伏出力下降

**2. 火电出力调整**
- 增开一台300MW燃气机组（15:30并网）
- 现役火电机组提升出力200MW

**3. 需求响应启动**
- 16:00-19:00：启动工业可调负荷100MW
- 空调负荷柔性调控50MW

**4. 新能源消纳保障**
- 光伏下降期间弃光率控制在3%以内
- 风电全额消纳，不安排弃风

### 预期效果
- 系统备用率：5.8%（满足安全要求）
- 新能源消纳率：98.5%
- 调度成本增量：约8万元（低于不优化的缺电损失）""",

  "计算任务": """## 近7天计算任务执行分析

### 任务统计
| 指标 | 数值 |
|------|------|
| 总任务数 | 42 |
| FL联邦学习 | 18（42.9%） |
| MPC安全计算 | 12（28.6%） |
| TEE可信执行 | 8（19.0%） |
| DP差分隐私 | 4（9.5%） |

### 任务状态
- 已完成：35（83.3%）
- 运行中：5（11.9%）
- 失败：2（4.8%）

### 调度优化效果评估
1. **负荷预测精度**：FL模型MAPE从4.2%降至3.1%（提升26%）
2. **新能源预测**：风电预测准确率提升至92.3%
3. **调度策略优化**：通过联邦学习整合3个电厂数据，优化机组组合方案
4. **成本节约**：预计月度发电成本降低约120万元

### 改进建议
- 增加MPC任务用于多方数据协同分析
- TEE任务优先用于调度策略的机密计算
- 建议每周更新联邦学习模型参数""",
        },
        "trade": {
  "价格走势": """## 电力现货市场价格分析

### 当前市场价格
| 市场 | 均价(元/MWh) | 峰价 | 谷价 | 峰谷价差 |
|------|-------------|------|------|----------|
| 日前市场 | 385.6 | 512.3 | 198.7 | 313.6 |
| 日内市场 | 392.1 | 528.5 | 205.2 | 323.3 |
| 实时市场 | 401.8 | 545.0 | 210.5 | 334.5 |

### 价格走势分析
- **峰谷价差**：313.6元/MWh，较上周扩大8.2%
- **价格趋势**：近日价格整体上行，受气温升高影响
- **供需形势**：午间光伏出力充裕价格低谷，晚峰供应偏紧

### 市场风险提示
- 价格波动风险：近日价差扩大，套利机会增加但风险同步上升
- 电量偏差风险：中长期合同偏差考核加严，偏差超过3%需缴纳考核金
- 信用风险：关注部分购电方的信用状况变化""",
  "报价策略": """## 发电企业日前市场报价策略建议

### 报价基础分析
- 可申报电量：500MW × 24h = 12,000MWh
- 边际成本：约280元/MWh（煤电）
- 预测出清价：峰段450-520元/MWh，谷段200-250元/MWh

### 分段报价策略
| 时段 | 报价(元/MWh) | 申报比例 | 策略说明 |
|------|-------------|----------|----------|
| 00:00-06:00 | 260 | 60% | 谷段保底出清 |
| 06:00-09:00 | 350 | 80% | 早峰逐步提升 |
| 09:00-12:00 | 420 | 90% | 上午高峰 |
| 12:00-14:00 | 300 | 70% | 午间光伏冲击 |
| 14:00-18:00 | 450 | 95% | 下午高峰重点 |
| 18:00-22:00 | 480 | 100% | 晚峰全力出清 |
| 22:00-24:00 | 320 | 75% | 过渡时段 |

### 风险控制
- 设置最低出清价260元/MWh，低于成本不出清
- 峰段预留10%容量参与实时市场调频
- 建议同步在中长期市场锁定40%基础电量""",
  "产品": """## 数据产品市场查询结果

当前市场共有12个已发布的电力交易相关数据产品：

### 推荐产品
1. **电力现货价格预测数据** — 日更新，准确率92%
   - 类型：API接口 | 价格：5000元/月
   
2. **负荷预测数据服务** — 小时级更新
   - 类型：数据订阅 | 价格：8000元/月

3. **新能源出力预测** — 15分钟更新
   - 类型：API接口 | 价格：6000元/月

4. **电力市场供需分析报告** — 周报
   - 类型：报告下载 | 价格：3000元/份

5. **碳排放因子数据** — 月更新
   - 类型：数据集 | 价格：2000元/月

> 建议优先订阅「电力现货价格预测数据」和「负荷预测数据服务」，可直接接入交易决策系统。""",
        },
        "query": {
  "风电": """## 风电相关数据资产检索结果

共找到 **8** 个与风电相关的数据资产：

| 序号 | 资产名称 | 分类 | 状态 | 数据量 |
|------|----------|------|------|--------|
| 1 | 山东风电场A发电量数据 | 发电 | 已发布 | 1,250,000条 |
| 2 | 风电功率预测数据集 | 发电 | 已发布 | 856,000条 |
| 3 | 风速气象观测数据 | 气象 | 已发布 | 2,100,000条 |
| 4 | 风电机组运行状态数据 | 设备状态 | 已发布 | 520,000条 |
| 5 | 风电场并网调度数据 | 调度 | 处理中 | 380,000条 |
| 6 | 风电消纳率统计 | 市场 | 已发布 | 95,000条 |
| 7 | 风电场SCADA实时数据 | 设备状态 | 已发布 | 5,200,000条 |
| 8 | 风电检修记录 | 运维 | 已发布 | 15,000条 |

### 可视化建议
- 发电量趋势：建议使用**折线图**展示日/月发电量变化
- 风速-出力关系：建议使用**散点图**分析风速与出力的相关性
- 消纳率分析：建议使用**堆叠面积图**展示消纳与弃风比例""",
  "数据源": """## 系统已注册数据源

共注册 **6** 个数据源，使用了多种工业协议：

| 数据源名称 | 协议类型 | 状态 | 说明 |
|-----------|----------|------|------|
| 风电场SCADA接入 | Modbus | 在线 | 风电机组实时数据采集 |
| 光伏电站监控 | DLMS | 在线 | 光伏逆变器数据采集 |
| 电网调度系统 | IEC61850 | 在线 | D5000调度数据对接 |
| 气象数据服务 | HTTP | 在线 | 中国气象局API |
| 电力市场数据 | MQTT | 在线 | 现货市场出清数据 |
| 负荷监测终端 | OPC-UA | 维护中 | 工业负荷实时监测 |

### 协议分布
- Modbus: 1个（16.7%）
- DLMS: 1个（16.7%）
- IEC61850: 1个（16.7%）
- HTTP: 1个（16.7%）
- MQTT: 1个（16.7%）
- OPC-UA: 1个（16.7%）""",
        },
        "security": {
  "威胁态势": """## 系统安全威胁态势分析

### 整体安全等级：Medium（中等）

### 威胁事件统计
| 统计维度 | 分类 | 数量 |
|----------|------|------|
| 严重程度 | Critical | 2 |
| 严重程度 | High | 8 |
| 严重程度 | Medium | 23 |
| 严重程度 | Low | 45 |
| 处理状态 | 已解决 | 52 |
| 处理状态 | 调查中 | 12 |
| 处理状态 | 新发现 | 14 |
| **合计** | | **78** |

### 未解决事件（需关注）
1. **[Critical]** 检测到异常API调用模式（IP: 103.x.x.x），疑似自动化扫描
2. **[High]** 某用户连续5次访问越权数据资产，触发ABAC策略拦截
3. **[Medium]** 联邦学习梯度更新异常，可能存在模型投毒风险

### 建议措施
1. 立即封禁可疑IP地址，加强API限流策略
2. 审查越权用户的权限配置，确认是否存在权限提升
3. 对联邦学习任务增加梯度裁剪和异常检测机制
4. 建议启用国密SM2签名验证加强身份认证""",
  "安全报告": """## 能源数据空间安全态势报告

### 一、概述
报告期间：近7天 | 安全等级：Medium | 总事件数：78

### 二、威胁事件统计
- Critical: 2件（2.6%）
- High: 8件（10.3%）
- Medium: 23件（29.5%）
- Low: 45件（57.7%）

### 三、风险评估
1. **网络安全风险**：中等 — 检测到外部扫描行为，未造成实质损害
2. **数据安全风险**：低 — 未发现数据泄露事件
3. **应用安全风险**：中等 — 存在越权访问尝试
4. **隐私计算安全**：低 — 联邦学习/MPC协议运行正常

### 四、处置建议
1. 加强边界防护，更新WAF规则
2. 完善ABAC策略，收紧数据访问权限
3. 增加安全审计频率，从周审计改为日审计
4. 定期更新国密证书，确保SM2/SM3/SM4合规

### 五、趋势分析
- 威胁事件数量较上周下降12%
- Critical事件响应时间平均15分钟，达标
- 建议持续关注自动化扫描攻击趋势""",
        },
    }

    agent_responses = responses.get(agent_type, {})
    query = conv_data["query"]

    # 尝试关键词匹配
    for keyword, response in agent_responses.items():
        if keyword in query:
            return response

    # 默认回复
    return f"这是{agent_type} Agent的演示回复。查询内容：{query}\n\n系统已检索相关数据并完成分析。如需真实AI分析，请配置 DEEPSEEK_API_KEY。"


# ==================== 演示Agent配置种子 ====================

async def seed_agent_configs():
    """创建演示用的Agent配置"""
    from app.database import init_db, close_db, AsyncSessionLocal
    from app.models.agent_model import AgentConfig
    from sqlalchemy import select

    await init_db()

    configs = [
        {
            "agent_type": "query",
            "name": "数据查询Agent",
            "description": "自然语言查询能源数据资产、元数据、数据目录，支持趋势分析和可视化建议",
            "system_prompt": None,  # 使用默认
            "organization_id": "demo_org",
        },
        {
            "agent_type": "trade",
            "name": "交易结算Agent",
            "description": "电力市场价格分析、报价策略制定、供需匹配、自动结算触发",
            "system_prompt": None,
            "organization_id": "demo_org",
        },
        {
            "agent_type": "security",
            "name": "安全巡检Agent",
            "description": "安全威胁检测、合规审计、异常行为分析、自然语言安全报告生成",
            "system_prompt": None,
            "organization_id": "demo_org",
        },
        {
            "agent_type": "dispatch",
            "name": "调度优化Agent",
            "description": "负荷预测、新能源消纳分析、调度策略优化、虚拟电厂管理",
            "system_prompt": None,
            "organization_id": "demo_org",
        },
    ]

    async with AsyncSessionLocal() as session:
        for cfg in configs:
            existing = await session.execute(
                select(AgentConfig).where(AgentConfig.agent_type == cfg["agent_type"])
            )
            if existing.scalar_one_or_none():
                print(f"  ⏭  Agent配置已存在: {cfg['name']}")
                continue

            agent_config = AgentConfig(
                name=cfg["name"],
                description=cfg["description"],
                agent_type=cfg["agent_type"],
                organization_id=cfg["organization_id"],
                model_name="deepseek-chat",
                model_provider="deepseek",
                temperature=0.7,
                max_tokens=4096,
                system_prompt=cfg["system_prompt"],
                enabled=True,
            )
            session.add(agent_config)
            print(f"  ✓ 创建Agent配置: {cfg['name']}")

        await session.commit()

    await close_db()


# ==================== 主入口 ====================

async def main():
    """运行所有演示数据种子脚本"""
    print("\n" + "=" * 60)
    print("  能源可信数据空间 — 演示数据初始化")
    print("=" * 60)

    print("\n[1/2] 创建 Agent 配置...")
    await seed_agent_configs()

    print("\n[2/2] 创建演示对话场景...")
    await seed_demo_conversations()

    print("\n" + "=" * 60)
    print("  所有演示数据创建完成！")
    print("=" * 60)
    print("\n演示场景列表：")
    for key, scenario in DEMO_SCENARIOS.items():
        print(f"  • {scenario['name']} ({scenario['agent_type']} Agent)")
    print(f"\n使用 demo_user_001 用户登录即可查看演示对话历史")
    print(f"API: GET /api/v1/agent/history?agent_type=dispatch")


if __name__ == "__main__":
    asyncio.run(main())
