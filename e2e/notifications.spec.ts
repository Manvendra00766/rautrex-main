import { test, expect } from '@playwright/test';

/**
 * These tests assume a running backend at http://localhost:8000
 * and a frontend at http://localhost:3000.
 */

test.describe('Notifications Realtime E2E', () => {
  
  test.beforeEach(async ({ page }) => {
    // Simple login flow
    await page.goto('/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/dashboard/);
    
    // Ensure we are on a clean state or handle existing notifications
    // (In a real CI, we'd use a fresh test user or seed the DB)
  });

  test('test_e2e_realtime_notification_appears', async ({ page, request }) => {
    // Capture current badge count if any
    const bellButton = page.locator('button:has(.lucide-bell)');
    const initialBadge = await bellButton.locator('span').textContent().catch(() => "0");
    const initialCount = parseInt(initialBadge || "0");

    // Trigger notification via API
    // Note: In a real environment, we'd need an auth token for this request
    const response = await request.post('http://localhost:8000/api/v1/test/trigger-notification', {
      data: {
        user_email: 'test@example.com',
        type: 'signal',
        title: 'E2E Realtime Noti',
        body: 'This should appear instantly'
      }
    });
    expect(response.ok()).toBeTruthy();

    // Verify bell badge increments within 3s without page refresh
    const badge = bellButton.locator('span');
    await expect(badge).toHaveText((initialCount + 1).toString(), { timeout: 3000 });
    
    // Verify toast appears
    await expect(page.locator('text=E2E Realtime Noti')).toBeVisible();
  });

  test('test_e2e_mark_all_read_clears_badge', async ({ page, request }) => {
    // Seed 3 notifications
    for (let i = 1; i <= 3; i++) {
        await request.post('http://localhost:8000/api/v1/test/trigger-notification', {
            data: {
              user_email: 'test@example.com',
              type: 'system',
              title: `Seed ${i}`,
              body: 'Seeding'
            }
        });
    }

    // Wait for badge to show at least 3
    const bellButton = page.locator('button:has(.lucide-bell)');
    await expect(bellButton.locator('span')).not.toHaveText('0', { timeout: 5000 });

    // Open dropdown
    await bellButton.click();
    
    // Click "Mark all read"
    const markAllBtn = page.getByRole('button', { name: /MARK ALL AS READ/i });
    await markAllBtn.click();

    // Badge should disappear
    await expect(bellButton.locator('span')).not.toBeVisible();
  });

  test('test_e2e_price_alert_triggers_notification', async ({ page, request }) => {
    // 1. Create alert
    await page.goto('/alerts');
    await page.click('text=Create Alert');
    await page.fill('input[name="ticker"]', 'TSLA');
    await page.selectOption('select[name="condition"]', 'above');
    await page.fill('input[name="target_price"]', '250');
    await page.click('button:has-text("Save Alert")');

    // 2. Mock price crossing (via test endpoint that triggers checker with fake price)
    const triggerRes = await request.post('http://localhost:8000/api/v1/test/mock-price-trigger', {
        data: {
            ticker: 'TSLA',
            price: 251
        }
    });
    expect(triggerRes.ok()).toBeTruthy();

    // 3. Notification appears within 10s
    await expect(page.locator('text=TSLA price target reached')).toBeVisible({ timeout: 10000 });
    
    const bellButton = page.locator('button:has(.lucide-bell)');
    await expect(bellButton.locator('span')).toBeVisible();
  });
});
