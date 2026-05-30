import logging
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, WebDriverException, 
    NoSuchWindowException, NoSuchElementException, 
    ElementNotInteractableException
)
import pandas as pd
import time
import random
from datetime import datetime
import json                                          # ← NEW

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

##################################################
# PARSING HELPER FUNCTIONS (for smart data extraction)
##################################################
DATE_PATTERN = re.compile(r'\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s+\d{2}:\d{2}')

STATUS_KEYWORDS = [
    'Gate out Empty', 'Gate out for delivery', 'Gate out', 'Gate in',
    'Load on', 'Discharge', 'Vessel arrival', 'Vessel departure',
    'On rail', 'Off rail', 'Rail departure', 'Rail arrival',
    'Empty container return'
]

def is_datetime(text):
    """Check if text matches the Maersk datetime format"""
    if text is None or text == '' or str(text) == 'nan':
        return False
    return bool(DATE_PATTERN.search(str(text)))

def is_status(text):
    """Check if text is a status field"""
    if text is None or text == '' or str(text) == 'nan':
        return False
    text_str = str(text)
    for keyword in STATUS_KEYWORDS:
        if keyword.lower() in text_str.lower():
            return True
    return False

##################################################
# Initialize Chrome options with ANTI-DETECTION
##################################################
def initialize_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    
    # ===== ANTI-DETECTION FEATURES =====
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    # ====================================
    
    chromedriver_path = r"C:\Users\ngodu\OneDrive - CEVA Logistics\Desktop\chromedriver-win64\chromedriver.exe"
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # ===== REMOVE WEBDRIVER PROPERTY =====
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })
    # ======================================

    driver.set_page_load_timeout(20)
    return driver

##################################################
# Main script setup
##################################################
print("="*70)
print("MAERSK CONTAINER TRACKING SCRAPER")
print("WITH ANTI-DETECTION FEATURES ⚡")
print("="*70)

print("\n🌐 Opening Chrome browser with anti-detection features...")
driver = initialize_driver()
print("✓ Browser opened")

print("🔗 Loading Maersk tracking page...")
driver.get("https://www.maersk.com/tracking/")
time.sleep(2)
print("✓ Page loaded")

print("🧹 Closing extra tabs...")
try:
    main_window = driver.current_window_handle
    all_windows = driver.window_handles
    for window in all_windows:
        if window != main_window:
            driver.switch_to.window(window)
            driver.close()
    driver.switch_to.window(main_window)
    print(f"✓ Closed {len(all_windows) - 1} extra tab(s)")
except Exception as e:
    print(f"⚠ Could not close extra tabs: {e}")

print("\n" + "="*70)
print("⏸ PAUSED - YOUR TURN!")
print("="*70)
print("\n🎯 IN THE BROWSER WINDOW:")
print("   1. Log in if required")
print("   2. Complete any CAPTCHA/bot verification if it appears")
print("   3. Wait for the tracking page to load completely")
print("\n✅ WHEN YOU'RE READY:")
print("   Come back here and press ENTER to start automation")
print("="*70)
input("\n⏯ Press ENTER to continue...")

wait = WebDriverWait(driver, 20)

excel_path = r"C:\Users\ngodu\OneDrive - CEVA Logistics\Desktop\Report\AP-GMNA rep\Base reports\Webscraping\MAEU.xlsx"

print(f"\n📋 Loading container list from Excel...")

if not os.path.exists(excel_path):
    print(f"❌ ERROR: Excel file not found at: {excel_path}")
    driver.quit()
    input("\nPress ENTER to exit...")
    exit()

try:
    df = pd.read_excel(excel_path)
    print(f"✓ Loaded {len(df)} containers to process")
except PermissionError:
    print(f"❌ ERROR: Cannot access Excel file - it may be open in Excel")
    print(f"   Please close the file and try again")
    print(f"   File: {excel_path}")
    driver.quit()
    input("\nPress ENTER to exit...")
    exit()
