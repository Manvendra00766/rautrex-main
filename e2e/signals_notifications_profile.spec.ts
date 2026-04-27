import { test, expect } from '@playwright/test';
import path from 'path';

const authFile = 'playwright/.auth/user.json';

test.describe('Signals, Notifications, and Profile Flow', () => {

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto('http://localhost:3000/login');
    await page.fill('input[id="email"]', 'test@example.com');
    await page.fill('input[id="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/(\/dashboard|\/)/);
    await page.context().storageState({ path: authFile });
    await page.close();
  });

  test.use({ storageState: authFile });

  test.describe('Signals Tests', () => {
    test('test_e2e_signal_shows_breakdown', async ({ page }) => {
        await page.goto('/signals');
        
        // 1. Search AAPL
        await page.fill('input[placeholder="Search tickers..."]', 'AAPL');
        await page.click('text=AAPL');
        
        // 2. Run Pipeline
        await page.click('text=RUN AI PIPELINE');

        // 3. Signal card shows BUY/SELL/HOLD
        await expect(page.locator('text=/BUY|SELL|HOLD/')).toBeVisible({ timeout: 20000 });

        // 4. Check 3 sub-cards: LSTM, XGBoost, Sentiment
        await expect(page.locator('text=LSTM Sequence Analysis')).toBeVisible();
        await expect(page.locator('text=XGBoost Feature Importance')).toBeVisible();
        await expect(page.locator('text=NLP Sentiment Score')).toBeVisible();
    });

    test('test_e2e_signal_confidence_shown', async ({ page }) => {
        await page.goto('/signals');
        await page.fill('input[placeholder="Search tickers..."]', 'AAPL');
        await page.click('text=AAPL');
        await page.click('text=RUN AI PIPELINE');

        // Confidence percentage displayed (e.g., @85.5%)
        const confidence = page.locator('text=/\\d{1,3}\\.\\d{1}%/');
        await expect(confidence).toBeVisible({ timeout: 20000 });
    });
  });

  test.describe('Notifications Tests', () => {
    test('test_e2e_bell_visible_in_navbar', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('button:has(.lucide-bell)')).toBeVisible();
    });

    test('test_e2e_bell_click_opens_dropdown', async ({ page }) => {
        await page.goto('/');
        await page.click('button:has(.lucide-bell)');
        // Dropdown contains "Notifications" heading
        await expect(page.locator('h3:has-text("Notifications")')).toBeVisible();
    });

    test('test_e2e_mark_all_read_button', async ({ page }) => {
        await page.goto('/');
        await page.click('button:has(.lucide-bell)');
        
        const markAllBtn = page.getByRole('button', { name: /MARK ALL AS READ/i });
        
        // If button is enabled (meaning unread exist)
        if (await markAllBtn.isEnabled()) {
            await markAllBtn.click();
            // All unread indicators (the blue dots/lines) should be gone
            // The unread line is `div.absolute.left-0.top-0.bottom-0.w-1.bg-accent`
            await expect(page.locator('.bg-accent.w-1')).toHaveCount(0);
        }
    });
  });

  test.describe('Profile Tests', () => {
    test('test_e2e_profile_page_loads', async ({ page }) => {
        await page.goto('/profile');
        // Check for email and current name (or placeholder)
        await expect(page.locator('text=test@example.com')).toBeVisible();
        await expect(page.locator('input[id="fullName"]')).toBeVisible();
    });

    test('test_e2e_edit_name', async ({ page }) => {
        await page.goto('/profile');
        const newName = `E2E User ${Date.now()}`;
        await page.fill('input[id="fullName"]', newName);
        await page.click('button:has-text("Save Changes")');
        
        // After save, the header name should update
        await expect(page.locator('h3:has-text("' + newName + '")')).toBeVisible();
    });

    test('test_e2e_portfolio_tab', async ({ page }) => {
        await page.goto('/profile');
        await page.click('button[role="tab"]:has-text("Portfolios")');
        // Table or empty state
        await expect(page.locator('text=/Name|No portfolios found/')).toBeVisible();
    });

    test('test_e2e_watchlist_tab', async ({ page }) => {
        await page.goto('/profile');
        await page.click('button[role="tab"]:has-text("Watchlists")');
        // Table or empty state
        await expect(page.locator('text=/Name|No watchlists found/')).toBeVisible();
    });
  });

});
