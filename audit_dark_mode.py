import re

with open('templates/dashboard_enterprise.html', 'r') as f:
    lines = f.readlines()

def find_selector(lines, line_idx):
    """Walk backwards to find the CSS selector for a given property line"""
    for i in range(line_idx - 1, max(0, line_idx - 30), -1):
        line = lines[i].strip()
        if '{' in line:
            sel = line.split('{')[0].strip()
            if sel:
                return sel, i + 1
            for j in range(i - 1, max(0, i - 5), -1):
                prev = lines[j].strip()
                if prev and not prev.startswith('/*') and not prev.startswith('*'):
                    return prev, j + 1
    return 'UNKNOWN', line_idx

def is_in_dark_mode_block(lines, idx):
    """Check if line index is inside a body.dark-mode CSS block"""
    brace_depth = 0
    for j in range(idx, max(0, idx - 80), -1):
        line = lines[j]
        brace_depth += line.count('}') - line.count('{')
        if 'body.dark-mode' in line or 'html.dark-mode' in line:
            return True
        if brace_depth > 0:
            return False
    return False

# 1. Find all backdrop-filter with blur in base CSS
print('=' * 80)
print('BACKDROP-FILTER (with blur) in BASE CSS (not dark-mode)')
print('=' * 80)
for idx, line in enumerate(lines):
    stripped = line.strip()
    if 'backdrop-filter' in stripped and 'blur' in stripped and 'none' not in stripped:
        if '-webkit-backdrop-filter' in stripped:
            continue
        if is_in_dark_mode_block(lines, idx):
            continue
        sel, sel_line = find_selector(lines, idx)
        print(f'  L{idx+1}: [{sel}]  =>  {stripped}')

# 2. High-opacity white backgrounds
print()
print('=' * 80)
print('HIGH-OPACITY rgba(255,255,255,X) BACKGROUNDS (X >= 0.45) in BASE CSS')
print('=' * 80)
for idx, line in enumerate(lines):
    stripped = line.strip()
    if 'background' not in stripped:
        continue
    matches = re.findall(r'rgba\(255\s*,\s*255\s*,\s*255\s*,\s*([\d.]+)\)', stripped)
    for m in matches:
        val = float(m)
        if val >= 0.45:
            if is_in_dark_mode_block(lines, idx):
                continue
            sel, sel_line = find_selector(lines, idx)
            print(f'  L{idx+1}: [{sel}] (opacity={m})  =>  {stripped[:140]}')
            break

# 3. White inset shadows with high opacity
print()
print('=' * 80)
print('INSET BOX-SHADOW with rgba(255,255,255,X) (X >= 0.4) in BASE CSS')
print('=' * 80)
for idx, line in enumerate(lines):
    stripped = line.strip()
    if 'inset' not in stripped or 'box-shadow' not in stripped:
        continue
    # Find all inset shadows with white rgba
    shadow_matches = re.findall(r'inset[^,;]*rgba\(255\s*,\s*255\s*,\s*255\s*,\s*([\d.]+)\)', stripped)
    for m in shadow_matches:
        val = float(m)
        if val >= 0.4:
            if is_in_dark_mode_block(lines, idx):
                continue
            sel, sel_line = find_selector(lines, idx)
            print(f'  L{idx+1}: [{sel}] (opacity={m})  =>  {stripped[:160]}')
            break
