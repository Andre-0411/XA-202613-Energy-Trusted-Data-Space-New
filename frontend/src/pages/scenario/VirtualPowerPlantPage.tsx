/**
 * 虚拟电厂可视化编辑器
 * 支持拖拽组件搭建电网网络，点击配置数据源，自动识别场景
 */
import React, { useState, useCallback, useRef, useEffect } from 'react';
import { 
  Button, Card, Tag, Dialog, Select, Input, MessagePlugin, 
  Tabs, Divider, Tooltip, Loading, Switch 
} from 'tdesign-react';
import { 
  AddIcon, EditIcon, DeleteIcon, PlayIcon, SaveIcon, 
  RefreshIcon, SearchIcon, LinkIcon 
} from 'tdesign-icons-react';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import request from '@/api/request';

// 类型定义
interface GridNode {
  id: string;
  type: 'generator' | 'load' | 'transformer' | 'bus' | 'storage' | 'solar' | 'wind' | 'ev';
  label: string;
  x: number;
  y: number;
  config: NodeConfig;
  status: 'idle' | 'running' | 'error' | 'warning';
  dataSource?: DataSourceConfig;
}

interface NodeConfig {
  capacity?: number;
  voltage?: number;
  power?: number;
  efficiency?: number;
  [key: string]: any;
}

interface DataSourceConfig {
  assetId?: string;
  assetName?: string;
  fields?: string[];
  refreshInterval?: number;
}

interface Connection {
  id: string;
  from: string;
  to: string;
  power?: number;
  status: 'active' | 'inactive' | 'overload';
}

interface Scenario {
  id: string;
  name: string;
  description: string;
  type: 'peak_shaving' | 'demand_response' | 'frequency_regulation' | 'energy_optimization';
  requiredData: string[];
  computeTask?: string;
}

// 设备组件配置
const EQUIPMENT_TYPES = [
  { type: 'generator', label: '发电机', icon: '⚡', color: '#f5222d', category: 'source' },
  { type: 'solar', label: '光伏', icon: '☀️', color: '#faad14', category: 'source' },
  { type: 'wind', label: '风机', icon: '🌬️', color: '#1890ff', category: 'source' },
  { type: 'storage', label: '储能', icon: '🔋', color: '#52c41a', category: 'source' },
  { type: 'ev', label: '充电桩', icon: '🔌', color: '#722ed1', category: 'load' },
  { type: 'load', label: '负荷', icon: '🏭', color: '#fa541c', category: 'load' },
  { type: 'transformer', label: '变压器', icon: '⚙️', color: '#13c2c2', category: 'transform' },
  { type: 'bus', label: '母线', icon: '━', color: '#595959', category: 'transform' },
];

// 场景模板
const SCENE_TEMPLATES: Scenario[] = [
  {
    id: 'peak_shaving',
    name: '削峰填谷',
    description: '利用储能和柔性负荷平衡电网峰谷',
    type: 'peak_shaving',
    requiredData: ['load_forecast', 'price_signal', 'storage_status'],
  },
  {
    id: 'demand_response',
    name: '需求响应',
    description: '根据电网需求调整用户用电',
    type: 'demand_response',
    requiredData: ['load_profile', 'comfort_constraints', 'dr_signal'],
  },
  {
    id: 'frequency_regulation',
    name: '频率调节',
    description: '快速响应电网频率变化',
    type: 'frequency_regulation',
    requiredData: ['frequency_data', 'agc_signal', 'capacity_available'],
  },
  {
    id: 'energy_optimization',
    name: '能效优化',
    description: '优化能源使用效率降低成本',
    type: 'energy_optimization',
    requiredData: ['energy_consumption', 'weather_forecast', 'price_forecast'],
  },
];

