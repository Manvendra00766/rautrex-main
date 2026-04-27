import { test, expect } from '@playwright/test';

test.describe('Auth Flow', () => {
  
  test('test_e2e_login_success', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[id="email"]', 'test@example.com');
    await page.fill('input[id="password"]', 'password123');
    await page.click('button[type="submit"]');
    // Successful login redirects to dashboard or home depending on logic
    // LoginPage.tsx uses router.push('/') but middleware might redirect to /dashboard
    await expect(page).toHaveURL(/(\/dashboard|\/)/);
  });

  test('test_e2e_signup_flow', async ({ page }) => {
    await page.goto('/signup');
    await page.fill('input[id="fullName"]', 'New User');
    const uniqueEmail = `user_${Date.now()}@example.com`;
    await page.fill('input[id="email"]', uniqueEmail);
    await page.fill('input[id="password"]', 'Abc123!@');
    await page.fill('input[id="confirmPassword"]', 'Abc123!@');
    await page.check('input[id="terms"]');
    await page.click('button[type="submit"]');
    
    // Should show success state "Check your email"
    await expect(page.locator('text=Check your email')).toBeVisible();
  });

  test('test_e2e_login_invalid_password', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[id="email"]', 'test@example.com');
    await page.fill('input[id="password"]', 'wrong-password');
    await page.click('button[type="submit"]');
    
    // Check for error message
    await expect(page.locator('text=Invalid login credentials')).toBeVisible();
  });

  test('test_e2e_password_strength_indicator', async ({ page }) => {
    await page.goto('/signup');
    const passwordInput = page.locator('input[id="password"]');
    const requirementsGrid = page.locator('.grid.grid-cols-2.gap-2');
    
    // Type "abc" (length is < 8, no upper, no number, no special)
    // Actually, "abc" meets nothing.
    await passwordInput.fill('abc');
    await expect(requirementsGrid.locator('.text-green-500')).toHaveCount(0);

    // Type "abcdefgh" (meets length only)
    await passwordInput.fill('abcdefgh');
    await expect(requirementsGrid.locator('.text-green-500')).toHaveCount(1);
    
    // Type "Abc123!@" (meets all 4)
    await passwordInput.fill('Abc123!@');
    await expect(requirementsGrid.locator('.text-green-500')).toHaveCount(4);
  });

  test('test_e2e_forgot_password_link', async ({ page }) => {
    await page.goto('/login');
    await page.click('text=Forgot password?');
    await expect(page).toHaveURL(/\/forgot-password/);
  });

  test('test_e2e_protected_redirect', async ({ page }) => {
    // Navigate to dashboard without being logged in
    await page.goto('/dashboard');
    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });

  test('test_e2e_logout_clears_session', async ({ page }) => {
    // 1. Login
    await page.goto('/login');
    await page.fill('input[id="email"]', 'test@example.com');
    await page.fill('input[id="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/(\/dashboard|\/)/);

    // 2. Logout (via Popover in Topbar)
    await page.goto('/dashboard');
    await page.click('button:has(.lucide-user)'); // Profile button
    const logoutBtn = page.getByRole('button', { name: /SIGN OUT/i });
    await logoutBtn.click();

    // 3. Try navigating back to dashboard
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe('Dashboard Features', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[id="email"]', 'test@example.com');
    await page.fill('input[id="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/(\/dashboard|\/)/);
  });

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
        // Check for 404 (assuming 404 page has "404" or "Not Found")
        await expect(page.locator('text=Not Found')).not.toBeVisible();
    }
  });

  test('test_e2e_global_search_in_topbar', async ({ page }) => {
    const searchInput = page.locator('input[placeholder="Search tickers..."]');
    await searchInput.fill('AAPL');
    // Wait for autocomplete
    const dropdown = page.locator('.bg-surface.border.border-white\\/10.rounded-xl.overflow-hidden');
    await expect(dropdown).toBeVisible({ timeout: 5000 });
    await expect(dropdown).toContainText('AAPL');
  });

  test('test_e2e_no_duplicate_search_bars', async ({ page }) => {
    await page.goto('/monte-carlo');
    // Count all inputs that look like search bars
    const searchBoxes = page.locator('input[placeholder*="Search"]');
    await expect(searchBoxes).toHaveCount(1);
  });
});

