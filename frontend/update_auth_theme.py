import os
import re

directory = r'D:\projects\rautrex-main\frontend\app\(dashboard)\(auth)'

replacements = {
    r'rgba\(\s*255\s*,\s*255\s*,\s*255\s*,': r'rgba(0,0,0,',
    r'#0d0d14': r'#FDF6EC',
    r'#1a1a24': r'#FDF6EC',
    r'bg-white/10': r'bg-black/5',
    r'bg-white/20': r'bg-black/10',
    r'text-white/60': r'text-[#8C8278]',
    r'text-white/80': r'text-[#2B2A27]',
    r'border-white/10': r'border-black',
    r'border-white/20': r'border-black',
    r'hover:bg-white/5': r'hover:bg-black/5',
    r'hover:bg-white/10': r'hover:bg-black/10',
    r'hover:text-white': r'hover:text-[#2B2A27]',
    r'stroke="#fff"': r'stroke="#000"',
    r'stroke="#FFFFFF"': r'stroke="#000"',
    r'fill="#fff"': r'fill="#000"',
    r'fill="#FFFFFF"': r'fill="#000"',
    r'text-white': r'text-[#2B2A27]',
    r'text-gray-400': r'text-[#8C8278]',
    r'border-\[#333\]': r'border-black',
    r'border-\[#222\]': r'border-black',
    r'border-gray-800': r'border-black',
    r'border-gray-700': r'border-black',
    r'#00d4ff': r'#8B6F47',
    
    r'bg-surface': r'bg-[#FDF6EC]',
    r'bg-\[#0d0d14\]': r'bg-[#FDF6EC]',
    r'bg-white/5': r'bg-black/5',
    r'border-white/5': r'border-black',
    r'glass-panel': r'bg-[#FDF6EC] border border-black shadow-sm'
}

for root, dirs, files in os.walk(directory):
    for file in files:
        if file.endswith('.tsx'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            for pattern, repl in replacements.items():
                content = re.sub(pattern, repl, content)
                
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f'Updated {filepath}')
print('Auth/Onboarding theme updated!')
