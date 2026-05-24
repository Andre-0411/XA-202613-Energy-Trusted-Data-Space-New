"""
Final MUI → TDesign + Tailwind migration script.
Handles remaining 23 files with MUI imports.
Strategy: Read each file, apply regex replacements, write back.
"""
import re, os, glob

FRONTEND = "D:/Projects/energy-trusted-data-space/frontend"
PAGES_DIR = os.path.join(FRONTEND, "src/pages")

# === MUI → TDesign Icon Mapping ===
ICON_MAP = {
    # MUI import name → TDesign import name
    "Add": "AddIcon",
    "Edit": "EditIcon",
    "Delete": "DeleteIcon",
    "Search": "SearchIcon",
    "Visibility": "BrowseIcon",
    "ArrowBack": "ArrowLeftIcon",
    "CheckCircle": "CheckCircleFilledIcon",
    "Cancel": "CloseIcon",
    "Close": "CloseIcon",
    "Warning": "ErrorCircleFilledIcon",
    "Info": "InfoCircleFilledIcon",
    "Refresh": "RefreshIcon",
    "Settings": "SettingIcon",
    "Link": "LinkIcon",
    "FilterList": "FilterIcon",
    "List": "ViewListIcon",
    "Category": "FolderOpenIcon",
    "HowToReg": "VerifiedIcon",
    "Star": "StarFilledIcon",
    "Folder": "FolderIcon",
    "FolderOpen": "FolderOpenIcon",
    "ChevronRight": "ChevronRightIcon",
    "ExpandMore": "ChevronDownIcon",
    "TrendingUp": "TrendingUpIcon",
    "Pending": "TimeIcon",
    "Security": "ShieldErrorFilledIcon",
    "VerifiedUser": "VerifiedIcon",
    "Shield": "ShieldErrorFilledIcon",
    "Lock": "LockOnIcon",
    "Key": "KeyIcon",
    "OpenInNew": "LinkIcon",
    "Publish": "SendIcon",
    "Unpublished": "CloseIcon",
    "Block": "CloseCircleFilledIcon",
    "ShoppingCart": "CartIcon",
    "MoreVert": "MoreIcon",
    "Speed": "TrendingUpIcon",
    "Storage": "ServerIcon",
    "Cloud": "CloudIcon",
    "Computer": "ServerIcon",
    "NetworkCheck": "WifiIcon",
    "Fingerprint": "FingerprintIcon",
    "VpnKey": "KeyIcon",
    "Autorenew": "RefreshIcon",
    "CalendarToday": "TimeIcon",
    "Notifications": "NotificationIcon",
    "Dashboard": "DashboardIcon",
    "Assessment": "DashboardIcon",
    "BarChart": "TrendingUpIcon",
    "Timeline": "TimeIcon",
    "Description": "ViewListIcon",
    "Code": "SlashIcon",
    "Build": "SettingIcon",
    "PlayArrow": "FlashlightIcon",
    "Stop": "CloseCircleFilledIcon",
    "Pause": "TimeIcon",
    "CopyAll": "FolderOpenIcon",
    "ContentCopy": "FolderOpenIcon",
    "Download": "FolderOpenIcon",
    "Upload": "FolderOpenIcon",
}

# MUI color → TDesign theme
COLOR_MAP = {
    "success": "success",
    "warning": "warning",
    "error": "danger",
    "info": "primary",
    "primary": "primary",
    "secondary": "default",
    "default": "default",
}


def find_mui_files():
    """Find all .tsx files still importing from MUI."""
    result = []
    for root, dirs, files in os.walk(PAGES_DIR):
        for f in files:
            if not f.endswith(".tsx"):
                continue
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
            if "@mui/material" in content or "@mui/icons-material" in content:
                result.append(path)
    return sorted(result)


def extract_mui_icons(content):
    """Extract MUI icon imports and return mapping of alias → tdesign name."""
    aliases = {}
    # Match: import { X as Y, Z } from '@mui/icons-material';
    pattern = r"import\s*\{([^}]+)\}\s*from\s*['\"]@mui/icons-material['\"]"
    for m in re.finditer(pattern, content):
        imports = m.group(1)
        for item in imports.split(","):
            item = item.strip()
            if not item:
                continue
            if " as " in item:
                orig, alias = item.split(" as ")
                orig = orig.strip()
                alias = alias.strip()
            else:
                orig = item.strip()
                alias = orig
            tdesign_name = ICON_MAP.get(orig, orig + "Icon")
            aliases[alias] = tdesign_name
    return aliases