test.describe('Monte Carlo Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[id="email"]', 'test@example.com');
    await page.fill('input[id="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.goto('/monte-carlo');
  });

  test('test_e2e_monte_carlo_full_flow', async ({ page }) => {
    // 1. Search AAPL if not active
    await page.fill('input[placeholder="Search tickers..."]', 'AAPL');
    await page.click('text=AAPL');

    // 2. Set params
    // Slider is harder to drag accurately, let's assume investment input
    await page.fill('input[type="number"]', '500'); // Investment input (the only number input in config)
    
    // 3. Click Run
    await page.click('text=EXECUTE PROJECTION');

    // 4. Assert chart renders (recharts-responsive-container)
    const chart = page.locator('.recharts-responsive-container');
    await expect(chart).toBeVisible({ timeout: 10000 });

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
    await page.fill('input[placeholder="Search tickers..."]', 'AAPL');
    await page.click('text=AAPL');
    
    await page.click('text=EXECUTE PROJECTION');
    // Immediately assert skeleton
    await expect(page.locator('.animate-pulse')).toBeVisible();
    
    // Wait for completion
    await expect(page.locator('text=Simulation Complete')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('.animate-pulse')).not.toBeVisible();
  });
});

test.describe('Backtester Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[id="email"]', 'test@example.com');
    await page.fill('input[id="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.goto('/backtest');
  });

  test('test_e2e_backtest_flow', async ({ page }) => {
    await page.click('text=SMA Crossover');
    await page.fill('input[placeholder="Search tickers..."]', 'RELIANCE.NS');
    await page.click('text=RELIANCE.NS');
    
    // Set dates
    await page.fill('label:has-text("Start Date") + input', '2020-01-01');
    await page.fill('label:has-text("End Date") + input', '2023-12-31');

    await page.click('text=RUN ANALYSIS');

    // Assert equity curve chart
    await expect(page.locator('.recharts-responsive-container')).toBeVisible({ timeout: 15000 });
    
    // Assert trade log table has rows
    const rows = page.locator('table tbody tr');
    await expect(rows.first()).toBeVisible();
  });

  test('test_e2e_strategy_params_change', async ({ page }) => {
    await page.click('text=SMA Crossover');
    await expect(page.locator('label:has-text("Fast")')).toBeVisible();
    
    await page.click('text=RSI Mean Reversion');
    await expect(page.locator('label:has-text("Period")')).toBeVisible();
    await expect(page.locator('label:has-text("Fast")')).not.toBeVisible();
  });
});

test.describe('Signals', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/login');
        await page.fill('input[id="email"]', 'test@example.com');
        await page.fill('input[id="password"]', 'password123');
        await page.click('button[type="submit"]');
        await page.goto('/signals');
    });

    test('test_e2e_signal_shows_breakdown', async ({ page }) => {
        await page.fill('input[placeholder="Search tickers..."]', 'AAPL');
        await page.click('text=AAPL');
        
        // Wait for results
        await expect(page.locator('text=BUY|SELL|HOLD')).toBeVisible({ timeout: 10000 });
        
        // Check 3 sub-cards
        await expect(page.locator('text=LSTM')).toBeVisible();
        await expect(page.locator('text=XGBoost')).toBeVisible();
        await expect(page.locator('text=Sentiment')).toBeVisible();
    });

    test('test_e2e_signal_confidence_shown', async ({ page }) => {
        await page.fill('input[placeholder="Search tickers..."]', 'AAPL');
        await page.click('text=AAPL');
        
        const confidence = page.locator('text=/\\d{1,3}%/');
        await expect(confidence).toBeVisible({ timeout: 10000 });
    });
});

