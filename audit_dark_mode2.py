import re

with open('templates/dashboard_enterprise.html', 'r') as f:
    content = f.read()
    lines = content.split('\n')

# Selectors that need dark mode overrides - from the audit above
# Format: (selector, issue_type, line, description)
problems = [
    # BACKDROP-FILTER
    ('.header', 'backdrop-filter', 342, 'blur(8px)'),
    ('.ph-stat-card', 'backdrop-filter', 1550, 'blur(10px) saturate(130%)'),
    ('.post-history-toolbar', 'backdrop-filter', 1594, 'blur(10px) saturate(130%)'),
    ('.history-item', 'backdrop-filter', 1764, 'blur(10px) saturate(130%)'),
    ('.creator-v4 .cv-topbar', 'backdrop-filter', 4029, 'blur(20px)'),
    ('.creator-v4 .cv-tbs-item', 'backdrop-filter', 4205, 'blur(8px)'),
    ('.creator-v4 .cv-float-gen-inner', 'backdrop-filter', 5468, 'blur(22px)'),
    ('.creator-v4 .cv-insights-topbar', 'backdrop-filter', 5562, 'blur(20px)'),
    ('.creator-v4 .cv-insights-col .insight-panel', 'backdrop-filter', 5905, 'blur(16px)'),
    ('.creator-v4 .cvv-score-card', 'backdrop-filter', 6002, 'blur(20px)'),
    ('.kb-template-modal', 'backdrop-filter', 9480, 'blur(6px)'),
    ('.sc-hero-icon', 'backdrop-filter', 10140, 'blur(10px) saturate(130%)'),
    ('.sc-status-pill', 'backdrop-filter', 10160, 'blur(8px) saturate(130%)'),
    ('.sc-samples-panel, .sc-results-panel', 'backdrop-filter', 10240, 'blur(10px) saturate(130%)'),
    ('.sc-add-btn', 'backdrop-filter', 10275, 'blur(8px)'),
    ('.sc-sample-v2', 'backdrop-filter', 10291, 'blur(8px) saturate(125%)'),
    ('.sc-empty-icon', 'backdrop-filter', 10369, 'blur(10px)'),
    ('.sc-samples-panel (2nd)', 'backdrop-filter', 10557, 'blur(12px) saturate(125%)'),
    ('.sc-samples-panel .sc-sample-v2', 'backdrop-filter', 10604, 'blur(7px)'),
    ('.rp-hero-icon', 'backdrop-filter', 11053, 'blur(16px)'),
    ('.ph2-hero', 'backdrop-filter', 11506, 'blur(12px) saturate(130%)'),
    ('#dashboard .quick-actions-card', 'backdrop-filter', 11920, 'blur(14px) saturate(135%)'),
    ('#dashboard .usage-meter', 'backdrop-filter', 11969, 'blur(8px)'),
    ('.setup-card-featured .setup-badge', 'backdrop-filter', 12179, 'blur(8px)'),
    ('.usage-plan-pill', 'backdrop-filter', 12379, 'blur(8px)'),
    ('.kb-v4 .kb4-storage-chip', 'backdrop-filter', 12615, 'blur(8px)'),
    ('.kb-v4 .kb4-chip', 'backdrop-filter', 12634, 'blur(8px)'),
    ('.kb-v4 .track-scroll-btn', 'backdrop-filter', 13331, 'blur(8px)'),
    ('.kb-v4 .kb-file-item', 'backdrop-filter', 13578, 'blur(8px)'),
    ('.kb-v4 .kb-template-card', 'backdrop-filter', 13754, 'blur(8px)'),
    ('.kb-template-modal (2nd)', 'backdrop-filter', 14024, 'blur(10px) !important'),
    ('#cmd-overlay', 'backdrop-filter', 28099, 'blur(8px)'),
    ('#upgrade-modal-overlay', 'backdrop-filter', 28502, 'blur(6px)'),

    # HIGH-OPACITY WHITE BG
    ('.header', 'white-bg', 341, 'rgba(255,255,255,0.92)'),
    ('.ph-stat-card', 'white-bg', 1542, 'rgba(255,255,255,0.88)'),
    ('.post-history-toolbar', 'white-bg', 1589, 'rgba(255,255,255,0.88)'),
    ('.ph-status-tabs', 'white-bg', 1685, 'rgba(255,255,255,0.88)'),
    ('.ph-layout-btn', 'white-bg', 1737, 'rgba(255,255,255,0.88)'),
    ('.history-item', 'white-bg', 1761, 'rgba(255,255,255,0.9)'),
    ('.ph-page-btn', 'white-bg', 1975, 'rgba(255,255,255,0.9)'),
    ('.skeleton::after', 'white-bg', 3798, 'linear-gradient with rgba(255,255,255,0.75)'),
    ('.kb-v4 .kb4-upload-drop', 'white-bg', 8640, 'rgba(255,255,255,0.75)'),
    ('.kb-v4 .kb4-upload-drop:hover', 'white-bg', 8646, 'rgba(255,255,255,0.9)'),
    ('.sc-steps', 'white-bg', 10524, 'linear-gradient with rgba(255,255,255,0.96)'),
    ('.sc-samples-panel', 'white-bg', 10553, 'linear-gradient with rgba(255,255,255,0.95)'),
    ('.sc-samples-panel .sc-sample-v2 textarea', 'white-bg', 10624, 'rgba(255,255,255,0.55)'),
    ('.setup-card-featured::before', 'white-bg', 12151, 'linear-gradient with rgba(255,255,255,0.65)'),
    ('.usage-card::before', 'white-bg', 12352, 'linear-gradient with rgba(255,255,255,0.65)'),

    # INSET SHADOWS
    ('.next-post-content-wrap', 'inset-shadow', 1035, 'inset rgba(255,255,255,0.6)'),
    ('.ph-stat-card', 'inset-shadow', 1549, 'inset rgba(255,255,255,0.65)'),
    ('.ph-stat-card:hover', 'inset-shadow', 1557, 'inset rgba(255,255,255,0.75)'),
    ('.post-history-toolbar', 'inset-shadow', 1593, 'inset rgba(255,255,255,0.65)'),
    ('.history-item', 'inset-shadow', 1763, 'inset rgba(255,255,255,0.68)'),
    ('.history-item:hover', 'inset-shadow', 1785, 'inset rgba(255,255,255,0.78)'),
    ('.kb-v4 .kb4-status-head .kb-ready-banner', 'inset-shadow', 8955, 'inset rgba(255,255,255,0.55)'),
    ('.sc-steps', 'inset-shadow', 10526, 'inset rgba(255,255,255,0.75)'),
    ('.sc-samples-panel', 'inset-shadow', 10556, 'inset rgba(255,255,255,0.8)'),
    ('.sc-samples-panel .sc-sample-v2', 'inset-shadow', 10603, 'inset rgba(255,255,255,0.78)'),
    ('#dashboard .quick-actions-card', 'inset-shadow', 11959, 'inset rgba(255,255,255,0.72)'),
]

