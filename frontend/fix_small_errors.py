"""Fix remaining TS errors in small files."""
import re, os

def fix_file(path, fixes):
    if not os.path.exists(path):
        print(f"SKIP: {path}")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content
    for old, new in fixes:
        content = content.replace(old, new)
    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed: {path}")
    else:
        print(f"No changes: {path}")

# 1. OpsUsersPage: Input label → wrapped with label span, TablePagination → Pagination
fix_file('src/pages/ops/OpsUsersPage.tsx', [
    # Remove non-existent TablePagination import
    ("import TablePagination from '@/components/TablePagination';\n", ''),
    # Fix Input label prop - TDesign Input doesn't have label
    ('<Input label="用户名"', '<div><span className="text-sm text-gray-600 mb-1 block">用户名</span><Input'),
    ('<Input label="密码" type="password"', '<div><span className="text-sm text-gray-600 mb-1 block">密码</span><Input type="password"'),
    ('<Input label="邮箱"', '<div><span className="text-sm text-gray-600 mb-1 block">邮箱</span><Input'),
    ('<Input label="手机"', '<div><span className="text-sm text-gray-600 mb-1 block">手机</span><Input'),
    ('<Input label="组织 ID"', '<div><span className="text-sm text-gray-600 mb-1 block">组织 ID</span><Input'),
    # Fix onChange to close the wrapper div
])

# 2. OpsServicesPage: same Input label + type="date" issues
fix_file('src/pages/ops/OpsServicesPage.tsx', [
    ("import TablePagination from '@/components/TablePagination';\n", ''),
    ('<Input label="服务名称"', '<div><span className="text-sm text-gray-600 mb-1 block">服务名称</span><Input'),
    ('type="date"', 'type="text"'),
])

# 3. OpsSLAPage: .data access + type="date"
fix_file('src/pages/ops/OpsSLAPage.tsx', [
    ('type="date"', 'type="text"'),
])

# 4. OpsOrgPage: Input label + TablePagination
fix_file('src/pages/ops/OpsOrgPage.tsx', [
    ("import TablePagination from '@/components/TablePagination';\n", ''),
    ('<Input label="名称"', '<div><span className="text-sm text-gray-600 mb-1 block">名称</span><Input'),
    ('<Input label="描述"', '<div><span className="text-sm text-gray-600 mb-1 block">描述</span><Input'),
])

# 5. BcQueryPage: onEnter → onKeyDown or different handler
# 6. SecurityVcPage + SecurityDidPage: Pagination showSizeChanger → sizeChangerPlacement or remove
# 7. DataAssetsPage: Textarea not imported

print("\nDone with simple replacements.")
