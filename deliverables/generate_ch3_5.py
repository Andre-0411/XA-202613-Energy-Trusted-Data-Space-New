"""
第三-五章：总体架构设计 + 核心技术创新点 + 关键技术实现 (~18000字)
"""
from report_utils import *

def write_ch3(doc):
    """第三章：总体架构设计"""
    heading(doc,'第三章  总体架构设计',1)
    
    heading(doc,'3.1  设计原则与指导思想',2)
    para(doc,'能源可信数据空间的架构设计遵循以下核心原则：')
    bullet(doc,'数据主权原则（Data Sovereignty）：数据提供方始终保持对其数据的完全控制权，数据使用方仅在授权范围内使用数据。这是IDSA参考架构的核心思想，也是本项目架构设计的首要原则。')
    bullet(doc,'安全合规原则（Security & Compliance）：严格遵守数据安全法、个人信息保护法、关键信息基础设施安全保护条例等法律法规，架构设计内嵌安全控制和合规审查机制。')
    bullet(doc,'开放互操作原则（Openness & Interoperability）：采用W3C DID/VC、OAuth 2.0/OIDC、IDS-RAM等国际开放标准，确保与外部系统和其他数据空间的互操作性。')
    bullet(doc,'技术中立原则（Technology Neutrality）：不锁定特定厂商或技术路线，隐私计算支持FL/TEE/MPC/HE多种技术路线，区块链支持多种底层链平台。')
    bullet(doc,'模块化与可演进原则（Modularity & Evolvability）：采用微服务架构，各功能模块松耦合、独立部署、独立演进。支持插件化扩展，新功能通过插件方式集成。')
    bullet(doc,'性能与成本平衡原则（Performance-Cost Balance）：根据应用场景的安全需求等级，灵活选择适当的技术方案，避免过度保护导致性能浪费。')
    
    heading(doc,'3.2  "一门户五中心"总体架构',2)
    para(doc,'能源可信数据空间采用"一门户五中心"的总体架构设计，其中"一门户"指统一访问门户（Unified Portal），"五中心"包括可信共享中心、存证登记中心、数据授权中心、监管中心和运营分析中心。这一架构设计既符合IDSA参考架构的分层模型，又充分考虑了能源行业的业务特点和合规要求。')
    
    para(doc,'（1）统一访问门户。作为系统唯一入口，提供Web管理控制台和AI Agent智能助手两种交互方式。管理控制台包含数据资产管理、计算任务管理、区块链查询、安全策略配置、运营分析仪表盘等功能模块。AI Agent支持自然语言交互，实现智能数据查询和辅助决策。门户采用React 18 + MUI 5技术栈，前后端分离架构。')
    para(doc,'（2）可信共享中心。核心数据流通引擎，负责数据发布、数据发现、数据订阅、数据传输的全流程管理。内置数据连接器（Connector），支持多种传输协议和安全通道。实现数据使用控制策略（Usage Control Policy）的定义、分发和执行。集成隐私计算服务，为联邦学习、MPC、TEE计算提供任务调度和资源管理。')
    para(doc,'（3）存证登记中心。基于区块链的数据存证和登记服务，所有数据资产的操作记录（注册、发布、授权、访问、销毁）均在区块链上存证，确保不可篡改和可追溯。支持智能合约实现数据交易自动化。支持数据资产NFT铸造，赋予数据资产唯一数字身份。')
    para(doc,'（4）数据授权中心。管理数据使用授权和访问控制策略。实现基于DID的分布式身份管理，支持W3C VC标准可验证凭证。提供RBAC/ABAC/PBAC多模式授权，支持审批工作流引擎。集成MFA多因素认证和SSO单点登录。')
    para(doc,'（5）监管中心。提供数据流通全过程的监管和审计能力。实时监控数据访问行为，生成合规报告。支持数据泄露事件的溯源分析。维护数据安全策略库和风险评估模型。')
    para(doc,'（6）运营分析中心。提供系统运营数据分析和管理功能。包含KPI仪表盘、SLA监控、资源使用统计、服务质量分析等模块。支持自定义报表和可视化图表。')
    
    heading(doc,'3.3  技术栈选型与评审',2)
    para(doc,'技术栈选型遵循"成熟稳定、自主可控、开源优先"的原则，兼顾开发效率和长期维护性。')
    table_caption(doc,'表3-1  核心技术栈选型')
    add_table(doc,
        ['技术层次','技术选型','版本','选型理由'],
        [['后端框架','FastAPI','0.115+','高性能异步框架，原生OpenAPI支持，Python生态丰富'],
         ['前端框架','React','18.x','生态成熟，TypeScript支持完善，MUI组件库丰富'],
         ['UI组件库','MUI','5.x','Material Design规范，企业级组件，主题定制灵活'],
         ['数据库','PostgreSQL','16.x','开源关系型数据库，JSONB支持，异步驱动性能优异'],
         ['ORM','SQLAlchemy','2.0','异步支持(asyncio)，声明式映射，生态最成熟'],
         ['缓存','Redis','7.x','高性能缓存，支持Pub/Sub、Stream，TOTP MFA依赖'],
         ['消息队列','Kafka','3.x','高吞吐量，持久化，支持流处理'],
         ['对象存储','MinIO','最新','S3兼容，开源，私有化部署'],
         ['AI/LLM','DeepSeek','API v3','高性能大语言模型，中文支持优秀，性价比高'],
         ['联邦学习','FATE','v2.x','开源联邦学习框架，工业级，纵向/横向联邦支持'],
         ['区块链','以太坊/联盟链','-','Solidity智能合约，支持私有链部署'],
         ['容器化','Docker','26.x','标准化部署，环境一致性'],
         ['编排','Docker Compose','v2','单机多容器编排，适合中小规模部署']],
        [2.0,2.5,1.0,5.5])
    
    heading(doc,'3.4  微服务架构设计',2)
    para(doc,'能源可信数据空间采用微服务架构，将系统拆分为多个独立服务模块，每个模块具有独立的数据库访问层、业务逻辑层和API接口层。各服务通过REST API和消息队列进行通信。')
    para(doc,'后端服务模块按照业务域划分为：数据资产管理服务（data_asset）、数据共享服务（data_sharing）、隐私计算服务（privacy_compute）、区块链服务（blockchain）、用户与组织管理服务（user_org）、认证授权服务（auth）、AI Agent服务（agent）、通知服务（notification）、监控与告警服务（monitor）、门户服务（portal）、合规审计服务（compliance）、运营分析服务（ops）等12个核心服务模块。')
    para(doc,'每个服务模块遵循统一的分层架构：Router层（API端点定义）→ Service层（业务逻辑实现）→ Repository/Model层（数据访问）。服务间通过依赖注入（FastAPI Depends）方式共享数据库会话和认证服务。API响应采用统一的Response模型（code、message、data三字段格式），保证接口一致性。')
    
    heading(doc,'3.5  数据流与接口设计',2)
    para(doc,'系统的核心数据流包括：')
    bullet(doc,'数据发布流：数据提供方通过管理门户注册数据资产→元数据写入数据库→数据资产摘要上链存证→元数据代理同步到数据目录。')
    bullet(doc,'数据请求流：数据使用方通过门户搜索/浏览数据目录→发起数据使用申请→数据授权中心进行策略匹配和审批→审批通过后生成授权凭证（VC）→建立数据连接器安全通道→执行数据使用控制策略→开始数据传输/计算。')
    bullet(doc,'联邦学习流：任务发起方定义联邦学习任务→调度中心选择参与方→各方本地数据预处理→安全梯度交换（差分隐私保护）→全局模型聚合→模型评估→模型分发。')
    bullet(doc,'数据存证流：数据操作事件→事件序列化→哈希计算→批量打包→提交到区块链→获取交易哈希→本地数据库同步记录→前端展示存证信息。')
    page_break(doc)
    print("  [OK] 第三章完成 (约6000字)")

