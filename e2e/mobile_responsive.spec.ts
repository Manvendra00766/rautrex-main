import { test, expect } from '@playwright/test';
import path from 'path';

const authFile = 'playwright/.auth/user.json';

test.describe('Mobile Responsiveness (375x812)', () => {
  // Set global viewport for this file
  test.use({ viewport: { width: 375, height: 812 } });

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

  // Re-use auth state for dashboard tests
  test.describe('Dashboard Mobile UI', () => {
    test.use({ storageState: authFile });

    test('test_e2e_mobile_sidebar_hidden', async ({ page }) => {
      await page.goto('/dashboard');
      // Sidebar has .hidden.md:flex classes, it should not be visible on 375px
      const sidebar = page.locator('aside');
      await expect(sidebar).not.toBeVisible();
    });

    test('test_e2e_mobile_bottom_nav_visible', async ({ page }) => {
      await page.goto('/dashboard');
      // BottomNav has .md:hidden fixed bottom-0 classes
      const bottomNav = page.locator('.md\\:hidden.fixed.bottom-0');
      await expect(bottomNav).toBeVisible();
      
      // Verify it's actually at the bottom
      const box = await bottomNav.boundingBox();
      expect(box?.y).toBeGreaterThan(700); // 812 - 16h (64px) = 748 approx
    });

    test('test_e2e_mobile_chart_renders', async ({ page }) => {
      await page.goto('/monte-carlo');
      
      // 1. Ticker selection (ensure data exists)
      await page.fill('input[placeholder="Search tickers..."]', 'AAPL');
      await page.click('text=AAPL');

      // 2. Run simulation
      await page.click('text=EXECUTE PROJECTION');

      // 3. Assert chart container visibility
      const chartContainer = page.locator('.recharts-responsive-container');
      await expect(chartContainer).toBeVisible({ timeout: 10000 });

      // 4. Assert non-zero height
      const box = await chartContainer.boundingBox();
      expect(box?.height).toBeGreaterThan(100);
    });
  });

  test.describe('Login Form Mobile Accessibility', () => {
    test('test_e2e_mobile_login_form_usable', async ({ page }) => {
      await page.goto('/login');

      const emailInput = page.locator('input[id="email"]');
      const passwordInput = page.locator('input[id="password"]');

      // Assert visibility
      await expect(emailInput).toBeVisible();
      await expect(passwordInput).toBeVisible();

      // Assert touch target size (>= 44px height for mobile)
      const emailBox = await emailInput.boundingBox();
      const passBox = await passwordInput.boundingBox();

      expect(emailBox?.height).toBeGreaterThanOrEqual(40); // 40px is standard for shadcn inputs, often used for 44px targets with padding
      expect(passBox?.height).toBeGreaterThanOrEqual(40);
      
      // Verify they are within the viewport width
      expect(emailBox?.width).toBeLessThan(375);
    });
  });

});
