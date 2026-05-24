"""
Comprehensive fix for MUI→TDesign migration issues:
1. Fix multi-line closing tag mismatches (h3>...</span>, h2>...</span>, p>...</span>)
2. Replace remaining MUI components (MenuItem, DialogActions, DialogTitle, DialogContent)
3. Fix import issues
"""
import re, os

FILES = [
    'src/pages/portal/LandingPage.tsx',
    'src/pages/ops/AgentManagePage.tsx',
    'src/pages/security/SecurityKeysPage.tsx',
    'src/pages/data/MetadataPage.tsx',
    'src/pages/data/DataMarketPage.tsx',
    'src/pages/data/DataQualityPage.tsx',
    'src/pages/ops/OpsMonitorPage.tsx',
    'src/pages/ops/AuditLogPage.tsx',
    'src/pages/data/ServiceRequestPage.tsx',
    'src/pages/ops/NotificationCenterPage.tsx',
    'src/pages/ops/OpsSLAPage.tsx',
    'src/pages/ops/OpsBillingPage.tsx',
    'src/pages/dashboard/DashboardPage.tsx',
    'src/pages/data/DataLineagePage.tsx',
    'src/pages/ops/SystemConfigPage.tsx',
    'src/pages/security/SecurityCryptoPage.tsx',
    'src/pages/ops/OpsKpiPage.tsx',
]

# MUI component replacements
MUI_REPLACEMENTS = {
    '<MenuItem': '<Select.Option',
    '</MenuItem>': '</Select.Option>',
    '<DialogActions>': '<div className="flex justify-end gap-2 p-4 border-t border-gray-100">',
    '</DialogActions>': '</div>',
    '<DialogActions className="p-4 border-t border-gray-100 flex justify-end gap-2">': '<div className="flex justify-end gap-2 p-4 border-t border-gray-100">',
    '<DialogTitle>': '<div className="text-lg font-semibold p-4 border-b border-gray-100">',
    '</DialogTitle>': '</div>',
    '<DialogContent>': '<div className="p-4">',
    '</DialogContent>': '</div>',
    '<DialogContent className="p-4">': '<div className="p-4">',
}

def fix_closing_tags_stack(content):
    """Fix mismatched closing tags using stack-based approach."""
    lines = content.split('\n')
    result = []
    fixes = 0

    # Track opening h/p tags and their expected closing
    tag_stack = []  # (tag_name, line_idx)

    for i, line in enumerate(lines):
        # Find opening tags: <h3>, <h2>, <p>, <h4>, etc.
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']:
            if re.search(r'<' + tag + r'\b', line) and not re.search(r'</' + tag + r'>', line):
                tag_stack.append((tag, i))

        # Find </span> that should be </h3>, </h2>, </p>, etc.
        if '</span>' in line and tag_stack:
            # Check if this </span> is likely a mismatched closing tag
            # Heuristic: if the line only has </span> with whitespace, or
            # if the corresponding opening tag is on the stack
            stripped = line.strip()
            if stripped == '</span>' or stripped.startswith('</span>'):
                tag_name, open_line = tag_stack[-1]
                # Check if the opening tag is still "active" (not yet closed)
                # by looking for the proper closing tag between open_line and current line
                between = '\n'.join(lines[open_line:i])
                proper_close = '</' + tag_name + '>'
                if proper_close not in between:
                    # This </span> is the closing for our tag
                    line = line.replace('</span>', '</' + tag_name + '>', 1)
                    tag_stack.pop()
                    fixes += 1

        result.append(line)

    return '\n'.join(result), fixes

def fix_file(f):
    if not os.path.exists(f):
        print(f'SKIP: {f} not found')
        return

    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()

    original = content
    total_fixes = 0

    # 1. Replace remaining MUI components
    for old, new in MUI_REPLACEMENTS.items():
        if old in content:
            count = content.count(old)
            content = content.replace(old, new)
            total_fixes += count

    # 2. Fix remaining same-line mismatches (catch any we missed)
    for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']:
        pat = r'(<' + tag + r'[^>]*>.*?)</span>'
        matches = re.findall(pat, content)
        if matches:
            content = re.sub(pat, r'\1</' + tag + '>', content)
            total_fixes += len(matches)

    # 3. Fix multi-line mismatches
    content, stack_fixes = fix_closing_tags_stack(content)
    total_fixes += stack_fixes

    # 4. Fix broken import statements (type import split across lines)
    # Pattern: import {\n  icons...\n  TypeName, -> import { icons } from '...';\nimport type { TypeName } from '...';
    # Actually, let's just check for the specific pattern in AgentManagePage
    if 'AgentManagePage' in f:
        # Fix broken import: the type import got split
        content = re.sub(
            r"import \{\s*\n\s*(\w+Icon[^}]*)\} from 'tdesign-icons-react';\s*\n\s*(AgentConfig[^}]*\}) from '@/api/agentManage';",
            r"import { \1 } from 'tdesign-icons-react';\nimport type { \2 from '@/api/agentManage';",
            content
        )

    if content != original:
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(content)
        print(f'Fixed {total_fixes} issues in {f}')
    else:
        print(f'No changes in {f}')

for f in FILES:
    fix_file(f)
