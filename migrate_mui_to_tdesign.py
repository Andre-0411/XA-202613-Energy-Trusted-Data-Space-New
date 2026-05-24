"""
MUI → TDesign + Tailwind CSS 自动迁移脚本
批量替换 MUI 导入和组件用法
"""
import re
import os
from pathlib import Path

FRONTEND_SRC = Path("D:/Projects/energy-trusted-data-space/frontend/src/pages")

# ========== MUI → TDesign 导入映射 ==========

# MUI 组件导入行模式
MUI_MATERIAL_IMPORT = re.compile(
    r"import\s*\{[^}]*\}\s*from\s*['\"]@mui/material['\"];?\s*\n?",
    re.MULTILINE
)

MUI_ICONS_IMPORT = re.compile(
    r"import\s+\w+\s+from\s*['\"]@mui/icons-material/\w+['\"];?\s*\n?",
    re.MULTILINE
)

MUI_ICONS_DESTRUCTURED_IMPORT = re.compile(
    r"import\s*\{[^}]*\}\s*from\s*['\"]@mui/icons-material['\"];?\s*\n?",
    re.MULTILINE
)

# ========== 组件替换规则 ==========

def get_tdesign_icon_name(mui_icon_name):
    """MUI icon name → TDesign icon name"""
    mapping = {
        'Search': 'SearchIcon',
        'Add': 'AddIcon',
        'Edit': 'EditIcon',
        'Delete': 'DeleteIcon',
        'Visibility': 'ViewIcon',
        'Refresh': 'RefreshIcon',
        'CheckCircle': 'CheckCircleFilledIcon',
        'Cancel': 'ErrorCircleFilledIcon',
        'Pending': 'TimeIcon',
        'Assignment': 'CartIcon',
        'AssignmentTurnedIn': 'CheckCircleFilledIcon',
        'ListAlt': 'DashboardIcon',
        'TrendingUp': 'TrendingUpIcon',
        'Publish': 'CloudIcon',
        'Label': 'Tag',
        'Storage': 'ServerIcon',
        'Warning': 'ErrorCircleFilledIcon',
        'Error': 'ErrorCircleFilledIcon',
        'Info': 'InfoCircleFilledIcon',
        'Settings': 'SettingIcon',
        'Person': 'UserIcon',
        'Business': 'BuildingIcon',
        'Security': 'SecuredIcon',
        'Lock': 'LockIcon',
        'Key': 'KeyIcon',
        'Notifications': 'NotificationIcon',
        'Wifi': 'WifiIcon',
        'ArrowBack': 'ArrowLeftIcon',
        'ChevronRight': 'ChevronRightIcon',
        'Home': 'HomeIcon',
        'Close': 'CloseIcon',
        'FilterList': 'FilterIcon',
        'Schedule': 'TimeIcon',
        'MoreVert': 'MoreIcon',
        'ExpandMore': 'ChevronDownIcon',
        'Download': 'DownloadIcon',
        'Upload': 'UploadIcon',
        'Copy': 'CopyIcon',
        'Share': 'ShareIcon',
        'Star': 'StarIcon',
        'Favorite': 'HeartIcon',
        'Calendar': 'CalendarIcon',
        'Email': 'MailIcon',
        'Phone': 'CallIcon',
        'Location': 'LocationIcon',
        'Link': 'LinkIcon',
        'Code': 'CodeIcon',
        'DataUsage': 'ChartIcon',
        'Timeline': 'ChartIcon',
        'BarChart': 'ChartIcon',
        'PieChart': 'ChartIcon',
        'TableChart': 'ChartIcon',
        'ViewList': 'ListIcon',
        'ViewModule': 'GridIcon',
        'SwapHoriz': 'SwapIcon',
        'CompareArrows': 'SwapIcon',
        'Check': 'CheckIcon',
        'Clear': 'CloseIcon',
        'Done': 'CheckIcon',
        'Folder': 'FolderIcon',
        'Description': 'FileIcon',
        'AttachFile': 'AttachmentIcon',
        'Build': 'ToolIcon',
        'BugReport': 'BugIcon',
        'Help': 'HelpIcon',
        'Exit': 'LogoutIcon',
        'Power': 'PowerIcon',
        'Speed': 'DashboardIcon',
        'Memory': 'ServerIcon',
        'Timer': 'TimeIcon',
        'Update': 'RefreshIcon',
        'Sync': 'RefreshIcon',
        'Cached': 'RefreshIcon',
        'ZoomIn': 'ZoomInIcon',
        'ZoomOut': 'ZoomOutIcon',
        'Fullscreen': 'MaximizeIcon',
        'Print': 'PrintIcon',
        'Save': 'SaveIcon',
        'Undo': 'RollbackIcon',
        'Redo': 'RedoIcon',
        'ContentCopy': 'CopyIcon',
        'ContentPaste': 'PasteIcon',
    }
    return mapping.get(mui_icon_name, 'SettingIcon')