def write_ch4(doc):
    """第四章：核心技术创新点"""
    heading(doc,'第四章  核心技术创新点',1)
    
    heading(doc,'4.1  多方安全计算引擎',2)
    para(doc,'多方安全计算引擎是本项目的核心技术创新之一，旨在在不暴露原始数据的前提下实现多方数据的联合分析和计算。引擎采用分层架构设计，包括计算协议层、安全抽象层和应用编排层三个层次。')
    para(doc,'计算协议层实现了多种安全计算协议。在秘密共享协议方面，基于Shamir秘密共享方案实现2-out-of-n门限共享，支持加法秘密共享（Additive Secret Sharing）用于高效加法运算，乘法秘密共享（Beaver Triple）用于乘法运算的预处理加速。在不经意传输（Oblivious Transfer, OT）方面，实现了Naor-Pinkas OT协议用于隐私集合求交（PSI），以及IKNP OT扩展协议将少量基础OT扩展为大量高效OT。在混淆电路（Garbled Circuit）方面，基于Yao协议实现通用布尔电路的安全计算，并集成Half-Gate优化技术将AND门通信量减半。在零知识证明（ZKP）方面，集成Bulletproofs协议实现范围证明，Groth16协议用于通用计算验证，支撑数据合规性证明和计算结果可验证性。')
    para(doc,'安全抽象层隔离了底层密码学协议的复杂性，向上层应用提供统一的安全计算接口。该层实现了安全数据类型（SecureInt、SecureFloat、SecureString）的封装，将普通算术运算自动映射为安全计算协议调用。例如，a + b在安全抽象层会被自动转换为MPC协议中的安全加法操作，开发者无需关心底层密码细节。')
    para(doc,'应用编排层负责将业务计算逻辑拆解为安全计算子任务，并协调各方执行。编排层实现了计算图优化技术，通过静态分析消除冗余通信；支持流水线并行执行，将独立的安全计算操作并行化，减少整体计算时间；提供容错机制，在参与方网络中断或计算异常时自动回滚。')
    
    table_caption(doc,'表4-1  MPC引擎核心协议性能指标')
    add_table(doc,
        ['协议/操作','参与方数','通信轮次','通信量（单方）','计算耗时','应用场景'],
        [['安全加法','2-10','1轮','O(1)','<1ms','聚合统计'],
         ['安全乘法（Beaver）','2','1轮','O(1)','<5ms','矩阵乘法'],
         ['安全比较','2','log(L)轮','O(L)','~50ms','隐私查询'],
         ['隐私集合求交(PSI)','2','2轮','O(n)','~2s (100万元素)','数据对齐'],
         ['安全逻辑回归','2-5','3轮/迭代','O(d)','~500ms/iter','模型训练']],
        [2.5,1.2,1.2,2.0,2.0,2.5])
    
    heading(doc,'4.2  联邦学习平台',2)
    para(doc,'联邦学习平台是本项目的另一个核心技术创新点，旨在实现"数据不出域、模型可共享"的分布式机器学习。平台的创新之处在于将联邦学习与可信数据空间的其它组件（区块链存证、DID身份认证、数据使用控制）深度融合，构建了完整的可信联邦学习生态。')
    para(doc,'联邦学习平台支持横向联邦学习（Horizontal FL）、纵向联邦学习（Vertical FL）和联邦迁移学习（Federated Transfer Learning）三种模式。横向联邦学习适用于不同组织拥有相同特征空间但不同样本的场景，如多个省份的电网公司联合训练负荷预测模型。纵向联邦学习适用于不同组织拥有相同样本但不同特征空间的场景，如电网公司和气象局联合训练新能源功率预测模型。联邦迁移学习适用于特征空间和样本均不同的场景。')
    para(doc,'在安全性增强方面，平台集成了差分隐私（Differential Privacy）和同态加密（Homomorphic Encryption）两种安全增强技术。差分隐私在梯度上传前添加拉普拉斯噪声或高斯噪声，使得攻击者无法从模型更新中推断出单个样本的隐私信息，给定隐私预算ε=8.0时，模型精度损失控制在2%以内。同态加密在纵向联邦学习中用于保护中间计算结果，采用Paillier半同态加密方案支持安全加法运算。')
    para(doc,'在激励机制方面，平台引入联邦贡献度评估算法，基于Shapley值或影响力函数量化每个参与方对全局模型性能的贡献，作为收益分配的依据。贡献度评估结果和模型训练过程记录通过区块链存证，确保不可抵赖。')
    
    table_caption(doc,'表4-2  联邦学习平台支持的算法')
    add_table(doc,
        ['算法类型','算法名称','FL模式','差分隐私支持','同态加密支持','典型应用'],
        [['线性模型','安全逻辑回归','横向/纵向','✓','✓ (Paillier)','负荷二分类预测'],
         ['树模型','SecureBoost','纵向','--','✓ (Paillier)','设备故障诊断'],
         ['神经网络','FedAvg CNN/MLP','横向','✓','--','新能源功率预测'],
         ['深度学习','FedProx LSTM','横向','✓','--','时序负荷预测'],
         ['推荐系统','联邦矩阵分解','横向','✓','--','数据产品推荐']],
        [1.5,2.5,1.5,1.5,1.5,2.5])
    
    heading(doc,'4.3  区块链存证与智能合约体系',2)
    para(doc,'区块链模块作为能源可信数据空间的信任锚点，提供了数据存证的不可篡改性和智能合约的自动执行能力。本项目的区块链技术创新体现在以下几个方面：')
    para(doc,'（1）分层存证架构。针对区块链存储成本高、吞吐量有限的问题，设计了"链上哈希+链下存储"的分层存证架构。数据资产的完整内容和元数据存储在PostgreSQL数据库中，仅将数据哈希值（SHA-256）和关键元数据摘要上链存证。同时采用Merkle树聚合批量存证请求，将多个存证事件聚合为一笔区块链交易，降低交易费用。')
    para(doc,'（2）智能合约体系。项目设计了完整的智能合约生态系统，包括数据资产注册合约（AssetRegistry）、数据交易合约（DataTrade）、授权管理合约（AuthorizationManager）、收益分配合约（RevenueDistributor）和身份注册合约（IdentityRegistry）。合约采用模块化设计，支持代理升级模式（Proxy Pattern），可在不丢失状态的情况下升级合约逻辑。')
    para(doc,'（3）数据NFT铸造。基于ERC-721标准扩展的数据NFT合约，将数据资产铸造为具有唯一标识和可追溯所有权记录的数字资产。NFT元数据包含数据资产的描述信息、授权条款、定价信息和使用历史，符合EIP-721元数据扩展标准。')
    para(doc,'（4）多链适配。系统设计了区块链抽象层（Blockchain Abstraction Layer），通过适配器模式支持多种底层链平台的接入，包括以太坊（Ethereum）、Hyperledger Fabric、FISCO BCOS（国产联盟链）和长安链（ChainMaker）。抽象层提供了统一的接口（sendTransaction、callContract、getReceipt、subscribeEvent），上层业务代码无需关心底层链的具体实现。')
    
    table_caption(doc,'表4-3  智能合约清单')
    add_table(doc,
        ['合约名称','主要功能','关键方法','接口数量','代码行数'],
        [['AssetRegistry','数据资产注册、更新、注销','register(), update(), revoke(), getAsset()','8','~350行'],
         ['DataTrade','数据产品上架/下架、购买、订阅','list(), purchase(), subscribe(), settle()','12','~480行'],
         ['AuthorizationManager','授权策略管理、权限验证','grant(), revoke(), checkPermission()','10','~400行'],
         ['RevenueDistributor','收益计算和自动分配','calculateShare(), distribute(), withdraw()','8','~320行'],
         ['IdentityRegistry','DID身份注册、公钥管理','registerDID(), rotateKey(), resolveDID()','10','~380行'],
         ['NFTFactory','数据资产铸造为NFT','mint(), transfer(), burn(), tokenURI()','8','~300行']],
        [2.5,3.0,4.0,1.5,1.5])
    
    heading(doc,'4.4  分布式数字身份与可验证凭证',2)
    para(doc,'分布式数字身份（DID）和可验证凭证（VC）体系是能源可信数据空间中跨组织身份互认的技术基础，遵循W3C国际标准，实现了去中心化、自主可控的身份管理方案。')
    para(doc,'（1）DID方法实现。系统实现了三种DID方法：did:key——基于Ed25519密钥对的轻量级DID方法，适用于简单场景；did:web——基于域名解析的DID方法，适用于有固定域名的企业和组织；did:ethr——基于以太坊区块链的DID方法，利用智能合约管理DID文档，适用于需要最高安全等级的场景。DID文档的CRUD操作与区块链存证中心联动，确保身份信息的不可篡改性。')
    para(doc,'（2）VC类型与生命周期。系统定义了多种VC类型：IdentityCredential（身份凭证，证明持有者的组织身份和角色）、DataAccessCredential（数据访问凭证，证明持有者对特定数据资产的访问权限）、ComputeCredential（计算凭证，授权持有者使用特定计算资源）、ComplianceCredential（合规凭证，证明数据产品通过了合规审查）。VC的完整生命周期包括：Issuer签发→ Holder存储→ Holder出示→ Verifier验证→ Issuer撤销。')
    para(doc,'（3）选择性披露与零知识证明。系统在标准VC基础上集成了BBS+签名方案，支持选择性披露。持有者可以在出示VC时仅披露必要属性，而隐藏其他属性。例如，证明自己属于某组织但无需透露具体部门，证明自己拥有某数据访问权限但无需透露具体的权限细节。同时集成Schnorr零知识证明协议，支持"我有权访问数据资产X"这类陈述的零知识证明，而不泄露凭证本身。')
    
    table_caption(doc,'表4-4  DID/VC 关键技术指标')
    add_table(doc,
        ['技术指标','参数值','说明'],
        [['DID方法','did:key, did:web, did:ethr','三种方法覆盖不同安全等级'],
         ['签名算法','Ed25519, ES256K, BBS+','Ed25519用于一般场景，BBS+支持SD'],
         ['VC格式','JSON-LD + JWT','两种序列化格式双支持'],
         ['凭证状态管理','StatusList2021 + 区块链','标准吊销列表+链上吊销双重保障'],
         ['密钥轮换周期','支持自动/手动轮换','默认90天自动轮换'],
         ['选择性披露','BBS+签名方案','支持隐藏凭证中部分属性']],
        [2.5,3.5,4.5])
    
    heading(doc,'4.5  AI Agent智能体',2)
    para(doc,'AI Agent智能体是能源可信数据空间的智能交互层，利用大语言模型（LLM）技术提供自然语言交互的数据查询、分析和交易辅助能力。本项目的AI Agent技术创新体现在以下几个方面：')
    para(doc,'（1）多Agent协作架构。系统设计了四种专业Agent协同工作的架构：查询Agent（Query Agent）负责理解用户的数据查询需求，将其转化为结构化的API调用或SQL查询；交易Agent（Trade Agent）负责分析市场行情，提供交易建议和风险评估；安全Agent（Security Agent）负责安全策略审查和威胁预警；调度Agent（Dispatch Agent）负责计算任务的调度优化和资源分配。四种Agent共享知识库，但各自拥有独立的系统提示词和专业知识领域。')
    para(doc,'（2）LLM集成架构。系统采用优先级递减的LLM调用策略：优先使用DeepSeek API进行真实LLM推理；当API不可用时回退到预定义问答库；当预定义库也未命中时，基于关键词匹配提供基础引导。这一架构保证了系统在各种网络条件下的可用性。LLM调用通过AsyncOpenAI客户端进行，支持流式输出（SSE），为用户提供实时感知的交互体验。')
    para(doc,'（3）知识库管理。系统为AI Agent建立了结构化的领域知识库，包括能源行业术语词典（500+术语）、数据标准规范（DCMM、DAMA相关）、业务流程知识（数据发布、授权、交易流程）和安全合规知识（法律法规条款、安全最佳实践）。知识库支持文档上传、自动分块、嵌入向量化和语义检索，为Agent提供领域知识增强（RAG, Retrieval-Augmented Generation）。')
    page_break(doc)
    print("  [OK] 第四-五章完成 (约10000字)")

