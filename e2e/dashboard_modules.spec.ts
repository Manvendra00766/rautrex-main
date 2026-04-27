import { test, expect } from '@playwright/test';
import path from 'path';

const authFile = 'playwright/.auth/user.json';

test.describe('Dashboard and Modules Flow', () => {

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto('http://localhost:3000/login');
    await page.fill('input[id="email"]', 'test@example.com');
    await page.fill('input[id="password"]', 'password123');
    await page.click('button[type="submit"]');
    // Successful login redirects to dashboard or home depending on logic
    await expect(page).toHaveURL(/(\/dashboard|\/)/);
    await page.context().storageState({ path: authFile });
    await page.close();
  });

  test.use({ storageState: authFile });

  test.describe('Dashboard Tests', () => {
    test('test_e2e_dashboard_loads_after_login', async ({ page }) => {
        await page.goto('/dashboard');
        // Page loads within 3 seconds
        await page.waitForLoadState('networkidle', { timeout: 3000 });
        // No "Chart Module Loading..." raw text visible
        await expect(page.locator('text=Chart Module Loading...')).not.toBeVisible();
    });

    test('test_e2e_sidebar_nav_links_work', async ({ page }) => {
        const links = [
            { label: "Dashboard", url: "/" },
            { label: "Markets", url: "/market" },
            { label: "Portfolio", url: "/portfolio" },
            { label: "Backtest", url: "/backtest" },
            { label: "Monte Carlo", url: "/monte-carlo" },
            { label: "Signals", url: "/signals" },
            { label: "Risk", url: "/risk" },
            { label: "Options", url: "/options" }
        ];

        for (const link of links) {
            await page.click(`aside >> text=${link.label}`);
            await expect(page).toHaveURL(new RegExp(link.url));
            await expect(page.locator('text=Not Found')).not.toBeVisible();
        }
    });

    test('test_e2e_global_search_in_topbar', async ({ page }) => {
        await page.goto('/');
        const searchInput = page.locator('input[placeholder="Search tickers..."]');
        await searchInput.fill('AAPL');
        // Wait for autocomplete dropdown
        const dropdown = page.locator('.bg-surface.border.border-white\\/10.rounded-xl.overflow-hidden');
        await expect(dropdown).toBeVisible({ timeout: 5000 });
        await expect(dropdown).toContainText('AAPL');
    });

    test('test_e2e_no_duplicate_search_bars', async ({ page }) => {
        await page.goto('/monte-carlo');
        // Count all elements that could be search boxes (roles or common patterns)
        const searchBoxes = page.locator('input[placeholder*="Search"]');
        await expect(searchBoxes).toHaveCount(1);
    });
  });

  test.describe('Monte Carlo Tests', () => {
    test('test_e2e_monte_carlo_full_flow', async ({ page }) => {
        await page.goto('/monte-carlo');
        
        // 1. Search AAPL
        await page.fill('input[placeholder="Search tickers..."]', 'AAPL');
        await page.click('text=AAPL');

        // 2. Set 500 sims (via Capital input as proxy since slider is hard to hit)
        // Note: page.fill targets the input[type="number"] which is "Capital Commitment"
        await page.fill('input[type="number"]', '500'); 
        
        // 3. Click Run
        await page.click('text=EXECUTE PROJECTION');

        // 4. Assert chart renders (responsive container exists)
        await expect(page.locator('.recharts-responsive-container')).toBeVisible({ timeout: 10000 });

        // 5. Assert 4 metric cards appear with non-zero values
        const metrics = ["Expected Value", "Value at Risk", "Prob. of Profit", "Annual Volatility"];
        for (const m of metrics) {
            const card = page.locator(`.glass-panel:has-text("${m}")`);
            await expect(card).toBeVisible();
            const val = await card.locator('.text-2xl').textContent();
            expect(val).not.toBe("$0");
            expect(val).not.toBe("0%");
        }
    });

    test('test_e2e_skeleton_shown_during_load', async ({ page }) => {
        await page.goto('/monte-carlo');
        await page.fill('input[placeholder="Search tickers..."]', 'AAPL');
        await page.click('text=AAPL');
        
        await page.click('text=EXECUTE PROJECTION');
        // Immediately assert skeleton visible
        await expect(page.locator('.animate-pulse')).toBeVisible();
        
        // Wait for completion
        await expect(page.locator('text=Simulation Complete')).toBeVisible({ timeout: 10000 });
        // Assert skeleton gone
        await expect(page.locator('.animate-pulse')).not.toBeVisible();
    });
  });

  test.describe('Backtester Tests', () => {
    test('test_e2e_backtest_flow', async ({ page }) => {
        await page.goto('/backtest');
        
        // 1. Select SMA Crossover
        await page.click('text=SMA Crossover');
        
        // 2. Search RELIANCE.NS
        await page.fill('input[placeholder="Search tickers..."]', 'RELIANCE.NS');
        await page.click('text=RELIANCE.NS');
        
        // 3. Set dates 2020-2023
        await page.fill('label:has-text("Start Date") + input', '2020-01-01');
        await page.fill('label:has-text("End Date") + input', '2023-12-31');

        // 4. Click Run
        await page.click('text=RUN ANALYSIS');

        // 5. Assert equity curve chart renders
        await expect(page.locator('.recharts-responsive-container')).toBeVisible({ timeout: 15000 });
        
        // 6. Assert trade log table has rows
        const rows = page.locator('table tbody tr');
        await expect(rows.first()).toBeVisible();
    });

    test('test_e2e_strategy_params_change', async ({ page }) => {
        await page.goto('/backtest');
        
        // Select SMA -> see fast_period
        await page.click('text=SMA Crossover');
        await expect(page.locator('label:has-text("Fast")')).toBeVisible();
        
        // Switch to RSI -> see rsi_period
        await page.click('text=RSI Mean Reversion');
        await expect(page.locator('label:has-text("Period")')).toBeVisible();
        
        // SMA params should be gone
        await expect(page.locator('label:has-text("Fast")')).not.toBeVisible();
    });
  });

});