def extract_mui_components(content):
    """Extract MUI component imports from @mui/material."""
    components = set()
    pattern = r"import\s*\{([^}]+)\}\s*from\s*['\"]@mui/material['\"]"
    for m in re.finditer(pattern, content):
        imports = m.group(1)
        for item in imports.split(","):
            item = item.strip()
            if item:
                components.add(item)
    return components


def migrate_file(filepath):
    """Migrate a single file from MUI to TDesign + Tailwind."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    filename = os.path.basename(filepath)

    # Step 1: Extract MUI icon aliases
    icon_aliases = extract_mui_icons(content)

    # Step 2: Remove MUI icon import block
    content = re.sub(
        r"import\s*\{[^}]*\}\s*from\s*['\"]@mui/icons-material['\"]\s*;?\n?",
        "",
        content,
    )

    # Step 3: Build TDesign icon imports
    tdesign_icons = sorted(set(icon_aliases.values()))
    if tdesign_icons:
        icon_import_line = f"import {{ {', '.join(tdesign_icons)} }} from 'tdesign-icons-react';\n"
        # Check if tdesign-icons-react already imported
        if "tdesign-icons-react" not in content:
            # Insert after last import or at top
            last_import = content.rfind("import ")
            if last_import >= 0:
                end_of_line = content.index("\n", last_import) + 1
                content = content[:end_of_line] + icon_import_line + content[end_of_line:]
            else:
                content = icon_import_line + content
        else:
            # Merge with existing tdesign-icons-react import
            existing_pattern = r"import\s*\{([^}]+)\}\s*from\s*['\"]tdesign-icons-react['\"]"
            existing_match = re.search(existing_pattern, content)
            if existing_match:
                existing_icons = set(
                    x.strip() for x in existing_match.group(1).split(",") if x.strip()
                )
                all_icons = sorted(existing_icons | set(tdesign_icons))
                content = re.sub(
                    existing_pattern,
                    f"import {{ {', '.join(all_icons)} }} from 'tdesign-icons-react'",
                    content,
                )

    # Step 4: Replace icon variable references in JSX
    # e.g. <AddIcon /> stays, but <Add /> → <AddIcon />
    for alias, tdesign_name in icon_aliases.items():
        if alias != tdesign_name:
            # Replace usage in JSX: <Alias → <TDesignName, </Alias → </TDesignName
            content = re.sub(rf"<{alias}(\s|/|>|$)", f"<{tdesign_name}\\1", content)
            content = re.sub(rf"</{alias}>", f"</{tdesign_name}>", content)

    # Step 5: Remove MUI material import
    content = re.sub(
        r"import\s*\{[^}]*\}\s*from\s*['\"]@mui/material['\"]\s*;?\n?",
        "",
        content,
    )

    # Step 6: Determine which TDesign components are needed based on usage
    tdesign_needed = set()

    # Check what MUI components were used
    mui_comps = extract_mui_components(original)

    # Map MUI components to TDesign equivalents in the content
    # Typography → h2/h3/p/span with Tailwind (already in JSX or need conversion)
    # We'll do component-level replacements

    # --- TextField → Input ---
    if "TextField" in mui_comps:
        tdesign_needed.add("Input")
        # TextField with select → Select
        if re.search(r"<TextField\s[^>]*\bselect\b", content):
            tdesign_needed.add("Select")
        # Convert TextField patterns
        # <TextField value={x} onChange={(e) => setX(e.target.value)} .../>
        content = re.sub(
            r"<TextField\s+value=\{(\w+)\}\s+onChange=\{\(e(?:\.target\.value)?\)\s*=>\s*set(\w+)\(e\.target\.value\)\}",
            r"<Input value={\1} onChange={(val) => set\2(String(val))}",
            content,
        )
        # <TextField ... onChange={(e) => setX(e.target.value)} ... value={x}
        # This is trickier - handle multiline TextField with onChange
        # Replace onChange pattern in any TextField
        content = re.sub(
            r"(onChange=\{)\(e(?:\.target\.value)?\)\s*=>\s*(set\w+)\(e\.target\.value\)(\})",
            r"\1(val) => \2(String(val))\3",
            content,
        )
        # <TextField select ...> → need to convert to Select
        # This is complex - for now, convert remaining <TextField to <Input
        content = content.replace("<TextField", "<Input")
        content = content.replace("</TextField>", "</Input>")

    # --- Box → div ---
    if "Box" in mui_comps:
        content = re.sub(r"<Box(\s|>)", r"<div\1", content)
        content = re.sub(r"</Box>", "</div>", content)

    # --- Paper → div with classes ---
    if "Paper" in mui_comps:
        content = re.sub(r"<Paper(\s|>)", r'<div className="rounded-xl bg-white border border-gray-200 shadow-sm"\1', content)
        content = re.sub(r"</Paper>", "</div>", content)

    # --- Card → div ---
    if "Card" in mui_comps:
        content = re.sub(r"<Card(\s|>)", r'<div className="rounded-xl bg-white border border-gray-200"\1', content)
        content = re.sub(r"</Card>", "</div>", content)

    # --- CardContent → div with padding ---
    if "CardContent" in mui_comps:
        content = re.sub(r"<CardContent(\s|>)", r'<div className="p-4"\1', content)
        content = re.sub(r"</CardContent>", "</div>", content)

    # --- Stack → div with flex ---
    if "Stack" in mui_comps:
        # Stack direction="row" spacing={N} → flex items-center gap-N
        content = re.sub(
            r'<Stack\s+direction="row"\s+spacing=\{(\d+)\}>',
            r'<div className="flex items-center gap-\1">',
            content,
        )
        # Stack spacing={N} → flex flex-col gap-N
        content = re.sub(
            r'<Stack\s+spacing=\{(\d+)\}>',
            r'<div className="flex flex-col gap-\1">',
            content,
        )
        # Generic Stack → div
        content = re.sub(r"<Stack(\s|>)", r"<div\1", content)
        content = re.sub(r"</Stack>", "</div>", content)

    # --- Grid → div ---
    if "Grid" in mui_comps:
        content = re.sub(r"<Grid\s+container>", r'<div className="grid grid-cols-1 md:grid-cols-2 gap-4">', content)
        content = re.sub(r"<Grid\s+item\s+xs=\{12\}\s+md=\{6\}>", r'<div className="md:col-span-1">', content)
        content = re.sub(r"<Grid\s+item\s+xs=\{12\}>", r'<div>', content)
        content = re.sub(r"<Grid\s+item\s+xs=\{6\}>", r'<div className="col-span-1">', content)
        content = re.sub(r"<Grid(\s|>)", r"<div\1", content)
        content = re.sub(r"</Grid>", "</div>", content)

    # --- Typography → semantic HTML ---
    if "Typography" in mui_comps:
        # variant="h5" → h2
        content = re.sub(r'<Typography\s+variant="h5"[^>]*>', r'<h2 className="text-xl font-semibold text-gray-800">', content)
        content = re.sub(r'<Typography\s+variant="h6"[^>]*>', r'<h3 className="text-base font-semibold text-gray-800">', content)
        content = re.sub(r'<Typography\s+variant="body1"[^>]*>', r'<p className="text-sm text-gray-700">', content)
        content = re.sub(r'<Typography\s+variant="body2"[^>]*>', r'<span className="text-xs text-gray-600">', content)
        # Generic Typography → span
        content = re.sub(r"<Typography(\s|>)", r"<span\1", content)
        content = re.sub(r"</Typography>", "</span>", content)

    # --- Chip → Tag ---
    if "Chip" in mui_comps:
        tdesign_needed.add("Tag")
        # Chip label={x} → <Tag>{x}</Tag>
        # This is complex with inline props, do basic replacement
        content = re.sub(r"<Chip(\s|>)", r"<Tag\1", content)
        content = re.sub(r"</Chip>", "</Tag>", content)

    # --- Tooltip title= → content= ---
    if "Tooltip" in mui_comps:
        tdesign_needed.add("Tooltip")
        content = content.replace("title={", "content={")
        content = re.sub(r'title="([^"]*)"', r'content="\1"', content)

    # --- IconButton → span ---
    if "IconButton" in mui_comps:
        content = re.sub(
            r"<IconButton(\s)",
            r'<span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center"\1',
            content,
        )
        content = re.sub(r"</IconButton>", "</span>", content)

    # --- Button variants ---
    if "Button" in mui_comps:
        tdesign_needed.add("Button")
        content = content.replace('variant="contained"', 'theme="primary"')
        content = content.replace("variant='contained'", "theme='primary'")
        content = content.replace('variant="outlined"', 'variant="outline"')
        content = content.replace("variant='outlined'", "variant='outline'")
        content = content.replace('variant="text"', 'variant="text"')

    # --- Dialog ---
    if "Dialog" in mui_comps:
        tdesign_needed.add("Dialog")
        content = re.sub(r'<Dialog\s+open=\{(\w+)\}\s+onClose=\{([^}]+)\}[^>]*>',
                        lambda m: f'<Dialog visible={{{m.group(1)}}} onClose={{{m.group(2)}}} header="" ',
                        content)
        content = re.sub(r"<DialogTitle>([^<]*)</DialogTitle>", r"", content)
        content = re.sub(r"<DialogContent>", r"", content)
        content = re.sub(r"</DialogContent>", r"", content)
        content = re.sub(r"<DialogActions>", r'<div className="flex justify-end gap-2 mt-4">', content)
        content = re.sub(r"</DialogActions>", r"</div>", content)

    # --- MenuItem ---
    if "MenuItem" in mui_comps:
        content = re.sub(r"<MenuItem\s+value=\"([^\"]*)\">", r'<option value="\1">', content)
        content = re.sub(r"</MenuItem>", r"</option>", content)

    # --- Divider ---
    if "Divider" in mui_comps:
        content = content.replace("<Divider />", '<hr className="border-gray-200 my-2" />')
        content = content.replace("<Divider/>", '<hr className="border-gray-200 my-2" />')

    # --- Remove MUI-specific props ---
    # sx={{ ... }} → convert to className where possible, or remove
    # This is complex; for now, remove simple sx props
    content = re.sub(r'\s+sx=\{\{[^}]*\}\}', '', content)
    # InputProps → prefixIcon
    content = re.sub(
        r'InputProps=\{\{\s*startAdornment:\s*(<[^>]+>)\s*\}\}',
        r'prefixIcon=\1',
        content,
    )
    # startIcon → icon
    content = re.sub(r"startIcon=\{(<[^>]+>)\}", r"icon=\1", content)
    # fullWidth → remove (not needed in TDesign)
    content = re.sub(r'\s+fullWidth', '', content)

    # Step 7: Build TDesign component import
    # Add needed components
    if "Input" in tdesign_needed or "TextField" in mui_comps:
        tdesign_needed.add("Input")
    if "Select" in tdesign_needed:
        tdesign_needed.add("Select")
    if "Tag" in tdesign_needed:
        tdesign_needed.add("Tag")
    if "Tooltip" in tdesign_needed:
        tdesign_needed.add("Tooltip")
    if "Button" in tdesign_needed:
        tdesign_needed.add("Button")
    if "Dialog" in tdesign_needed:
        tdesign_needed.add("Dialog")
    if "MessagePlugin" in tdesign_needed:
        tdesign_needed.add("MessagePlugin")

    # Check if tdesign-react already imported
    tdesign_comp_pattern = r"import\s*\{([^}]+)\}\s*from\s*['\"]tdesign-react['\"]"
    tdesign_match = re.search(tdesign_comp_pattern, content)
    if tdesign_match:
        existing = set(x.strip() for x in tdesign_match.group(1).split(",") if x.strip())
        all_comps = sorted(existing | tdesign_needed)
        content = re.sub(
            tdesign_comp_pattern,
            f"import {{ {', '.join(all_comps)} }} from 'tdesign-react'",
            content,
        )
    elif tdesign_needed:
        # Add new import
        comp_import = f"import {{ {', '.join(sorted(tdesign_needed))} }} from 'tdesign-react';\n"
        # Insert after React import or at top
        react_import = content.find("from 'react'")
        if react_import >= 0:
            end = content.index("\n", react_import) + 1
            content = content[:end] + comp_import + content[end:]
        else:
            content = comp_import + content

    # Step 8: Clean up any remaining MUI references
    # Remove @mui imports that might have been missed
    content = re.sub(r".*from\s*['\"]@mui/[^'\"]*['\"];?\n?", "", content)

    # Step 9: Remove empty lines created by removals (collapse 3+ blank lines to 2)
    content = re.sub(r"\n{3,}", "\n\n", content)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def main():
    files = find_mui_files()
    print(f"Found {len(files)} files with MUI imports\n")

    migrated = []
    failed = []

    for filepath in files:
        rel = os.path.relpath(filepath, FRONTEND)
        try:
            changed = migrate_file(filepath)
            if changed:
                migrated.append(rel)
                print(f"  [OK] {rel}")
            else:
                print(f"  [--] {rel} (no changes)")
        except Exception as e:
            failed.append((rel, str(e)))
            print(f"  [ERR] {rel}: {e}")

    print(f"\n=== Summary ===")
    print(f"Migrated: {len(migrated)}")
    print(f"Failed: {len(failed)}")
    if failed:
        for name, err in failed:
            print(f"  - {name}: {err}")


if __name__ == "__main__":
    main()
