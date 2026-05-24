import re, os

files = [
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

for f in files:
    if not os.path.exists(f):
        print(f'SKIP: {f} not found')
        continue
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()

    original = content
    fixes = 0

    # Fix same-line mismatches: <h3 ...>text</span> -> <h3 ...>text</h3>
    for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']:
        pat = r'(<' + tag + r'[^>]*>.*?)</span>'
        matches = re.findall(pat, content)
        if matches:
            content = re.sub(pat, r'\1</' + tag + '>', content)
            fixes += len(matches)

    # Also fix MenuItem -> Select.Option and DialogActions -> div
    # Check for remaining MUI components
    remaining_mui = re.findall(r'<(MenuItem|DialogActions|DialogContent|DialogTitle|Dialog|Select|Stack|Box|Paper|Grid|Card|CardContent|Chip|Tab|Tabs)\b', content)

    if content != original:
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(content)
        print(f'Fixed {fixes} closing tags in {f}. Remaining MUI: {len(remaining_mui)}')
    else:
        print(f'No same-line fixes in {f}. Remaining MUI: {len(remaining_mui)}')