def collect_mui_icons(content):
    """从文件内容中收集所有使用的 MUI 图标"""
    icons = set()
    # Pattern: import XxxIcon from '@mui/icons-material/Xxx'
    for m in re.finditer(r"import\s+(\w+)\s+from\s*['\"]@mui/icons-material/\w+['\"]", content):
        icons.add(m.group(1))
    # Pattern: import { Xxx, Yyy } from '@mui/icons-material'
    for m in re.finditer(r"import\s*\{([^}]+)\}\s*from\s*['\"]@mui/icons-material['\"]", content):
        for icon in m.group(1).split(','):
            icon = icon.strip()
            if icon:
                icons.add(icon)
    return icons


def build_tdesign_imports(content):
    """根据文件实际使用的 MUI 组件，生成 TDesign 导入"""
    tdesign_imports = set()
    tdesign_icon_imports = set()

    # 检测使用了哪些 TDesign 组件
    if re.search(r'\bButton\b', content) and 'Button' not in ['PageHeader', 'DataTable', 'StatusTag', 'ConfirmDialog']:
        tdesign_imports.add('Button')
    if re.search(r'\bInput\b', content):
        tdesign_imports.add('Input')
    if re.search(r'\bSelect\b', content):
        tdesign_imports.add('Select')
    if re.search(r'\bTag\b', content):
        tdesign_imports.add('Tag')
    if re.search(r'\bTooltip\b', content):
        tdesign_imports.add('Tooltip')
    if re.search(r'\bMessagePlugin\b', content):
        tdesign_imports.add('MessagePlugin')
    if re.search(r'\bSkeleton\b', content):
        tdesign_imports.add('Skeleton')
    if re.search(r'\bProgress\b', content):
        tdesign_imports.add('Progress')
    if re.search(r'\bDialog\b', content):
        tdesign_imports.add('Dialog')
    if re.search(r'\bForm\b', content):
        tdesign_imports.add('Form')
    if re.search(r'\bTable\b', content):
        tdesign_imports.add('Table')
    if re.search(r'\bPagination\b', content):
        tdesign_imports.add('Pagination')
    if re.search(r'\bMenu\b', content):
        tdesign_imports.add('Menu')
    if re.search(r'\bBadge\b', content):
        tdesign_imports.add('Badge')
    if re.search(r'\bDropdown\b', content):
        tdesign_imports.add('Dropdown')
    if re.search(r'\bAvatar\b', content):
        tdesign_imports.add('Avatar')
    if re.search(r'\bBreadcrumb\b', content):
        tdesign_imports.add('Breadcrumb')
    if re.search(r'\bTabs\b', content):
        tdesign_imports.add('Tabs')
    if re.search(r'\bSwitch\b', content):
        tdesign_imports.add('Switch')
    if re.search(r'\bCheckbox\b', content):
        tdesign_imports.add('Checkbox')
    if re.search(r'\bRadio\b', content):
        tdesign_imports.add('Radio')
    if re.search(r'\bDatePicker\b', content):
        tdesign_imports.add('DatePicker')
    if re.search(r'\bTimePicker\b', content):
        tdesign_imports.add('TimePicker')
    if re.search(r'\bUpload\b', content):
        tdesign_imports.add('Upload')
    if re.search(r'\bTransfer\b', content):
        tdesign_imports.add('Transfer')
    if re.search(r'\bTree\b', content):
        tdesign_imports.add('Tree')
    if re.search(r'\bCascader\b', content):
        tdesign_imports.add('Cascader')
    if re.search(r'\bAutoComplete\b', content):
        tdesign_imports.add('AutoComplete')
    if re.search(r'\bSlider\b', content):
        tdesign_imports.add('Slider')
    if re.search(r'\bAlert\b', content):
        tdesign_imports.add('Alert')
    if re.search(r'\bDrawer\b', content):
        tdesign_imports.add('Drawer')
    if re.search(r'\bPopover\b', content):
        tdesign_imports.add('Popover')
    if re.search(r'\bPopconfirm\b', content):
        tdesign_imports.add('Popconfirm')
    if re.search(r'\bNotification\b', content):
        tdesign_imports.add('Notification')
    if re.search(r'\bLoading\b', content):
        tdesign_imports.add('Loading')
    if re.search(r'\bImageViewer\b', content):
        tdesign_imports.add('ImageViewer')
    if re.search(r'\bColorPicker\b', content):
        tdesign_imports.add('ColorPicker')
    if re.search(r'\bTreeSelect\b', content):
        tdesign_imports.add('TreeSelect')
    if re.search(r'\bRangeInput\b', content):
        tdesign_imports.add('RangeInput')
    if re.search(r'\bInputNumber\b', content):
        tdesign_imports.add('InputNumber')
    if re.search(r'\bTextarea\b', content):
        tdesign_imports.add('Textarea')
    if re.search(r'\bGuide\b', content):
        tdesign_imports.add('Guide')
    if re.search(r'\bStickyTool\b', content):
        tdesign_imports.add('StickyTool')
    if re.search(r'\bSideBar\b', content):
        tdesign_imports.add('SideBar')
    if re.search(r'\bStep\b', content):
        tdesign_imports.add('Step')
    if re.search(r'\bSteps\b', content):
        tdesign_imports.add('Steps')
    if re.search(r'\bTimeline\b', content):
        tdesign_imports.add('Timeline')
    if re.search(r'\bComment\b', content):
        tdesign_imports.add('Comment')
    if re.search(r'\bList\b', content):
        tdesign_imports.add('List')
    if re.search(r'\bCard\b', content):
        tdesign_imports.add('Card')
    if re.search(r'\bCollapse\b', content):
        tdesign_imports.add('Collapse')
    if re.search(r'\bDivider\b', content):
        tdesign_imports.add('Divider')
    if re.search(r'\bSpace\b', content):
        tdesign_imports.add('Space')
    if re.search(r'\bLayout\b', content):
        tdesign_imports.add('Layout')
    if re.search(r'\bGrid\b', content):
        tdesign_imports.add('Grid')
    if re.search(r'\bAnchor\b', content):
        tdesign_imports.add('Anchor')
    if re.search(r'\bAffix\b', content):
        tdesign_imports.add('Affix')
    if re.search(r'\bBackTop\b', content):
        tdesign_imports.add('BackTop')

    # 收集图标
    icons = collect_mui_icons(content)
    for icon_name in icons:
        td_icon = get_tdesign_icon_name(icon_name)
        tdesign_icon_imports.add(td_icon)

    # 去掉已经通过 common 组件导入的
    tdesign_imports -= {'Tag'}  # Tag 可能通过 StatusTag 使用

    lines = []
    if tdesign_imports:
        sorted_imports = sorted(tdesign_imports)
        lines.append(f"import {{ {', '.join(sorted_imports)} }} from 'tdesign-react';")
    if tdesign_icon_imports:
        sorted_icons = sorted(tdesign_icon_imports)
        lines.append(f"import {{ {', '.join(sorted_icons)} }} from 'tdesign-icons-react';")

    return '\n'.join(lines)


