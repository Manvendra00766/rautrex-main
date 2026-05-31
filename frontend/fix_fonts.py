import os
import re

directories = [
    r'D:\projects\rautrex-main\frontend\app\(dashboard)',
    r'D:\projects\rautrex-main\frontend\app\(auth)',
    r'D:\projects\rautrex-main\frontend\components'
]

font_replacements = {
    r'text-\[9px\]': r'text-xs',
    r'text-\[10px\]': r'text-xs',
    r'text-\[11px\]': r'text-xs'
}

for d in directories:
    for root, dirs, files in os.walk(d):
        for file in files:
            if file.endswith('.tsx'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                original_content = content
                for pattern, repl in font_replacements.items():
                    content = re.sub(pattern, repl, content)
                    
                if content != original_content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f'Updated font sizes in {filepath}')

print('Font sizes fixed!')