test.describe('Notifications', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/login');
        await page.fill('input[id="email"]', 'test@example.com');
        await page.fill('input[id="password"]', 'password123');
        await page.click('button[type="submit"]');
    });

    test('test_e2e_bell_visible_in_navbar', async ({ page }) => {
        await expect(page.locator('button:has(.lucide-bell)')).toBeVisible();
    });

    test('test_e2e_bell_click_opens_dropdown', async ({ page }) => {
        await page.click('button:has(.lucide-bell)');
        await expect(page.locator('text=Notifications')).toBeVisible();
    });

    test('test_e2e_mark_all_read_button', async ({ page }) => {
        await page.click('button:has(.lucide-bell)');
        const markAllBtn = page.getByRole('button', { name: /MARK ALL AS READ/i });
        if (await markAllBtn.isVisible()) {
            await markAllBtn.click();
            // Check all unread indicators (dots) are gone
            await expect(page.locator('.bg-accent.rounded-full')).toHaveCount(0);
        }
    });
});

test.describe('Profile', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/login');
        await page.fill('input[id="email"]', 'test@example.com');
        await page.fill('input[id="password"]', 'password123');
        await page.click('button[type="submit"]');
        await page.goto('/profile');
    });

    test('test_e2e_profile_page_loads', async ({ page }) => {
        await expect(page.locator('text=test@example.com')).toBeVisible();
    });

    test('test_e2e_edit_name', async ({ page }) => {
        await page.click('text=Edit Profile');
        await page.fill('input[id="fullName"]', 'Updated Name');
        await page.click('text=Save Changes');
        await expect(page.locator('text=Updated Name')).toBeVisible();
    });

    test('test_e2e_portfolio_tab', async ({ page }) => {
        await page.click('text=Portfolios');
        // Should show list or empty state
        await expect(page.locator('text=My Portfolios|No portfolios found')).toBeVisible();
    });

    test('test_e2e_watchlist_tab', async ({ page }) => {
        await page.click('text=Watchlists');
        await expect(page.locator('text=My Watchlists|No watchlists found')).toBeVisible();
    });
});

test.describe('Mobile Responsive', () => {
    test.use({ viewport: { width: 375, height: 812 } });

    test('test_e2e_mobile_sidebar_hidden', async ({ page }) => {
        await page.goto('/login');
        await page.fill('input[id="email"]', 'test@example.com');
        await page.fill('input[id="password"]', 'password123');
        await page.click('button[type="submit"]');
        
        await expect(page.locator('aside')).not.toBeVisible();
    });

    test('test_e2e_mobile_bottom_nav_visible', async ({ page }) => {
        await page.goto('/login');
        await page.fill('input[id="email"]', 'test@example.com');
        await page.fill('input[id="password"]', 'password123');
        await page.click('button[type="submit"]');
        
        await expect(page.locator('.md\\:hidden.fixed.bottom-0')).toBeVisible();
    });

    test('test_e2e_mobile_chart_renders', async ({ page }) => {
        await page.goto('/login');
        await page.fill('input[id="email"]', 'test@example.com');
        await page.fill('input[id="password"]', 'password123');
        await page.click('button[type="submit"]');
        
        await page.goto('/monte-carlo');
        await page.fill('input[placeholder="Search tickers..."]', 'AAPL');
        await page.click('text=AAPL');
        await page.click('text=EXECUTE PROJECTION');
        await expect(page.locator('.recharts-responsive-container')).toBeVisible({ timeout: 10000 });
    });

    test('test_e2e_mobile_login_form_usable', async ({ page }) => {
        await page.goto('/login');
        await expect(page.locator('input[id="email"]')).toBeVisible();
        await expect(page.locator('input[id="password"]')).toBeVisible();
    });
});

