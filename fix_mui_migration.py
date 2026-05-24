"""
修复 MUI → TDesign 迁移脚本产生的 TypeScript 错误
"""
import re
from pathlib import Path

FRONTEND_SRC = Path("D:/Projects/energy-trusted-data-space/frontend/src/pages")

def fix_typography_closing_tags(content):
    """修复 Typography 开闭标签不匹配问题"""
    # 将所有 </p> 中的 </Typography> 替换问题修复
    # 先把所有 Typography 开标签映射
    tag_map = {
        '<h1 className="text-2xl font-bold mb-4">': '</h1>',
        '<h2 className="text-xl font-semibold mb-3">': '</h2>',
        '<h3 className="text-lg font-medium mb-2">': '</h3>',
        '<h4 className="text-base font-medium mb-1">': '</h4>',
        '<h5 className="text-sm font-medium mb-1">': '</h5>',
        '<p className="text-base text-gray-700">': '</p>',
        '<p className="text-sm text-gray-500">': '</p>',
        '<p>': '</p>',
    }

    # 查找所有开标签并记录位置
    opens = []
    for tag in tag_map:
        idx = 0
        while True:
            idx = content.find(tag, idx)
            if idx == -1:
                break
            opens.append((idx, tag, tag_map[tag]))
            idx += len(tag)

    # 按位置排序
    opens.sort()

    # 对于每个开标签，找到最近的 </p> 并替换为正确的闭标签
    for pos, open_tag, close_tag in opens:
        # 找到这个开标签之后最近的 </p>
        search_start = pos + len(open_tag)
        close_p = content.find('</p>', search_start)
        if close_p != -1:
            # 检查中间是否有其他开标签
            has_nested = False
            for other_pos, other_open, _ in opens:
                if other_pos > pos and other_pos < close_p:
                    has_nested = True
                    break
            if not has_nested:
                content = content[:close_p] + close_tag + content[close_p + 4:]

    return content


def fix_broken_imports(content, filepath):
    """修复被脚本打断的多行 import 语句"""
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # 检测是否是被插入的 tdesign-react import 打断了多行 import
        if 'import { Button, Card, Grid' in line and i > 0:
            prev = lines[i-1].strip() if i > 0 else ''
            # 检查前一行是否是不完整的 import
            if prev.endswith(',') or prev.endswith('{') or (prev.startswith('import') and '{' in prev and '}' not in prev):
                # 这个 tdesign import 被错误地插入了，先收集它
                tdesign_import = line
                # 向后找到被中断的 import 的剩余部分
                j = i + 1
                remaining_parts = []
                while j < len(lines):
                    next_line = lines[j].strip()
                    if next_line.startswith('} from') or next_line.startswith("} from"):
                        # 找到 import 结束
                        remaining_parts.append(lines[j])
                        j += 1
                        break
                    elif next_line and not next_line.startswith('//') and not next_line.startswith('/*'):
                        remaining_parts.append(lines[j])
                        j += 1
                    else:
                        break

                # 重建 import：先写 tdesign import，再写被中断的 import
                fixed_lines.append(tdesign_import)
                # 重建原始 import
                for part in remaining_parts:
                    fixed_lines.append(part)
                i = j
                continue

        # 检测不完整的 import 语句（import { 后面直接跟了其他 import）
        if line.strip().startswith('import {') and '}' not in line and i + 1 < len(lines):
            next_line = lines[i+1].strip() if i + 1 < len(lines) else ''
            if next_line.startswith('import '):
                # 当前 import 没有闭合但下一行是新 import，说明被打断了
                # 尝试找到后续的闭合行
                j = i + 1
                parts = [line]
                while j < len(lines):
                    if lines[j].strip().startswith('} from') or (lines[j].strip().endswith(';') and 'from' in lines[j]):
                        parts.append(lines[j])
                        j += 1
                        break
                    elif lines[j].strip().startswith('import '):
                        # 这是被错误插入的 import
                        fixed_lines.append(lines[j])
                        j += 1
                    else:
                        parts.append(lines[j])
                        j += 1
                fixed_lines.extend(parts)
                i = j
                continue

        fixed_lines.append(line)
        i += 1

    return '\n'.join(fixed_lines)


def fix_sx_props(content):
    """移除 div 上的 sx prop（非 MUI 组件不支持）"""
    # sx={{ ... }} 在 div 上无效，替换为 className
    # 简单的 sx 转换
    content = re.sub(
        r'\s+sx=\{\{[^}]*\}\}',
        '',
        content
    )
    return content


def fix_unclosed_tags(content):
    """修复 Typography → h 标签替换后可能导致的未闭合标签"""
    # 统计开闭标签数量
    for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div']:
        opens = len(re.findall(f'<{tag}[\\s>]', content))
        closes = len(re.findall(f'</{tag}>', content))
        if opens != closes:
            # 差异不大时尝试修复
            pass
    return content


def fix_file(filepath):
    """修复单个文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 1. 修复 Typography 闭标签
    content = fix_typography_closing_tags(content)

    # 2. 修复 sx props
    content = fix_sx_props(content)

    # 3. 修复被打断的 import
    content = fix_broken_imports(content, filepath)

    # 4. 移除未使用的 LoadingOverlay import（如果已删除）
    content = re.sub(
        r"import LoadingOverlay from '@/components/LoadingOverlay';\n",
        '',
        content
    )

    # 5. 清理多余空行
    content = re.sub(r'\n{4,}', '\n\n\n', content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    fixed_count = 0
    for module in ['data', 'compute', 'blockchain', 'portal', 'auth', 'monitor-screen', 'ops', 'security']:
        module_path = FRONTEND_SRC / module
        if not module_path.exists():
            continue
        for tsx_file in sorted(module_path.glob("*.tsx")):
            if fix_file(tsx_file):
                print(f"  🔧 已修复: {tsx_file.name}")
                fixed_count += 1
            else:
                print(f"  ✅ 无需修复: {tsx_file.name}")

    print(f"\n修复完成: {fixed_count} 个文件")


if __name__ == '__main__':
    main()