except Exception as e:
    print(f"❌ ERROR: Failed to read Excel file: {str(e)}")
    driver.quit()
    input("\nPress ENTER to exit...")
    exit()

output_dir = os.path.dirname(excel_path)
print(f"📁 Output directory: {output_dir}")

print("🤖 Starting automation...\n")

##################################################
# Function to retrieve rows from the table
##################################################
def get_rows_from_table(tracking_number):
    try:
        table = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="transport-plan__container__0"]/ul'))
        )
        time.sleep(0.5)
        
        rows = table.find_elements(By.TAG_NAME, "li")
        all_rows = []
        
        for row in rows:
            try:
                row_text = row.text.strip()
                if not row_text:
                    continue
                
                row_parts = row_text.split('\n')
                
                row_data = {
                    'Container_Number': tracking_number,
                    'Type_of_Tracking': 'Current Tracking',
                    'Raw_Data': row_text,
                    'Row_Parts': row_parts
                }
                
                all_rows.append(row_data)
                
            except Exception as e:
                logging.warning(f"Error extracting row data: {e}")
                continue
        
        logging.info(f"Extracted {len(all_rows)} events for container {tracking_number}")
        return all_rows
    
    except TimeoutException:
        logging.error(f"Timed out waiting for data table for container {tracking_number}")
        return []
    except WebDriverException as e:
        logging.error(f"WebDriverException while extracting table: {e}")
        return []

##################################################
# Retry mechanism for handling failures
##################################################
def process_container_with_retry(container_id, retries=3):
    attempts = 0
    while attempts < retries:
        try:
            success = process_container(container_id)
            if success:
                return True
        except Exception as e:
            logging.error(f"Attempt {attempts + 1} failed for container {container_id}: {e}")
        attempts += 1
        time.sleep(1)

    logging.error(f"All {retries} attempts failed for container {container_id}.")
    return False