# Now check each selector for dark mode overrides
# Search for body.dark-mode versions
print('=' * 90)
print('DARK MODE OVERRIDE CHECK')
print('=' * 90)

# Gather unique selectors
unique_selectors = {}
for sel, itype, line, desc in problems:
    sel_clean = sel.replace(' (2nd)', '')
    if sel_clean not in unique_selectors:
        unique_selectors[sel_clean] = []
    unique_selectors[sel_clean].append((itype, line, desc))

# For each selector, search for body.dark-mode version
for sel, issues in sorted(unique_selectors.items(), key=lambda x: x[1][0][1]):
    # Build search patterns
    sel_escaped = re.escape(sel)
    # Search for body.dark-mode <sel>
    dark_patterns = [
        f'body.dark-mode {sel}',
        f'body.dark-mode\n{sel}',
    ]
    
    # Simple text search
    found_dark = False
    dark_lines = []
    dark_content = ''
    for i, line in enumerate(lines):
        for dp in dark_patterns:
            if dp.replace('\n', '') in line.replace('\n', ''):
                found_dark = True
                # Read the block
                block = ''
                for k in range(i, min(len(lines), i + 20)):
                    block += lines[k] + '\n'
                    if '}' in lines[k] and k > i:
                        break
                dark_lines.append(i + 1)
                dark_content += block
    
    # Also try broader search
    if not found_dark:
        # Try searching for the selector within dark-mode context  
        for i, line in enumerate(lines):
            if sel.replace('.', '').replace(' ', '') in line.replace(' ', '') and 'dark-mode' in line:
                found_dark = True
                block = ''
                for k in range(i, min(len(lines), i + 15)):
                    block += lines[k] + '\n'
                    if '}' in lines[k] and k > i:
                        break
                dark_lines.append(i + 1)
                dark_content += block
    
    print(f'\n--- {sel} ---')
    for itype, line, desc in issues:
        print(f'  BASE: L{line} [{itype}] {desc}')
    
    if found_dark:
        # Check what properties are overridden
        has_backdrop_none = 'backdrop-filter: none' in dark_content or 'backdrop-filter:none' in dark_content
        has_bg_override = 'background:' in dark_content or 'background-color:' in dark_content
        has_shadow_none = 'box-shadow: none' in dark_content or 'box-shadow:none' in dark_content
        has_shadow_override = 'box-shadow:' in dark_content or 'box-shadow :' in dark_content
        
        print(f'  DARK MODE FOUND at line(s): {dark_lines}')
        
        for itype, line, desc in issues:
            if itype == 'backdrop-filter':
                if has_backdrop_none:
                    print(f'    [OK] backdrop-filter: none found')
                else:
                    print(f'    [NEEDS FIX] backdrop-filter NOT reset to none')
            elif itype == 'white-bg':
                if has_bg_override:
                    print(f'    [OK] background override found')
                else:
                    print(f'    [NEEDS FIX] white background NOT overridden')
            elif itype == 'inset-shadow':
                if has_shadow_none or has_shadow_override:
                    print(f'    [OK] box-shadow override found')
                else:
                    print(f'    [NEEDS FIX] inset white shadow NOT killed')
    else:
        print(f'  [NO DARK MODE OVERRIDE] - ALL issues NEED FIXING')
        for itype, line, desc in issues:
            print(f'    [NEEDS FIX] {itype}: {desc}')
