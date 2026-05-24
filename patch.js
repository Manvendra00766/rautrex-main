const fs = require('fs');

const files = [
    'frontend/app/(dashboard)/dashboard/backtest/page.tsx',
    'frontend/app/(dashboard)/dashboard/compare/page.tsx',
    'frontend/app/(dashboard)/dashboard/monte-carlo/page.tsx',
    'frontend/app/(dashboard)/dashboard/options/page.tsx',
    'frontend/app/(dashboard)/dashboard/portfolio/page.tsx',
    'frontend/app/(dashboard)/dashboard/risk/page.tsx',
    'frontend/app/(dashboard)/dashboard/signals/page.tsx',
    'frontend/app/(dashboard)/dashboard/strategy/page.tsx',
    'frontend/components/dcf/CompareMode.tsx',
    'frontend/components/dcf/DCFCalculator.tsx',
    'frontend/components/dcf/ShareableFCFChart.tsx',
    'frontend/components/paper-trading/PaperTradingDashboard.tsx',
    'frontend/components/ui/DefaultChart.tsx'
];

files.forEach(file => {
    let content = fs.readFileSync(file, 'utf8');
    let changed = false;

    if (content.includes('<ResponsiveContainer') && !content.includes('<ChartWrapper')) {
        if (!content.includes('import ChartWrapper')) {
            const lines = content.split('\n');
            let lastImportIndex = -1;
            for (let i = 0; i < lines.length; i++) {
                if (lines[i].startsWith('import ')) {
                    lastImportIndex = i;
                }
            }
            if (lastImportIndex !== -1) {
                lines.splice(lastImportIndex + 1, 0, `import ChartWrapper from '@/components/ChartWrapper';`);
                content = lines.join('\n');
                changed = true;
            }
        }

        content = content.replace(/<ResponsiveContainer([^>]*)>/g, '<ChartWrapper height={300}>\n<ResponsiveContainer$1>');
        content = content.replace(/<\/ResponsiveContainer>/g, '</ResponsiveContainer>\n</ChartWrapper>');
        changed = true;
    }

    if (changed) {
        fs.writeFileSync(file, content, 'utf8');
        console.log('Patched', file);
    }
});