##################################################
# Main function to process each container
##################################################
def process_container(container_id):
    global driver, wait
    try:
        if not driver.current_window_handle:
            logging.warning("Browser window is closed. Reinitializing driver.")
            driver.quit()
            driver = initialize_driver()
            wait = WebDriverWait(driver, 20)
            print("\n⚠ Browser was closed. Please manually navigate and log in again.")
            input("Press ENTER after you're ready to continue...")
            return False

        logging.info(f"Step 1: Looking for search box...")
        
        search_box = None
        
        try:
            logging.info("   Method 1: Accessing shadow DOM...")
            mc_input_elements = driver.find_elements(By.TAG_NAME, 'mc-input')
            
            if mc_input_elements:
                mc_input = mc_input_elements[0]
                shadow_root = driver.execute_script('return arguments[0].shadowRoot', mc_input)
                if shadow_root:
                    search_box = shadow_root.find_element(By.CSS_SELECTOR, 'input')
                    logging.info("✓ Found input inside shadow DOM")
        except Exception as e:
            logging.warning(f"   Method 1 (shadow DOM) failed: {e}")
        
        if not search_box:
            try:
                logging.info("   Method 2: Looking for input with name='track-input'...")
                search_box = WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[name="track-input"]'))
                )
                logging.info("✓ Found search box by name='track-input'")
            except TimeoutException:
                logging.warning("   Method 2 failed")
        
        if not search_box:
            try:
                logging.info("   Method 3: Finding any visible text input...")
                all_inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="text"]')
                for inp in all_inputs:
                    try:
                        if inp.is_displayed() and inp.is_enabled():
                            search_box = inp
                            logging.info("✓ Using visible text input")
                            break
                    except:
                        continue
            except Exception as e:
                logging.warning(f"   Method 3 failed: {e}")
        
        if not search_box:
            logging.error("❌ Could not find search box with any method!")
            try:
                screenshot_path = os.path.join(output_dir, f"error_screenshot_{container_id}_{datetime.now().strftime('%H%M%S')}.png")
                driver.save_screenshot(screenshot_path)
                logging.info(f"Screenshot saved to: {screenshot_path}")
            except:
                pass
            return True
        
        if search_box is None:
            logging.error("Search box is None, skipping container")
            return True
        
        logging.info(f"Step 2: Preparing to interact with search box...")
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_box)
        time.sleep(0.3)
        
        logging.info("   Clicking on input field...")
        clicked = False
        
        try:
            actions = ActionChains(driver)
            actions.move_to_element(search_box).click().perform()
            logging.info("   ✓ Clicked with Actions")
            clicked = True
        except Exception as e:
            logging.warning(f"   Actions click failed: {e}")
        
        if not clicked:
            try:
                driver.execute_script("arguments[0].click();", search_box)
                logging.info("   ✓ Clicked with JavaScript")
                clicked = True
            except Exception as e:
                logging.warning(f"   JavaScript click failed: {e}")
        
        if not clicked:
            try:
                search_box.click()
                logging.info("   ✓ Clicked with regular click")
            except Exception as e:
                logging.warning(f"   Regular click failed: {e}")
        
        time.sleep(0.3)
        
        driver.execute_script("arguments[0].focus();", search_box)
        time.sleep(0.2)
        
        logging.info(f"Step 3: Clearing search box...")
        
        driver.execute_script("arguments[0].value = '';", search_box)
        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", search_box)
        time.sleep(0.1)
        
        for _ in range(3):
            try:
                search_box.send_keys(Keys.CONTROL + "a")
                search_box.send_keys(Keys.BACKSPACE)
                time.sleep(0.05)
            except:
                pass
        
        try:
            for _ in range(50):
                search_box.send_keys(Keys.BACKSPACE)
        except:
            pass
        
        driver.execute_script("arguments[0].value = '';", search_box)
        time.sleep(0.2)
        
        current_value = search_box.get_attribute('value')
        if current_value and current_value != '':
            logging.warning(f"   Field still contains: '{current_value}' - one more aggressive clear...")
            driver.execute_script("""
                arguments[0].value = '';
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, search_box)
            time.sleep(0.2)
        
        final_value = search_box.get_attribute('value')
        if not final_value or final_value == '':
            logging.info(f"   ✓ Field cleared successfully")
        else:
            logging.warning(f"   ⚠ Field still has: '{final_value}'")
        
        logging.info(f"Step 4: Entering container ID: {container_id}...")
        try:
            for char in container_id:
                search_box.send_keys(char)
                time.sleep(0.03)
            logging.info(f"✓ Entered container ID: {container_id}")
        except Exception as e:
            logging.warning(f"Regular input failed, trying JavaScript method: {e}")
            driver.execute_script("arguments[0].value = arguments[1];", search_box, container_id)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", search_box)
            logging.info(f"✓ Entered container ID via JavaScript: {container_id}")
        
        entered_value = search_box.get_attribute('value')
        if entered_value != container_id:
            logging.warning(f"Input verification failed! Expected: {container_id}, Got: {entered_value}")
            logging.info("Attempting JavaScript method as backup...")
            driver.execute_script("arguments[0].value = arguments[1];", search_box, container_id)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", search_box)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", search_box)
        
        time.sleep(0.3)

        logging.info(f"Step 5: Looking for Track button...")
        track_button = None
        try:
            logging.info("   Method 1: Looking for mc-button with data-test='track-button'...")
            track_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'mc-button[data-test="track-button"]'))
            )
            logging.info("✓ Found Track button by data-test")
        except TimeoutException:
            try:
                logging.info("   Method 2: Looking for mc-button with 'Track' text...")
                buttons = driver.find_elements(By.TAG_NAME, "mc-button")
                for btn in buttons:
                    if "track" in btn.text.lower():
                        track_button = btn
                        logging.info("✓ Found Track button by text in mc-button")
                        break
            except Exception as e:
                logging.warning(f"   Method 2 failed: {e}")
            
            if not track_button:
                try:
                    logging.info("   Method 3: Looking for any button with 'Track' text...")
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        if "track" in btn.text.lower():
                            track_button = btn
                            logging.info("✓ Found Track button (regular button)")
                            break
                except Exception as e:
                    logging.warning(f"   Method 3 failed: {e}")
            
            if not track_button:
                try:
                    logging.info("   Method 4: By button text XPath...")
                    track_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, '//button[text()="Track"]'))
                    )
                    logging.info("✓ Found Track button by XPath text")
                except TimeoutException:
                    logging.error("❌ Could not find Track button with any method!")
                    try:
                        screenshot_path = os.path.join(output_dir, f"error_trackbutton_{container_id}_{datetime.now().strftime('%H%M%S')}.png")
                        driver.save_screenshot(screenshot_path)
                        logging.info(f"Screenshot saved to: {screenshot_path}")
                    except:
                        pass
                    return True
        
        if track_button is None:
            logging.error("Track button is None, skipping container")
            return True
        
        logging.info(f"Step 6: Clicking Track button...")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", track_button)
        time.sleep(0.3)
        
        try:
            track_button.click()
            logging.info("   ✓ Clicked with regular click")
        except:
            driver.execute_script("arguments[0].click();", track_button)
            logging.info("   ✓ Clicked with JavaScript")
        
        logging.info(f"✓ Searching for container {container_id}...")

        time.sleep(1.5)
        
        logging.info(f"Step 7: Checking for results...")
        try:
            no_results = driver.find_elements(By.XPATH, "//*[contains(text(), 'No results') or contains(text(), 'not found') or contains(text(), 'could not be found')]")
            if no_results:
                logging.info(f"No results found for {container_id}. Skipping.")
                all_matching_rows.append({
                    'Container_Number': container_id,
                    'Type_of_Tracking': 'Current Tracking',
                    'Status': 'Container Not Found',
                    'Location': '',
                    'Date': '',
                    'Time': '',
                    'Vessel_Name': '',
                    'Transport': ''
                })
                return True
        except Exception as e:
            logging.warning(f"Error checking for no results: {e}")

        logging.info(f"Step 8: Extracting data from table...")
        matching_rows = get_rows_from_table(container_id)
        
        if len(matching_rows) > 0:
            all_matching_rows.extend(matching_rows)
            logging.info(f"✓ Successfully extracted {len(matching_rows)} rows for {container_id}")
        else:
            logging.warning(f"No data extracted for {container_id}")
            try:
                screenshot_path = os.path.join(output_dir, f"nodata_{container_id}_{datetime.now().strftime('%H%M%S')}.png")
                driver.save_screenshot(screenshot_path)
                logging.info(f"Screenshot saved to: {screenshot_path}")
            except:
                pass

        return True

    except NoSuchWindowException as e:
        logging.error(f"Window closed unexpectedly while processing container {container_id}: {e}")
        logging.warning("Reinitializing driver.")
        driver.quit()
        driver = initialize_driver()
        wait = WebDriverWait(driver, 20)
        print("\n⚠ Browser was closed. Please manually navigate and log in again.")
        input("Press ENTER after you're ready to continue...")
        return False

    except NoSuchElementException as e:
        logging.error(f"Element not found for container {container_id}: {e}")
        return True

    except ElementNotInteractableException as e:
        logging.error(f"Element not interactable for container {container_id}: {e}")
        return True

    except TimeoutException as e:
        logging.error(f"Timeout while processing container {container_id}: {e}")
        try:
            screenshot_path = os.path.join(output_dir, f"timeout_{container_id}_{datetime.now().strftime('%H%M%S')}.png")
            driver.save_screenshot(screenshot_path)
            logging.info(f"Screenshot saved to: {screenshot_path}")
            print(f"⚠ Timeout on container {container_id} - screenshot saved for debugging")
        except:
            pass
        return True

    except WebDriverException as e:
        error_message = str(e)
        logging.error(f"WebDriverException encountered while processing container {container_id}: {error_message}")

        if "Timed out receiving message from renderer" in error_message or "timeout" in error_message.lower():
            logging.warning("Renderer timeout detected. Continuing to next container...")
            return True

        return True

##################################################
# Iterate through the Excel data
##################################################
all_matching_rows = []
containers_processed = 0

try:
    for index, row in df.iterrows():
        container_id = row.iloc[0]
        logging.info(f"Processing container {index + 1}/{len(df)}: {container_id}")
        
        if containers_processed > 0 and containers_processed % 100 == 0:
            print("\n" + "="*70)
            print(f"🔄 RESTART CHECKPOINT - {containers_processed} containers processed")
            print("="*70)
            print("Closing current browser and opening fresh instance...")
            
            try:
                driver.quit()
                print("✓ Browser closed")
            except:
                pass
            
            time.sleep(2)
            
            print("🌐 Opening fresh Chrome browser...")
            driver = initialize_driver()
            print("✓ New browser opened")
            
            print("🔗 Loading Maersk tracking page...")
            driver.get("https://www.maersk.com/tracking/")
            time.sleep(3)
            print("✓ Page loaded")
            
            try:
                main_window = driver.current_window_handle
                all_windows = driver.window_handles
                for window in all_windows:
                    if window != main_window:
                        driver.switch_to.window(window)
                        driver.close()
                driver.switch_to.window(main_window)
                if len(all_windows) > 1:
                    print(f"✓ Closed {len(all_windows) - 1} extra tab(s)")
            except:
                pass
            
            wait = WebDriverWait(driver, 20)
            
            print("\n⏸ PAUSED FOR VERIFICATION")
            print("="*70)
            print("🎯 CHECK THE BROWSER:")
            print("   • If CAPTCHA appears, solve it now")
            print("   • If you see 'Access Blocked', solve any puzzle")
            print("   • Log in again if needed")
            print("   • Wait for the page to load completely")
            print("\n✅ WHEN READY:")
            print("   Press ENTER to continue processing")
            print("="*70)
            input("\n⏯ Press ENTER to resume...")
            print(f"\n🤖 Resuming automation... {len(df) - index} containers remaining\n")
        
        while not process_container(container_id):
            pass
        
        containers_processed += 1
        time.sleep(random.uniform(0.2, 0.5))

except Exception as e:
    logging.critical(f"An unexpected error occurred: {e}")
finally:
    driver.quit()
    print("\n🔒 Browser closed")

##################################################
# SMART PARSING - Build final DataFrame from all rows
##################################################
print("\n🔄 Processing data with smart parsing...")
output_df = pd.DataFrame(all_matching_rows)

VESSEL_PATTERNS = [
    (re.compile(r'^Load on\s+(.+)$', re.IGNORECASE), 'Load on'),
    (re.compile(r'^Vessel departure\s*\((.+)\)$', re.IGNORECASE), 'Vessel departure'),
    (re.compile(r'^Vessel arrival\s*\((.+)\)$', re.IGNORECASE), 'Vessel arrival'),
]

def extract_vessel_from_status(status_text):
    """Extract vessel name and clean status from status text"""
    if not status_text:
        return status_text, ''
    
    for pattern, clean_status in VESSEL_PATTERNS:
        match = pattern.match(status_text.strip())
        if match:
            vessel_name = match.group(1).strip()
            return clean_status, vessel_name
    
    return status_text, ''

if len(output_df) > 0 and 'Row_Parts' in output_df.columns:
    clean_data = []
    
    for idx, row in output_df.iterrows():
        container = row['Container_Number']
        parts = row['Row_Parts'] if 'Row_Parts' in row.index else []
        
        if not isinstance(parts, list):
            if pd.isna(parts) or parts is None:
                parts = []
            else:
                try:
                    parts = list(parts)
                except:
                    parts = []
        
        status = ''
        location = ''
        terminal = ''
        datetime_str = ''
        
        for part in parts:
            if is_datetime(part):
                datetime_str = part
            elif is_status(part):
                status = part
            elif not location:
                location = part
            elif not terminal:
                terminal = part
                
        clean_status, vessel_name = extract_vessel_from_status(status)
        
        date_only = ''
        time_only = ''
        if datetime_str:
            match = DATE_PATTERN.search(datetime_str)
            if match:
                dt_str = match.group()
                parts_dt = dt_str.rsplit(' ', 1)
                if len(parts_dt) == 2:
                    date_only = parts_dt[0]
                    time_only = parts_dt[1]
        
        full_location = location
        if terminal and terminal != location:
            full_location = f"{location} - {terminal}" if location else terminal
        
        clean_data.append({
            'Container_Number': container,
            'Type_of_Tracking': 'Current Tracking',
            'Status': clean_status,
            'Location': full_location,
            'Date': date_only,
            'Time': time_only,
            'Vessel_Name': vessel_name,
            'Transport': ''
        })
    
    output_df = pd.DataFrame(clean_data)

if len(output_df) > 0:
    output_df['Concat_1'] = output_df['Container_Number'] + output_df['Status'] + output_df['Type_of_Tracking']
    output_df['Concat_2'] = output_df['Container_Number'] + output_df['Status']
    output_df['Concat_3'] = output_df['Container_Number'] + output_df['Type_of_Tracking']
    
    columns_order = [
        'Container_Number',
        'Concat_1',
        'Concat_2',
        'Concat_3',
        'Type_of_Tracking',
        'Status',
        'Location',
        'Date',
        'Time',
        'Vessel_Name',
        'Transport'
    ]
    
    existing_columns = [col for col in columns_order if col in output_df.columns]
    output_df = output_df[existing_columns]
    
    output_df['Duplicates'] = ''
    
    try:
        output_df['Date_Temp'] = pd.to_datetime(output_df['Date'], format='%d %b %Y', errors='coerce')
        grouped = output_df.groupby('Concat_2')
        for name, group in grouped:
            if len(group) > 1:
                valid_dates = group[group['Date_Temp'].notna()]
                if len(valid_dates) > 0:
                    latest_idx = valid_dates['Date_Temp'].idxmax()
                    output_df.loc[latest_idx, 'Duplicates'] = 'Latest'
        output_df.drop(columns=['Date_Temp'], inplace=True, errors='ignore')
    except Exception as e:
        logging.warning(f"Could not process duplicates: {e}")

output_directory = os.path.dirname(excel_path)
print(f"\n📁 Output directory: {output_directory}")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

if len(output_df) > 0:
    # ── Save Excel (unchanged) ───────────────────────────────────────────
    output_filename = f"maersk_tracking_{timestamp}.xlsx"
    output_path = os.path.join(output_directory, output_filename)
    output_df.to_excel(output_path, index=False)

    # ── Save JSON ────────────────────────────────────────────────────────  ← NEW
    records = output_df.to_dict(orient="records")

    json_payload = {
        "carrier":      "MAEU",
        "scraped_at":   timestamp,
        "total_events": len(records),
        "records":      records
    }

    json_filename = f"maersk_tracking_{timestamp}.json"
    json_file = os.path.join(output_directory, json_filename)

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, indent=2, default=str)  # default=str handles any leftover Timestamps
    # ────────────────────────────────────────────────────────────────────

    print("\n" + "="*70)
    print("✅ SCRAPING COMPLETE!")
    print("="*70)
    print(f"\n📊 SUMMARY:")
    print(f"   • Total containers processed: {len(df)}")
    print(f"   • Browser restarts triggered: {containers_processed // 100}")
    print(f"   • Total rows extracted: {len(output_df)}")
    if 'Container_Number' in output_df.columns:
        print(f"   • Unique containers: {output_df['Container_Number'].nunique()}")
    print(f"\n📁 OUTPUT FILES:")
    print(f"   Excel → {output_path}")
    print(f"   JSON  → {json_file}")
    print("="*70)
    
    logging.info(f"Extracted data saved to {output_path}")
    logging.info(f"JSON data saved to {json_file}")
else:
    print("\n⚠ No data was extracted. Check the logs for errors.")
    print(f"Expected output location would have been: {os.path.join(output_directory, f'maersk_tracking_{timestamp}.xlsx')}")
