import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# Debug print
print("EMAIL:", EMAIL)
print("PASSWORD:", PASSWORD)

# Fail early if creds are missing
if not EMAIL or not PASSWORD:
    print("❌ ERROR: EMAIL or PASSWORD not found in .env file.")
    exit()

# Session persistence file
SESSION_FILE = "session_state.txt"

# Load last page if session exists
if os.path.exists(SESSION_FILE):
    with open(SESSION_FILE, "r") as f:
        page = int(f.read().strip() or "1")
else:
    page = 1

# Setup driver
options = Options()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)

# Login
driver.get("https://app.shopcanal.com/login")

WebDriverWait(driver, 60).until(
    EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter email address']"))
).send_keys(EMAIL)
driver.find_element(By.XPATH, "//input[@placeholder='Enter password']").send_keys(PASSWORD)
driver.find_element(By.XPATH, "//button[.//span[contains(text(), 'Sign in')]]").click()
print("✅ Logged in")

# Flip account
try:
    account_tiles = WebDriverWait(driver, 60).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#team-card-button > span > div"))
    )
    for tile in account_tiles:
        if "flip" in tile.text.strip().lower():
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", tile)
            driver.execute_script("arguments[0].click();", tile)
            print("✅ Clicked the correct 'flip' account.")
            break
except Exception as e:
    driver.save_screenshot("error_flip_account_match.png")
    print("❌ Failed to click the 'flip' account — see error_flip_account_match.png")
    driver.quit()
    exit()

# Retailer selection
try:
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "appTypestorefrontRadio"))).click()
    print("✅ Selected 'Retailer' radio.")
    WebDriverWait(driver, 60).until(
        EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Continue']]"))
    ).click()
    print("➡️ Clicked 'Continue' after selecting Retailer.")
except Exception as e:
    driver.save_screenshot("error_retailer_continue.png")
    print("❌ Retailer step failed — see error_retailer_continue.png")
    driver.quit()
    exit()

# Inventory tab
try:
    WebDriverWait(driver, 60).until(
        EC.element_to_be_clickable((By.XPATH, "//span[normalize-space(text())='Inventory']"))
    ).click()
    print("📦 Clicked 'Inventory' tab.")
except Exception as e:
    driver.save_screenshot("error_inventory_click.png")
    print("❌ Failed to click Inventory tab — see error_inventory_click.png")
    driver.quit()
    exit()

# Log file setup
log_path = "synced_products_log.txt"

# Infinite pagination loop
print("🔁 Starting infinite resync loop...")
while True:
    url = f"https://app.shopcanal.com/shopkeep/inventory?page={page}"
    driver.get(url)
    print(f"\n🌐 Loaded page {page}")

    try:
        WebDriverWait(driver, 60).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "i.sc-f88a7778-0.cMYjQI.ri-refresh-line"))
        )
        icons = driver.find_elements(By.CSS_SELECTOR, "i.sc-f88a7778-0.cMYjQI.ri-refresh-line")
        if not icons:
            print("✅ No resync icons — restarting at page 1.")
            page = 1
            continue

        print(f"🔁 Found {len(icons)} buttons on page {page}")
        for i in range(len(icons)):
            try:
                icons = driver.find_elements(By.CSS_SELECTOR, "i.sc-f88a7778-0.cMYjQI.ri-refresh-line")
                icon = icons[i]
                button = icon.find_element(By.XPATH, "./ancestor::button")
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", button)
                print(f"   🔄 Clicked Resync icon {i+1}")

                # Get product title from nearby context
                try:
                    product_container = button.find_element(By.XPATH, "./ancestor::div[contains(@class,'sc')]")
                    title_el = product_container.find_element(By.XPATH, ".//p")
                    title = title_el.text.strip()
                except:
                    title = "Unknown Title"

                checkbox = WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@type='checkbox' and @value='all']"))
                )
                if not checkbox.get_attribute("checked"):
                    driver.execute_script("arguments[0].click();", checkbox)
                    print("      ☑️ Clicked 'Select All' checkbox.")

                resync_btn = WebDriverWait(driver, 60).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Resync']"))
                )
                driver.execute_script("arguments[0].click();", resync_btn)
                print("      🔁 Clicked 'Resync'.")

                WebDriverWait(driver, 60).until_not(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Resync']"))
                )

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(log_path, "a") as log_file:
                    log_file.write(f"{timestamp} - {title}\n")

                print(f"      ✅ Modal closed — Logged: {title}")
                time.sleep(1.2)

            except Exception as e:
                print(f"   ⚠️ Skipped item {i+1} on page {page} due to: {e}")
                continue

    except TimeoutException:
        print(f"⚠️ Timeout — no icons found on page {page}. Restarting at 1.")
        page = 1
        continue

    # Save current page to session file
    with open(SESSION_FILE, "w") as f:
        f.write(str(page))

    page += 1