const VirtualPowerPlantPage: React.FC = () => {
  const breadcrumbs: BreadcrumbItem[] = [homeBreadcrumb, { label: '业务场景' }, { label: '虚拟电厂' }];
  
  // 状态
  const [nodes, setNodes] = useState<GridNode[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [selectedNode, setSelectedNode] = useState<GridNode | null>(null);
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [showDataSourceDialog, setShowDataSourceDialog] = useState(false);
  const [showSceneDialog, setShowSceneDialog] = useState(false);
  const [detectedScene, setDetectedScene] = useState<Scenario | null>(null);
  const [dataAssets, setDataAssets] = useState<any[]>([]);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectFrom, setConnectFrom] = useState<string | null>(null);
  const [draggedType, setDraggedType] = useState<string | null>(null);
  const [showComputeDialog, setShowComputeDialog] = useState(false);
  const [computeProgress, setComputeProgress] = useState(0);
  const [computeStatus, setComputeStatus] = useState<'idle' | 'running' | 'completed' | 'error'>('idle');
  
  const canvasRef = useRef<HTMLDivElement>(null);

  // 加载数据资产
  useEffect(() => {
    fetchDataAssets();
  }, []);

  const fetchDataAssets = async () => {
    try {
      const res: any = await request.get('/data/assets', { params: { page: 1, page_size: 100 } });
      const data = res?.data || res;
      setDataAssets(data?.items || data || []);
    } catch (error) {
      console.error('Failed to fetch data assets:', error);
    }
  };

  // 拖拽处理
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (!draggedType || !canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const newNode: GridNode = {
      id: `node_${Date.now()}`,
      type: draggedType as any,
      label: EQUIPMENT_TYPES.find(t => t.type === draggedType)?.label || '设备',
      x,
      y,
      config: {},
      status: 'idle',
    };

    setNodes(prev => [...prev, newNode]);
    setDraggedType(null);
    detectScenario([...nodes, newNode], connections);
  };

  // 节点拖动
  const handleNodeDrag = (nodeId: string, e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startY = e.clientY;
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return;

    const startNodeX = node.x;
    const startNodeY = node.y;

    const handleMouseMove = (moveE: MouseEvent) => {
      const dx = moveE.clientX - startX;
      const dy = moveE.clientY - startY;
      setNodes(prev => prev.map(n => 
        n.id === nodeId ? { ...n, x: startNodeX + dx, y: startNodeY + dy } : n
      ));
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  // 连线处理
  const handleNodeClick = (nodeId: string) => {
    if (isConnecting) {
      if (connectFrom && connectFrom !== nodeId) {
        const newConnection: Connection = {
          id: `conn_${Date.now()}`,
          from: connectFrom,
          to: nodeId,
          status: 'active',
        };
        setConnections(prev => [...prev, newConnection]);
        setIsConnecting(false);
        setConnectFrom(null);
        detectScenario(nodes, [...connections, newConnection]);
        MessagePlugin.success('连接已建立');
      }
    } else {
      setSelectedNode(nodes.find(n => n.id === nodeId) || null);
    }
  };

  // 场景识别
  const detectScenario = (currentNodes: GridNode[], currentConnections: Connection[]) => {
    const nodeTypes = currentNodes.map(n => n.type);
    
    // 分析网络特征
    const hasStorage = nodeTypes.includes('storage');
    const hasRenewable = nodeTypes.includes('solar') || nodeTypes.includes('wind');
    const hasLoad = nodeTypes.includes('load') || nodeTypes.includes('ev');
    const hasGenerator = nodeTypes.includes('generator');
    
    // 识别最适合的场景
    let bestScenario: Scenario | null = null;
    
    if (hasStorage && hasLoad) {
      bestScenario = SCENE_TEMPLATES.find(s => s.id === 'peak_shaving') || null;
    } else if (hasRenewable && hasStorage) {
      bestScenario = SCENE_TEMPLATES.find(s => s.id === 'energy_optimization') || null;
    } else if (hasLoad && currentNodes.length >= 3) {
      bestScenario = SCENE_TEMPLATES.find(s => s.id === 'demand_response') || null;
    } else if (hasGenerator && hasLoad) {
      bestScenario = SCENE_TEMPLATES.find(s => s.id === 'frequency_regulation') || null;
    }
    
    setDetectedScene(bestScenario);
  };

  // 配置数据源
  const handleDataSourceConfig = (assetId: string) => {
    if (!selectedNode) return;
    
    const asset = dataAssets.find(a => a.id === assetId);
    if (!asset) return;

    setNodes(prev => prev.map(n => 
      n.id === selectedNode.id 
        ? { 
            ...n, 
            dataSource: { 
              assetId: asset.id, 
              assetName: asset.name, 
              fields: asset.fields || [],
              refreshInterval: 60,
            } 
          } 
        : n
    ));
    setShowDataSourceDialog(false);
    MessagePlugin.success(`已绑定数据源: ${asset.name}`);
  };

  // 执行计算
  const handleExecuteCompute = async () => {
    if (!detectedScene) return;
    
    setShowComputeDialog(true);
    setComputeStatus('running');
    setComputeProgress(0);

    // 模拟计算进度
    const interval = setInterval(() => {
      setComputeProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setComputeStatus('completed');
          return 100;
        }
        return prev + 10;
      });
    }, 500);

    try {
      // 调用后端计算API
      const nodeData = nodes.map(n => ({
        type: n.type,
        config: n.config,
        dataSource: n.dataSource,
      }));

      await request.post('/compute/tasks', {
        task_type: detectedScene.type,
        input_data: {
          nodes: nodeData,
          connections: connections,
          scene: detectedScene.id,
        },
        algorithm: 'federated_learning',
      });

      MessagePlugin.success('计算任务已提交');
    } catch (error) {
      setComputeStatus('error');
      MessagePlugin.error('计算任务提交失败');
    }
  };

  // 保存拓扑
  const handleSave = async () => {
    try {
      await request.post('/virtual-power-plant/save', {
        nodes,
        connections,
        scene: detectedScene,
      });
      MessagePlugin.success('拓扑已保存');
    } catch (error) {
      MessagePlugin.error('保存失败');
    }
  };

  // 删除节点
  const handleDeleteNode = (nodeId: string) => {
    setNodes(prev => prev.filter(n => n.id !== nodeId));
    setConnections(prev => prev.filter(c => c.from !== nodeId && c.to !== nodeId));
    setSelectedNode(null);
  };

  // 渲染连线
  const renderConnections = () => {
    return connections.map(conn => {
      const fromNode = nodes.find(n => n.id === conn.from);
      const toNode = nodes.find(n => n.id === conn.to);
      if (!fromNode || !toNode) return null;

      const x1 = fromNode.x + 60;
      const y1 = fromNode.y + 30;
      const x2 = toNode.x + 60;
      const y2 = toNode.y + 30;

      return (
        <line
          key={conn.id}
          x1={x1} y1={y1} x2={x2} y2={y2}
          stroke={conn.status === 'overload' ? '#f5222d' : conn.status === 'active' ? '#52c41a' : '#d9d9d9'}
          strokeWidth={2}
          strokeDasharray={conn.status === 'inactive' ? '5,5' : 'none'}
        />
      );
    });
  };

  // 渲染节点
  const renderNodes = () => {
    return nodes.map(node => {
      const equipType = EQUIPMENT_TYPES.find(t => t.type === node.type);
      const isSelected = selectedNode?.id === node.id;
      const isConnectSource = connectFrom === node.id;

      return (
        <div
          key={node.id}
          className={`absolute cursor-pointer select-none transition-all duration-200 ${
            isSelected ? 'ring-2 ring-blue-500 shadow-lg' : ''
          } ${isConnectSource ? 'ring-2 ring-green-500' : ''}`}
          style={{ left: node.x, top: node.y }}
          onMouseDown={(e) => handleNodeDrag(node.id, e)}
          onClick={() => handleNodeClick(node.id)}
        >
          <div 
            className="w-[120px] h-[60px] rounded-lg border-2 flex flex-col items-center justify-center bg-white hover:shadow-md"
            style={{ borderColor: equipType?.color || '#d9d9d9' }}
          >
            <span className="text-2xl">{equipType?.icon}</span>
            <span className="text-xs font-medium mt-1">{node.label}</span>
          </div>
          {node.dataSource && (
            <div className="absolute -top-2 -right-2 w-4 h-4 bg-green-500 rounded-full border-2 border-white" />
          )}
          {node.status === 'running' && (
            <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            </div>
          )}
        </div>
      );
    });
  };

  return (
    <PageContainer>
      <PageHeader title="虚拟电厂可视化编辑器" breadcrumbs={breadcrumbs} />
      
      <div className="flex gap-4" style={{ height: 'calc(100vh - 180px)' }}>
        {/* 左侧设备面板 */}
        <div className="w-48 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-3 bg-gray-50 border-b border-gray-200">
            <h3 className="font-semibold text-sm">设备组件</h3>
          </div>
          <div className="p-2 space-y-1">
            {EQUIPMENT_TYPES.map(equip => (
              <div
                key={equip.type}
                draggable
                onDragStart={() => setDraggedType(equip.type)}
                className="flex items-center gap-2 p-2 rounded cursor-grab hover:bg-gray-50 active:cursor-grabbing"
              >
                <span className="text-xl">{equip.icon}</span>
                <span className="text-sm">{equip.label}</span>
              </div>
            ))}
          </div>
          
          <Divider />
          
          <div className="p-2">
            <Button 
              block 
              size="small" 
              variant={isConnecting ? 'base' : 'outline'}
              theme={isConnecting ? 'danger' : 'primary'}
              onClick={() => {
                setIsConnecting(!isConnecting);
                setConnectFrom(null);
              }}
            >
              {isConnecting ? '取消连线' : '连线模式'}
            </Button>
          </div>
        </div>

        {/* 中间画布 */}
        <div className="flex-1 relative">
          <div 
            ref={canvasRef}
            className="w-full h-full bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden relative"
            style={{ 
              backgroundImage: 'radial-gradient(circle, #e5e7eb 1px, transparent 1px)',
              backgroundSize: '20px 20px' 
            }}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
          >
            {/* SVG连线层 */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none">
              {renderConnections()}
            </svg>
            
            {/* 节点层 */}
            {renderNodes()}

            {/* 空状态 */}
            {nodes.length === 0 && (
              <div className="absolute inset-0 flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <p className="text-lg font-medium">拖拽设备组件到此处</p>
                  <p className="text-sm mt-2">搭建虚拟电厂电网拓扑</p>
                </div>
              </div>
            )}
          </div>

          {/* 工具栏 */}
          <div className="absolute top-4 right-4 flex gap-2">
            <Button size="small" icon={<SaveIcon />} onClick={handleSave}>保存</Button>
            <Button size="small" icon={<RefreshIcon />} onClick={() => { setNodes([]); setConnections([]); setDetectedScene(null); }}>清空</Button>
          </div>
        </div>

        {/* 右侧配置面板 */}
        <div className="w-72 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <Tabs defaultValue="scene" className="h-full">
            <Tabs.TabPanel value="scene" label="场景识别">
              <div className="p-4 space-y-4">
                {/* 检测到的场景 */}
                {detectedScene ? (
                  <Card>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="font-semibold">🎯 推荐场景</h4>
                        <Tag theme="success" variant="light">已识别</Tag>
                      </div>
                      <h3 className="text-lg font-bold text-blue-600">{detectedScene.name}</h3>
                      <p className="text-sm text-gray-500">{detectedScene.description}</p>
                      <Divider />
                      <div>
                        <p className="text-sm font-medium mb-2">所需数据:</p>
                        <div className="flex flex-wrap gap-1">
                          {detectedScene.requiredData.map(d => (
                            <Tag key={d} size="small">{d}</Tag>
                          ))}
                        </div>
                      </div>
                      <Button 
                        block 
                        theme="primary" 
                        icon={<PlayIcon />}
                        onClick={handleExecuteCompute}
                      >
                        执行计算
                      </Button>
                    </div>
                  </Card>
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    <p>添加设备后自动识别场景</p>
                  </div>
                )}

                {/* 场景模板列表 */}
                <div>
                  <h4 className="font-medium mb-2">场景模板</h4>
                  <div className="space-y-2">
                    {SCENE_TEMPLATES.map(scene => (
                      <Card key={scene.id} className="cursor-pointer hover:shadow-md" onClick={() => setDetectedScene(scene)}>
                        <div className="flex items-center gap-2">
                          <span className="text-lg">
                            {scene.type === 'peak_shaving' ? '⚡' : 
                             scene.type === 'demand_response' ? '📡' :
                             scene.type === 'frequency_regulation' ? '📊' : '🔋'}
                          </span>
                          <div>
                            <p className="font-medium text-sm">{scene.name}</p>
                            <p className="text-xs text-gray-400">{scene.description}</p>
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
              </div>
            </Tabs.TabPanel>

            <Tabs.TabPanel value="config" label="节点配置">
              <div className="p-4">
                {selectedNode ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="font-semibold">{selectedNode.label}</h4>
                      <Tag>{selectedNode.type}</Tag>
                    </div>
                    
                    <div className="space-y-2">
                      <label className="text-sm font-medium">节点名称</label>
                      <Input 
                        value={selectedNode.label} 
                        onChange={(val) => {
                          setNodes(prev => prev.map(n => 
                            n.id === selectedNode.id ? { ...n, label: val } : n
                          ));
                          setSelectedNode({ ...selectedNode, label: val });
                        }}
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium">容量 (kW)</label>
                      <Input 
                        type="number"
                        value={String(selectedNode.config.capacity || '')} 
                        onChange={(val) => {
                          const newConfig = { ...selectedNode.config, capacity: Number(val) };
                          setNodes(prev => prev.map(n => 
                            n.id === selectedNode.id ? { ...n, config: newConfig } : n
                          ));
                          setSelectedNode({ ...selectedNode, config: newConfig });
                        }}
                      />
                    </div>

                    <Divider />

                    <div>
                      <h4 className="font-medium mb-2">数据源绑定</h4>
                      {selectedNode.dataSource ? (
                        <Card>
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-medium">{selectedNode.dataSource.assetName}</span>
                              <Tag theme="success" size="small">已绑定</Tag>
                            </div>
                            <p className="text-xs text-gray-400">
                              字段: {selectedNode.dataSource.fields?.join(', ') || '无'}
                            </p>
                            <Button 
                              size="small" 
                              variant="outline" 
                              onClick={() => setShowDataSourceDialog(true)}
                            >
                              更换数据源
                            </Button>
                          </div>
                        </Card>
                      ) : (
                        <Button 
                          block 
                          variant="outline" 
                          icon={<LinkIcon />}
                          onClick={() => setShowDataSourceDialog(true)}
                        >
                          绑定数据源
                        </Button>
                      )}
                    </div>

                    <Divider />

                    <Button 
                      block 
                      theme="danger" 
                      variant="outline" 
                      icon={<DeleteIcon />}
                      onClick={() => handleDeleteNode(selectedNode.id)}
                    >
                      删除节点
                    </Button>
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    <p>点击节点查看配置</p>
                  </div>
                )}
              </div>
            </Tabs.TabPanel>

            <Tabs.TabPanel value="status" label="运行状态">
              <div className="p-4 space-y-4">
                <Card>
                  <h4 className="font-semibold mb-3">网络统计</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="text-center p-2 bg-blue-50 rounded">
                      <p className="text-2xl font-bold text-blue-600">{nodes.length}</p>
                      <p className="text-xs text-gray-500">节点数</p>
                    </div>
                    <div className="text-center p-2 bg-green-50 rounded">
                      <p className="text-2xl font-bold text-green-600">{connections.length}</p>
                      <p className="text-xs text-gray-500">连接数</p>
                    </div>
                    <div className="text-center p-2 bg-yellow-50 rounded">
                      <p className="text-2xl font-bold text-yellow-600">
                        {nodes.filter(n => n.dataSource).length}
                      </p>
                      <p className="text-xs text-gray-500">已绑定数据</p>
                    </div>
                    <div className="text-center p-2 bg-purple-50 rounded">
                      <p className="text-2xl font-bold text-purple-600">
                        {nodes.filter(n => n.status === 'running').length}
                      </p>
                      <p className="text-xs text-gray-500">运行中</p>
                    </div>
                  </div>
                </Card>

                <Card>
                  <h4 className="font-semibold mb-3">设备列表</h4>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {nodes.map(node => {
                      const equip = EQUIPMENT_TYPES.find(t => t.type === node.type);
                      return (
                        <div key={node.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                          <div className="flex items-center gap-2">
                            <span>{equip?.icon}</span>
                            <span className="text-sm">{node.label}</span>
                          </div>
                          <Tag 
                            size="small" 
                            theme={node.status === 'running' ? 'success' : node.status === 'error' ? 'danger' : 'default'}
                          >
                            {node.status === 'running' ? '运行中' : node.status === 'error' ? '异常' : '待机'}
                          </Tag>
                        </div>
                      );
                    })}
                  </div>
                </Card>
              </div>
            </Tabs.TabPanel>
          </Tabs>
        </div>
      </div>

      {/* 数据源绑定弹窗 */}
      <Dialog
        header="绑定数据源"
        visible={showDataSourceDialog}
        onClose={() => setShowDataSourceDialog(false)}
        width="600px"
      >
        <div className="space-y-4">
          <Input prefixIcon={<SearchIcon />} placeholder="搜索数据资产..." />
          <div className="max-h-60 overflow-y-auto space-y-2">
            {dataAssets.map(asset => (
              <Card 
                key={asset.id} 
                className="cursor-pointer hover:shadow-md"
                onClick={() => handleDataSourceConfig(asset.id)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{asset.name}</p>
                    <p className="text-sm text-gray-400">{asset.description || '无描述'}</p>
                  </div>
                  <Tag>{asset.type || '数据集'}</Tag>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </Dialog>

      {/* 计算进度弹窗 */}
      <Dialog
        header="计算任务执行"
        visible={showComputeDialog}
        onClose={() => setShowComputeDialog(false)}
        width="500px"
      >
        <div className="space-y-4">
          {computeStatus === 'running' && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span>执行进度</span>
                <span>{computeProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${computeProgress}%` }}
                />
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Loading size="small" />
                <span>正在执行联邦学习计算...</span>
              </div>
            </div>
          )}
          {computeStatus === 'completed' && (
            <div className="text-center py-4">
              <div className="text-4xl mb-2">✅</div>
              <p className="text-lg font-semibold">计算完成</p>
              <p className="text-gray-500">结果已生成，请查看报告</p>
            </div>
          )}
          {computeStatus === 'error' && (
            <div className="text-center py-4">
              <div className="text-4xl mb-2">❌</div>
              <p className="text-lg font-semibold text-red-600">计算失败</p>
              <p className="text-gray-500">请检查配置后重试</p>
            </div>
          )}
        </div>
      </Dialog>
    </PageContainer>
  );
};

export default VirtualPowerPlantPage;