def migrate_file(filepath):
    """迁移单个文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    original_lines = content.count('\n') + 1

    # Step 1: 收集 MUI 图标信息（在删除导入之前）
    tdesign_imports_block = build_tdesign_imports(content)

    # Step 2: 删除 MUI 导入
    content = MUI_MATERIAL_IMPORT.sub('', content)
    content = MUI_ICONS_IMPORT.sub('', content)
    content = MUI_ICONS_DESTRUCTURED_IMPORT.sub('', content)

    # Step 3: 在第一个非注释、非空行之后插入 TDesign 导入
    # 找到所有导入行结束后的位置
    lines = content.split('\n')
    insert_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('import ') or stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*') or stripped == '' or stripped.startswith("/**"):
            insert_idx = i + 1
        elif stripped.startswith('export ') or stripped.startswith('function ') or stripped.startswith('const ') or stripped.startswith('interface ') or stripped.startswith('type '):
            break
        else:
            break

    if tdesign_imports_block:
        lines.insert(insert_idx, tdesign_imports_block)

    content = '\n'.join(lines)

    # Step 4: 替换组件用法
    # Box → div (简化处理，只替换 self-closing 和带属性的)
    content = re.sub(r'<Box\s+', '<div ', content)
    content = re.sub(r'<Box>', '<div>', content)
    content = re.sub(r'</Box>', '</div>', content)

    # Paper → div with styling
    content = re.sub(
        r'<Paper\s*(?:elevation=\{?\d*\}?\s*)?(?:sx=\{[^}]*\}\s*)?>',
        '<div className="rounded-xl bg-white border border-gray-200 shadow-sm">',
        content
    )
    content = re.sub(r'<Paper\s+[^>]*>', '<div className="rounded-xl bg-white border border-gray-200 shadow-sm">', content)
    content = re.sub(r'</Paper>', '</div>', content)

    # Typography → semantic tags
    content = re.sub(r'<Typography\s+variant="h4"[^>]*>', '<h1 className="text-2xl font-bold mb-4">', content)
    content = re.sub(r'<Typography\s+variant="h5"[^>]*>', '<h2 className="text-xl font-semibold mb-3">', content)
    content = re.sub(r'<Typography\s+variant="h6"[^>]*>', '<h3 className="text-lg font-medium mb-2">', content)
    content = re.sub(r'<Typography\s+variant="subtitle1"[^>]*>', '<h4 className="text-base font-medium mb-1">', content)
    content = re.sub(r'<Typography\s+variant="subtitle2"[^>]*>', '<h5 className="text-sm font-medium mb-1">', content)
    content = re.sub(r'<Typography\s+variant="body1"[^>]*>', '<p className="text-base text-gray-700">', content)
    content = re.sub(r'<Typography\s+variant="body2"[^>]*>', '<p className="text-sm text-gray-500">', content)
    content = re.sub(r'<Typography[^>]*>', '<p>', content)
    content = re.sub(r'</Typography>', '</p>', content)

    # Stack → flex div
    content = re.sub(
        r'<Stack\s+direction="row"[^>]*>',
        '<div className="flex items-center gap-3">',
        content
    )
    content = re.sub(
        r'<Stack\s+direction="column"[^>]*>',
        '<div className="flex flex-col gap-3">',
        content
    )
    content = re.sub(r'<Stack[^>]*>', '<div className="flex flex-col gap-3">', content)
    content = re.sub(r'</Stack>', '</div>', content)

    # Container → div
    content = re.sub(r'<Container[^>]*>', '<div className="max-w-screen-xl mx-auto px-4 sm:px-6">', content)
    content = re.sub(r'</Container>', '</div>', content)

    # Card + CardContent → div
    content = re.sub(r'<Card[^>]*>', '<div className="rounded-xl bg-white border border-gray-200 shadow-sm">', content)
    content = re.sub(r'</Card>', '</div>', content)
    content = re.sub(r'<CardContent[^>]*>', '<div className="p-5">', content)
    content = re.sub(r'</CardContent>', '</div>', content)

    # Grid container → grid div
    content = re.sub(r'<Grid\s+container[^>]*>', '<div className="grid grid-cols-12 gap-4">', content)
    content = re.sub(r'<Grid\s+item\s+xs=\{12\}[^>]*>', '<div className="col-span-12">', content)
    content = re.sub(r'<Grid\s+item\s+xs=\{6\}[^>]*>', '<div className="col-span-6">', content)
    content = re.sub(r'<Grid\s+item\s+xs=\{4\}[^>]*>', '<div className="col-span-4">', content)
    content = re.sub(r'<Grid\s+item\s+xs=\{3\}[^>]*>', '<div className="col-span-3">', content)
    content = re.sub(r'<Grid\s+item[^>]*>', '<div>', content)
    content = re.sub(r'</Grid>', '</div>', content)

    # LinearProgress → Progress
    content = re.sub(r'<LinearProgress\s*/>', '<Progress theme="line" />', content)
    content = re.sub(r'<LinearProgress[^>]*/>', '<Progress theme="line" />', content)

    # Chip → Tag
    content = re.sub(r'<Chip\s+label=\{?"?([^"}]+)"?\}[^>]*/>',  r'<Tag>{\1}</Tag>', content)
    content = re.sub(r'<Chip\s+[^>]*label=\{?"?([^"}]+)"?\}[^>]*/>',  r'<Tag>{\1}</Tag>', content)

    # IconButton → Button variant="text"
    content = re.sub(r'<IconButton[^>]*>', '<Button variant="text" theme="default">', content)
    content = re.sub(r'</IconButton>', '</Button>', content)

    # Button variants
    content = re.sub(r'variant="contained"', 'theme="primary"', content)
    content = re.sub(r'variant="outlined"', 'variant="outline"', content)

    # Snackbar + Alert → MessagePlugin (simplified)
    content = re.sub(r'<Snackbar[^>]*>.*?</Snackbar>', '', content, flags=re.DOTALL)
    content = re.sub(r'<Alert\s+[^>]*severity="success"[^>]*>([^<]*)</Alert>', r'MessagePlugin.success("\1")', content)
    content = re.sub(r'<Alert\s+[^>]*severity="error"[^>]*>([^<]*)</Alert>', r'MessagePlugin.error("\1")', content)
    content = re.sub(r'<Alert\s+[^>]*severity="warning"[^>]*>([^<]*)</Alert>', r'MessagePlugin.warning("\1")', content)
    content = re.sub(r'<Alert\s+[^>]*severity="info"[^>]*>([^<]*)</Alert>', r'MessagePlugin.info("\1")', content)

    # Remove DialogTitle/DialogContent/DialogActions wrappers (simplified)
    content = re.sub(r'<DialogTitle[^>]*>', '<h3 className="text-lg font-semibold mb-4">', content)
    content = re.sub(r'</DialogTitle>', '</h3>', content)
    content = re.sub(r'<DialogContent[^>]*>', '<div className="py-4">', content)
    content = re.sub(r'</DialogContent>', '</div>', content)
    content = re.sub(r'<DialogActions[^>]*>', '<div className="flex justify-end gap-3 mt-4">', content)
    content = re.sub(r'</DialogActions>', '</div>', content)

    # Remove empty lines left by import removal
    content = re.sub(r'\n{3,}', '\n\n', content)

    new_lines = content.count('\n') + 1

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, original_lines, new_lines
    return False, original_lines, new_lines


def main():
    """主函数：遍历所有页面文件并迁移"""
    targets = [
        'data', 'compute', 'blockchain', 'portal', 'auth', 'monitor-screen',
        'ops', 'security'
    ]

    total_migrated = 0
    total_skipped = 0

    for module in targets:
        module_path = FRONTEND_SRC / module
        if not module_path.exists():
            print(f"⚠️  模块目录不存在: {module_path}")
            continue

        for tsx_file in sorted(module_path.glob("*.tsx")):
            # 跳过已迁移的（无 MUI 引用）
            with open(tsx_file, 'r', encoding='utf-8') as f:
                content = f.read()

            if '@mui' not in content:
                print(f"  ✅ 已迁移: {tsx_file.name}")
                total_skipped += 1
                continue

            migrated, old_lines, new_lines = migrate_file(tsx_file)
            if migrated:
                print(f"  🔄 已迁移: {tsx_file.name} ({old_lines} → {new_lines} 行)")
                total_migrated += 1
            else:
                print(f"  ⚪ 无变化: {tsx_file.name}")
                total_skipped += 1

    print(f"\n{'='*50}")
    print(f"迁移完成: {total_migrated} 个文件已修改, {total_skipped} 个跳过")


if __name__ == '__main__':
    main()
