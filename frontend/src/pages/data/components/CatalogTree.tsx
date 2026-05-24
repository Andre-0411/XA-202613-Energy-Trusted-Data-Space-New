/**
 * CatalogTree - 分类树侧边栏组件
 * 用于数据目录页面的分类导航树
 */
import React, { useState } from 'react';
import {
  FolderOpenIcon, ChevronRightIcon, ChevronDownIcon,
} from 'tdesign-icons-react';

/** 分类树节点 */
export interface CategoryNode {
  id: string;
  label: string;
  children: CategoryNode[];
}

/** 树节点渲染组件 */
const TreeNode: React.FC<{
  node: CategoryNode;
  depth: number;
  selectedId: string;
  onSelect: (id: string) => void;
}> = ({ node, depth, selectedId, onSelect }) => {
  const [expanded, setExpanded] = useState<boolean>(depth === 0);
  const hasChildren = node.children.length > 0;
  const isSelected = selectedId === node.id;

  return (
    <div>
      <div
        className={`flex items-center gap-1 cursor-pointer rounded py-1.5 px-2 ${
          isSelected ? 'bg-blue-50' : 'hover:bg-gray-50'
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => {
          onSelect(node.id);
          if (hasChildren) setExpanded(!expanded);
        }}
      >
        {hasChildren ? (
          expanded ? <ChevronDownIcon size="14px" className="text-gray-400" /> : <ChevronRightIcon size="14px" className="text-gray-400" />
        ) : (
          <span className="w-3.5" />
        )}
        {expanded && hasChildren ? (
          <FolderOpenIcon size="16px" className="text-blue-500" />
        ) : (
          <FolderOpenIcon size="16px" className="text-gray-400" />
        )}
        <span className={`text-sm ${isSelected ? 'font-semibold text-blue-600' : 'text-gray-700'}`}>
          {node.label}
        </span>
      </div>
      {expanded && hasChildren && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
};

/** 预置分类树 - 匹配后端六大分类 */
export const CATEGORY_TREE: CategoryNode[] = [
  {
    id: 'generation',
    label: '发电数据',
    children: [
      { id: '发电', label: '发电数据', children: [] },
    ],
  },
  {
    id: 'consumption',
    label: '用电数据',
    children: [
      { id: '用电', label: '用电数据', children: [] },
    ],
  },
  {
    id: 'dispatch',
    label: '调度数据',
    children: [
      { id: '调度', label: '调度数据', children: [] },
    ],
  },
  {
    id: 'market',
    label: '市场数据',
    children: [
      { id: '市场', label: '市场数据', children: [] },
    ],
  },
  {
    id: 'device',
    label: '设备状态数据',
    children: [
      { id: '设备状态', label: '设备状态数据', children: [] },
    ],
  },
  {
    id: 'geo',
    label: '地理信息数据',
    children: [
      { id: '地理信息', label: '地理信息数据', children: [] },
    ],
  },
];

interface CatalogTreeProps {
  selectedCategory: string;
  onCategorySelect: (id: string) => void;
}

/** CatalogTree 组件 */
const CatalogTree: React.FC<CatalogTreeProps> = ({ selectedCategory, onCategorySelect }) => {
  return (
    <div className="w-64 shrink-0 rounded-xl bg-white border border-gray-200 shadow-sm p-4 overflow-auto">
      <h4 className="text-sm font-bold mb-2">分类导航</h4>
      <hr className="border-gray-200 mb-2" />
      <div
        className={`flex items-center gap-1 cursor-pointer rounded py-1.5 px-2 mb-1 ${
          !selectedCategory ? 'bg-blue-50' : 'hover:bg-gray-50'
        }`}
        onClick={() => onCategorySelect('')}
      >
        <FolderOpenIcon size="16px" className="text-blue-500" />
        <span className={`text-sm ${!selectedCategory ? 'font-semibold text-blue-600' : 'text-gray-700'}`}>全部</span>
      </div>
      {CATEGORY_TREE.map((node) => (
        <TreeNode
          key={node.id}
          node={node}
          depth={0}
          selectedId={selectedCategory}
          onSelect={onCategorySelect}
        />
      ))}
    </div>
  );
};

export default CatalogTree;
