import os
import sys
import time
import urllib.parse
from datetime import datetime, UTC
import requests

# Load environment variables
from dotenv import load_dotenv
if os.path.exists("backend/.env"):
    load_dotenv("backend/.env")
elif os.path.exists(".env"):
    load_dotenv(".env")
else:
    load_dotenv()


# We try to import custom dependencies if installed
try:
    import pyotp
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_INSTALLED = True
except ImportError:
    PLAYWRIGHT_INSTALLED = False

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
UPSTOX_CLIENT_ID = os.getenv("UPSTOX_CLIENT_ID")
UPSTOX_CLIENT_SECRET = os.getenv("UPSTOX_CLIENT_SECRET")
UPSTOX_REDIRECT_URI = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:8000/api/v1/onboarding/upstox-callback")

# Credentials for auto login
USER_ID = os.getenv("UPSTOX_USER_ID")  # Mobile number or Client ID
PIN = os.getenv("UPSTOX_PIN")          # 4-digit or 6-digit PIN
TOTP_SECRET = os.getenv("UPSTOX_TOTP_SECRET") # TOTP Key (e.g. from Google Authenticator setup)
USER_EMAIL = os.getenv("USER_EMAIL")  # Email of profile to update

def auto_login():
    if not PLAYWRIGHT_INSTALLED:
        print("=" * 80)
        print("ERROR: Missing automated login dependencies!")
        print("Please install them using the following command:")
        print("    pip install pyotp playwright")
        print("    playwright install chromium")
        print("=" * 80)
        return False

    if not all([SUPABASE_URL, SUPABASE_KEY, UPSTOX_CLIENT_ID, UPSTOX_CLIENT_SECRET]):
        print("Error: Missing basic server credentials in .env (SUPABASE_URL, SUPABASE_KEY, UPSTOX_CLIENT_ID, UPSTOX_CLIENT_SECRET).")
        return False
        
    if not all([USER_ID, PIN, TOTP_SECRET, USER_EMAIL]):
        print("Error: Automated login credentials missing in .env (UPSTOX_USER_ID, UPSTOX_PIN, UPSTOX_TOTP_SECRET, USER_EMAIL).")
        return False

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Generating 2FA TOTP code programmatically...")
    totp = pyotp.TOTP(TOTP_SECRET.replace(" ", ""))
    current_otp = totp.now()

    encoded_redirect = urllib.parse.quote(UPSTOX_REDIRECT_URI)
    auth_url = f"https://api.upstox.com/v2/login/authorization/dialog?client_id={UPSTOX_CLIENT_ID}&redirect_uri={encoded_redirect}&response_type=code"

    # Auto-detect: run headless in CI/cloud, show browser locally for debugging
    is_headless = os.getenv("CI") == "true" or os.getenv("HEADLESS", "false").lower() == "true"
    print(f"Launching {'headless ' if is_headless else ''}browser to authorize session...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=is_headless)
            # Create a 100% clean, fresh context with standard desktop user agent
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            # Listen to browser console logs and errors
            page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))
            page.on("pageerror", lambda err: print(f"[Browser JS Error] {err}"))
            # Bot evasion: bypass navigator.webdriver automated detection
            page.add_init_script("delete navigator.__proto__.webdriver;")

            # ── Register auth code capture listeners EARLY (before any navigation) ──
            captured_code = [None]

            def handle_navigation(frame):
                url = frame.url
                if "code=" in url:
                    parsed = urllib.parse.urlparse(url)
                    params = urllib.parse.parse_qs(parsed.query)
                    code = params.get("code", [None])[0]
                    if code:
                        captured_code[0] = code
                        print(f"[OK] Captured auth code from navigation: {code[:8]}...")

            def handle_request(request):
                url = request.url
                if "code=" in url:
                    parsed = urllib.parse.urlparse(url)
                    params = urllib.parse.parse_qs(parsed.query)
                    code = params.get("code", [None])[0]
                    if code:
                        captured_code[0] = code
                        print(f"[OK] Captured auth code from request: {code[:8]}...")

            def handle_response(response):
                url = response.url
                if "code=" in url:
                    parsed = urllib.parse.urlparse(url)
                    params = urllib.parse.parse_qs(parsed.query)
                    code = params.get("code", [None])[0]
                    if code:
                        captured_code[0] = code
                        print(f"[OK] Captured auth code from response: {code[:8]}...")

            page.on("framenavigated", handle_navigation)
            page.on("request", handle_request)
            page.on("response", handle_response)

            page.goto(auth_url, wait_until="domcontentloaded")
 
            # ── Step 1: Mobile Number screen ──
            print("Step 1/4: Entering login ID...")
            page.wait_for_selector("#mobileNum, input[name='mobileNumber'], input[type='text']", timeout=15000)
            input_field = page.locator("#mobileNum, input[name='mobileNumber'], input[type='text']").first
            input_field.focus()
            input_field.fill("")
            input_field.type(USER_ID, delay=80)
            
            input_field.press("Tab")
            time.sleep(1)
            
            submit_btn = page.locator("button[type='submit'], #submit-btn, button:has-text('Get OTP'), button:has-text('get OTP')").first
            submit_btn.focus()
            submit_btn.click(force=True)
            page.keyboard.press("Enter")
            
            # ── Step 2: OTP screen ──
            print("Step 2/4: Waiting for OTP screen...")
            page.wait_for_selector("text=Verify your number", timeout=15000)
            time.sleep(2)
            
            print("Step 2/4: Entering TOTP code...")
            otp_selector = "input[name='otp'], input[type='number'], input[type='text'], #otp, #mobileNum, input"
            otp_field = page.locator(otp_selector).first
            otp_field.focus()
            otp_field.fill("")
            otp_field.type(current_otp, delay=80)
            
            time.sleep(1)
            continue_btn = page.locator("button:has-text('Continue'), button[type='submit']").first
            continue_btn.click()
            
            # ── Step 3: PIN screen ──
            print("Step 3/4: Waiting for PIN screen...")
            page.wait_for_selector("input[type='password'], input[name='pin'], #pin", timeout=15000)
            time.sleep(1)

            print("Step 3/4: Entering PIN...")
            pin_selector = "input[name='pin'], input[type='password'], #pin"
            pin_field = page.locator(pin_selector).first
            pin_field.focus()
            pin_field.fill("")
            pin_field.type(PIN, delay=80)
            
            time.sleep(1)
            final_btn = page.locator("button[type='submit'], button:has-text('Continue')").first
            final_btn.click()
            
            # ── Step 4: Handle Authorize screen OR direct redirect ──
            print("Step 4/4: Waiting for authorization...")
            
            # Give the page time to transition
            time.sleep(3)
            
            # Check if we already got the code from listeners
            if not captured_code[0]:
                # Check if there's an "Authorize" / "Allow" / "Approve" confirmation screen
                try:
                    authorize_btn = page.locator(
                        "button:has-text('Authorize'), "
                        "button:has-text('Allow'), "
                        "button:has-text('Approve'), "
                        "button:has-text('Accept'), "
                        "button:has-text('Confirm'), "
                        "input[value='Authorize'], "
                        "a:has-text('Authorize')"
                    )
                    if authorize_btn.count() > 0:
                        print("  --> Found 'Authorize' button. Clicking...")
                        authorize_btn.first.click()
                        time.sleep(3)
                    else:
                        print("  --> No authorize button found, checking for redirect...")
                except Exception:
                    pass
            
            # Wait for redirect with code in URL
            if not captured_code[0]:
                try:
                    page.wait_for_url(lambda u: "code=" in u, timeout=15000)
                except Exception:
                    print("  --> URL wait timed out, checking current URL...")
            
            # Fallback: extract code directly from current page URL
            if not captured_code[0]:
                current_url = page.url
                print(f"  --> Current URL: {current_url[:80]}...")
                if "code=" in current_url:
                    parsed = urllib.parse.urlparse(current_url)
                    params = urllib.parse.parse_qs(parsed.query)
                    code_val = params.get("code", [None])[0]
                    if code_val:
                        captured_code[0] = code_val
                        print(f"[OK] Extracted auth code from page URL: {code_val[:8]}...")

            # Fallback: check all frames
            if not captured_code[0]:
                for frame in page.frames:
                    frame_url = frame.url
                    if "code=" in frame_url:
                        parsed = urllib.parse.urlparse(frame_url)
                        params = urllib.parse.parse_qs(parsed.query)
                        code_val = params.get("code", [None])[0]
                        if code_val:
                            captured_code[0] = code_val
                            print(f"[OK] Extracted auth code from frame: {code_val[:8]}...")
                            break

            # Save debug screenshot before closing if code not found
            if not captured_code[0]:
                try:
                    screenshot_path = "backend/logs/login_debug_screenshot.png"
                    os.makedirs("backend/logs", exist_ok=True)
                    page.screenshot(path=screenshot_path, full_page=True)
                    print(f"  --> Debug screenshot saved: {screenshot_path}")
                    # Also dump the page content for analysis
                    page_text = page.inner_text("body")
                    print(f"  --> Page text: {page_text[:300]}...")
                except Exception as dbg_err:
                    print(f"  --> Debug capture failed: {dbg_err}")

            code = captured_code[0]
            browser.close()
            
            if not code:
                print("[FAIL] Failed to capture authorization code. Check the debug screenshot in backend/logs/")
                return False

            print(f"[OK] Session authorized! Exchanging code: {code[:8]}... for access token.")
            
            # ── Step 5: Exchange code for token ──
            token_url = "https://api.upstox.com/v2/login/authorization/token"
            payload = {
                "code": code,
                "client_id": UPSTOX_CLIENT_ID,
                "client_secret": UPSTOX_CLIENT_SECRET,
                "redirect_uri": UPSTOX_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            
            res = requests.post(token_url, data=payload, headers=headers, timeout=15)
            if res.status_code != 200:
                print(f"[FAIL] Token exchange failed ({res.status_code}): {res.text}")
                return False
                
            token_data = res.json()
            access_token = token_data.get("access_token", "")
            token_data["broker"] = "upstox"
            token_data["fetched_at"] = datetime.now(tz=UTC).isoformat()
            
            print(f"[OK] Access token received: {access_token[:12]}...")
            
            # ── Step 6: Save in Supabase ──
            print("Saving token to Supabase...")
            from supabase import create_client
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            
            # Find the profile that has broker_oauth set (the Upstox-connected user)
            # The profiles table uses 'id' (UUID), not 'email'
            profile_res = supabase.table("profiles").select("id").not_.is_("broker_oauth", "null").execute()
            if profile_res.data:
                for row in profile_res.data:
                    user_id = row["id"]
                    supabase.table("profiles").update({"broker_oauth": token_data}).eq("id", user_id).execute()
                    print(f"  Updated token for user: {user_id}")
            else:
                # Fallback: if no profile has broker_oauth yet, update the first profile
                all_profiles = supabase.table("profiles").select("id").limit(1).execute()
                if all_profiles.data:
                    user_id = all_profiles.data[0]["id"]
                    supabase.table("profiles").update({"broker_oauth": token_data}).eq("id", user_id).execute()
                    print(f"  Set token for first profile: {user_id}")
                else:
                    print("[FAIL] No profiles found in database to save token to!")
            
            print("=" * 60)
            print("[OK] SUCCESS: Upstox token refreshed! Active for 24 hours.")
            print(f"  Token: {access_token[:12]}...")
            print(f"  Saved at: {token_data['fetched_at']}")
            print("=" * 60)
            return True
            
        except Exception as e:
            print(f"[FAIL] Error during browser automation: {e}")
            try:
                screenshot_path = "backend/logs/login_error_screenshot.png"
                os.makedirs("backend/logs", exist_ok=True)
                page.screenshot(path=screenshot_path, full_page=True)
                print(f"  --> Error screenshot saved: {screenshot_path}")
            except Exception as ss_err:
                print(f"  --> Could not capture screenshot: {ss_err}")
            try:
                browser.close()
            except:
                pass
            return False

if __name__ == "__main__":
    try:
        success = auto_login()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