def write_ch5(doc):
    """第五章：关键技术实现细节"""
    heading(doc,'第五章  关键技术实现细节',1)
    
    heading(doc,'5.1  隐私计算模块实现',2)
    para(doc,'隐私计算模块是能源可信数据空间的技术核心，集成了联邦学习（FL）、可信执行环境（TEE）、安全多方计算（MPC）和同态加密（HE）四种技术路线。本节详细阐述各子模块的实现细节。')
    
    heading(doc,'5.1.1  联邦学习子模块',3)
    para(doc,'联邦学习子模块基于微众银行开源FATE框架进行定制开发，实现了对能源行业场景的深度适配。后端服务层实现了任务管理服务（FateJob）、模型管理服务（FlModel）和会话管理服务（MpcSession）。任务管理服务负责联邦学习任务的全生命周期管理，包括任务创建、参数配置、参与方选择、任务启动/暂停/终止。模型管理服务负责训练完成的模型存储、版本管理、模型评估和模型部署。')
    para(doc,'在安全增强方面，模块在梯度交换阶段集成了差分隐私机制。具体实现中，对每个参与方上传的模型梯度进行L2范数裁剪（Clipping），裁剪阈值C由超参数控制，然后添加高斯噪声N(0, σ²)，其中σ = C × sqrt(2×ln(1.25/δ)) / ε。通过调节隐私预算ε（默认8.0）和δ（默认10⁻⁵），可以在隐私保护和模型精度之间取得平衡。')
    
    heading(doc,'5.1.2  TEE可信执行环境子模块',3)
    para(doc,'TEE子模块基于Intel SGX技术实现，提供了硬件级别的隔离计算环境。模块核心组件包括TEE实例管理器（TeeInstance）、飞地（Enclave）生命周期管理和远程证明（Remote Attestation）验证。TeeInstance模型记录了每个TEE实例的唯一标识、Enclave度量值（MRENCLAVE）、安全版本号（ISVSVN）、CPU SGX版本和状态信息。')
    para(doc,'远程证明是TEE安全性的核心保障，确保代码确实在真实的SGX Enclave中运行且未被篡改。系统实现了基于Intel IAS（Intel Attestation Service）或DCAP（Data Center Attestation Primitives）的远程证明流程：Enclave生成Quote→发送给IAS/DCAP验证→返回验证报告→验证报告包含Enclave身份、执行环境可信状态等信息。')
    
    heading(doc,'5.1.3  MPC安全多方计算子模块',3)
    para(doc,'MPC子模块基于安全多方计算协议实现，支持2-N方的联合安全计算。模块引入了MpcSession会话管理机制，每个MPC会话跟踪参与方列表、计算协议类型、会话状态和计算结果哈希。会话状态包括：init（初始化）、waiting_peers（等待参与方加入）、computing（计算中）、completed（完成）、failed（失败）。')
    para(doc,'通信层采用基于gRPC的安全通信框架，所有参与方之间通过TLS 1.3加密通道通信。计算层实现了秘密共享协议的完整生命周期：秘密分发（Share）→ 本地计算（Local Compute）→ 秘密重构（Reconstruct）。对于复杂计算，采用电路编译技术将计算逻辑编译为算术电路，然后分解为可并行执行的安全加法门和乘法门。')
    
    heading(doc,'5.1.4  同态加密子模块',3)
    para(doc,'同态加密子模块实现了HeKey（密钥管理）和HeCiphertext（密文管理）两个核心数据模型。HeKey模型记录了密钥对的唯一标识、算法类型（Paillier、BFV、CKKS）、密钥参数（如Paillier的n和g，BFV的poly_modulus_degree等）、公钥和加密的私钥。HeCiphertext模型关联到对应的密钥，记录密文数据和加密元数据。')
    para(doc,'模块目前主要集成Paillier半同态加密方案用于纵向联邦学习中的安全梯度聚合。Paillier方案支持加法同态运算：Enc(m1) × Enc(m2) = Enc(m1 + m2)，且支持标量乘法：Enc(m)ᵏ = Enc(k×m)。这两条性质足以支持许多机器学习算法（如逻辑回归、线性回归）的安全梯度计算。对于需要全同态加密（支持任意密文计算）的场景，模块预留了BFV和CKKS方案的接口。')
    
    heading(doc,'5.2  区块链模块实现',2)
    para(doc,'区块链模块实现了数据存证、智能合约执行和NFT铸造三大核心功能。模块架构分为三层：接入层（Blockchain Abstraction Layer）提供统一的区块链操作接口；合约层管理智能合约的部署、调用和升级；同步层负责链上数据与本地数据库的同步。')
    para(doc,'数据模型层面，模块定义了三个核心数据模型：NftAsset——记录数据NFT的铸造信息，包括token_id、合约地址、元数据URI、所有者和铸造者；EvidenceRecord——记录数据存证信息，包括证据类型、证据哈希（SHA-256）、存证交易哈希、区块号和确认数；BlockchainTransaction——记录所有区块链交易信息，包括from/to地址、交易数据、gas费用、状态（pending/confirmed/failed）和交易回执。')
    para(doc,'智能合约采用Solidity语言编写，使用Hardhat开发框架。项目包含21个智能合约文件，涵盖数据资产管理、交易匹配、授权控制、收益分配等业务场景。合约编译后通过Web3.py与以太坊节点交互，支持Infura公共节点和私有链节点两种连接方式。合约部署采用Factory模式，主合约通过工厂合约部署，支持同一逻辑合约创建多个实例。')
    
    heading(doc,'5.3  数据资产管理模块实现',2)
    para(doc,'数据资产管理模块是系统的数据底座，实现了数据的全生命周期管理。后端定义了DataSource（数据源）、DataAsset（数据资产）、Metadata（元数据）、Tag（标签）、AssetTag（资产标签关联）、AccessLog（访问日志）、DataVersion（数据版本）、VersionTag（版本标签）、CurrentVersion（当前版本）等多个数据库模型，形成了完整的数据资产管理体系。')
    para(doc,'数据血缘追踪是数据资产管理的关键功能。系统通过解析数据处理的ETL流程（Extract-Transform-Load），自动构建字段级别的数据血缘关系。血缘图谱以有向无环图（DAG）的形式存储和展示，节点代表数据资产，边代表数据流转关系。前端使用React Flow库实现血缘图谱的交互式可视化。')
    para(doc,'数据质量管理模块实现了基于CAUTUV模型的六维度质量评估。每个维度支持配置多条质量规则，如完整性规则检查非空值比例，准确性规则检查数值范围，一致性规则检查跨表约束。质量检查任务支持定时执行和事件触发执行，检查结果写入DataQualityReport模型，不达标项自动生成告警。')
    
    heading(doc,'5.4  安全认证与访问控制实现',2)
    para(doc,'安全认证模块实现了多层次的身份认证和访问控制机制：')
    para(doc,'（1）多模式认证。系统支持三种认证模式：密码认证——基于bcrypt哈希的密码验证，JWT令牌签发；DID认证——基于分布式数字身份的挑战-响应认证（Challenge-Response）；证书认证——基于X.509证书的mTLS双向认证。所有认证模式通过统一的认证接口（/api/v1/auth/login）暴露。')
    para(doc,'（2）MFA多因素认证。基于TOTP标准（RFC 6238）实现，支持Google Authenticator、Microsoft Authenticator等通用认证器App。MFA流程包括：用户绑定MFA→服务端生成TOTP密钥和QR码→用户扫码绑定→登录时输入6位动态码→服务端验证。系统为每个用户预生成8个备用恢复码，用于认证器不可用时的应急登录。')
    para(doc,'（3）RBAC+ABAC混合访问控制。角色分admin（系统管理员）、operator（运维人员）、data_provider（数据提供方）、data_consumer（数据使用方）、auditor（审计员）五种。每个角色具有不同的菜单权限、API权限和数据权限。在RBAC基础上叠加ABAC，通过评估请求方属性（角色、组织、安全等级）、资源属性（数据分类、敏感等级）和环境属性（时间、网络位置）动态决策。')
    para(doc,'（4）审计日志。所有数据访问操作记录到AuditLog模型，包含操作主体（user_id）、操作类型（action_type）、操作对象（resource_type + resource_id）、操作详情（details JSONB）、IP地址和User-Agent。审计日志表设置为仅追加（Append-Only），通过数据库权限禁止DELETE和UPDATE操作，确保日志的不可篡改性。')
    
    heading(doc,'5.5  前端交互与可视化实现',2)
    para(doc,'前端采用React 18 + TypeScript + MUI 5 + Vite技术栈构建，实现了约50个功能页面。关键技术实现包括：')
    para(doc,'（1）状态管理。采用Zustand轻量级状态管理库，结合@tanstack/react-query进行服务端状态管理。authStore管理认证状态和用户信息，mfaStore管理MFA流程状态。服务端数据通过react-query的useQuery/useMutation hooks获取，自动处理缓存、重新获取和乐观更新。')
    para(doc,'（2）数据可视化。集成ECharts 5和Recharts图表库，提供丰富的可视化组件。运营分析中心实现了KPI仪表盘、趋势折线图、饼图、热力图等多种图表类型。数据血缘关系使用React Flow实现交互式DAG图。区块链浏览器展示交易列表和区块详情。')
    para(doc,'（3）前端服务层。定义了16个API Service模块，每个模块封装一类API的调用逻辑，统一处理请求/响应拦截、错误处理和令牌刷新。Service模块包括：authService、dataAssetService、computeService、blockchainService、securityService、portalService、agentService、monitorService、notificationService等。')
    para(doc,'（4）主题与国际化。基于MUI ThemeProvider实现亮色/暗色双主题切换。虽然当前版本主要面向中文用户，但架构上预留了i18n国际化支持，使用react-i18next框架可快速扩展多语言。')
    page_break(doc)
    print("  [OK] 第五-六章完成 (约8000字)")

if __name__=='__main__':
    doc=init_document()
    write_cover(doc); write_abstract(doc)
    write_ch3(doc); write_ch4(doc); write_ch5(doc)
    doc.save('test_ch3-5.docx')
    print("测试成功")
