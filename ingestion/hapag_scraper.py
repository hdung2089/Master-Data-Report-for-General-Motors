import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import ElementClickInterceptedException
import time
from datetime import datetime
import os
import re
import json                                          # ← NEW

# ==================== CONFIGURATION ====================
CHROMEDRIVER_PATH = r"C:\Users\ngodu\OneDrive - CEVA Logistics\Desktop\chromedriver-win64\chromedriver.exe"
TRACKING_URL = "https://www.hapag-lloyd.com/en/online-business/track/track-by-container-solution.html"
CONTAINER_LIST_FILE = r"C:\Users\ngodu\OneDrive - CEVA Logistics\Desktop\Report\AP-GMNA rep\Base reports\Webscraping\HLCU.xlsx"
# =======================================================

def scrape_with_deduplication(container_list_file):
    """
    Optimized scraper with duplicate detection, overlay handling, and tracking type classification
    """
    print("="*70)
    print("HAPAG-LLOYD SCRAPER - OPTIMIZED WITH TRACKING TYPES ⚡")
    print("="*70)
    print("\n✨ FEATURES:")
    print("   • Fast processing (30-40% faster)")
    print("   • Handles floating popups/chat widgets")
    print("   • Historic/Current/Future tracking classification")
    print("   • Duplicate detection")
    print("   • Enhanced concatenation with Transport mode")
    print("   • Saves to WebScrape folder")
    print("="*70)
    
    input("\n👉 Press ENTER to start...")
    
    # Read containers
    print(f"\n📋 Reading containers from Excel...")
    df_containers = pd.read_excel(container_list_file)
    
    if 'Container_Number' not in df_containers.columns:
        print("❌ Error: Excel must have 'Container_Number' column")
        return None
    
    containers = df_containers['Container_Number'].dropna().tolist()
    print(f"✓ Found {len(containers)} containers to process\n")
    
    # Get output directory
    output_dir = os.path.dirname(container_list_file)
    print(f"📁 Output directory: {output_dir}\n")
    
    # Setup Selenium
    print("🌐 Opening Chrome browser...")
    service = Service(CHROMEDRIVER_PATH)
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    
    # Anti-detection features
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    driver = webdriver.Chrome(service=service, options=options)
    
    # Remove webdriver property
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })
    
    print("✓ Browser opened\n")
    
    try:
        # Navigate to site
        print(f"🔗 Loading: {TRACKING_URL}")
        driver.get(TRACKING_URL)
        time.sleep(1.5)
        
        # Pause for manual verification
        print("\n" + "="*70)
        print("⏸ PAUSED - YOUR TURN!")
        print("="*70)
        print("\n🎯 IN THE BROWSER WINDOW:")
        print("   1. Click 'Verify you are human' checkbox")
        print("   2. Complete any CAPTCHA if it appears")
        print("   3. Wait for the tracking page to load")
        print("   4. (Optional) Close any chat/feedback popups")
        print("\n✅ WHEN YOU SEE THE SEARCH BOX:")
        print("   Come back here and press ENTER")
        print("="*70)
        
        input("\n⏯ Press ENTER after completing Cloudflare check...")
        
        print("\n🤖 Automation starting (TURBO MODE ⚡)...\n")
        
        all_data = []
        successful = 0
        failed = 0
        start_time = time.time()
        
        # Process each container
        for idx, container in enumerate(containers, 1):
            print(f"\n{'─'*70}")
            print(f"📦 Container {idx}/{len(containers)}: {container}")
            
            try:
                # Refresh page if not first container
                if idx > 1:
                    driver.get(TRACKING_URL)
                    time.sleep(1)
                
                # Find search box
                input_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="tracing_by_container_f:hl12"]'))
                )
                
                # Clear and enter container number
                input_field.clear()
                time.sleep(0.1)
                
                for char in container:
                    input_field.send_keys(char)
                    time.sleep(0.04)
                
                print(f"   ✓ Entered container number")
                time.sleep(0.2)
                
                # Click search button with overlay handling
                search_button = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="tracing_by_container_f:hl25"]'))
                )
                
                # Try clicking normally first
                try:
                    search_button.click()
                    print(f"   ✓ Searching...")
                except ElementClickInterceptedException:
                    print(f"   ⚠ Popup blocking button, using fallback method...")
                    
                    # Method 1: Try to close floating button if it exists
                    try:
                        floating_btn = driver.find_element(By.TAG_NAME, "floating-btn")
                        driver.execute_script("arguments[0].style.display = 'none';", floating_btn)
                        print(f"   ✓ Removed floating button")
                        time.sleep(0.3)
                    except:
                        pass
                    
                    # Method 2: Scroll button into view
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_button)
                    time.sleep(0.3)
                    
                    # Method 3: JavaScript click as final fallback
                    try:
                        search_button.click()
                        print(f"   ✓ Searching (retry successful)...")
                    except:
                        driver.execute_script("arguments[0].click();", search_button)
                        print(f"   ✓ Searching (JavaScript click)...")
                
                # Wait for results
                try:
                    table = WebDriverWait(driver, 12).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="tracing_by_container_f:hl66"]'))
                    )
                    time.sleep(0.5)
                except:
                    time.sleep(2)
                    table = driver.find_element(By.XPATH, '//*[@id="tracing_by_container_f:hl66"]')
                
                # Extract tracking table
                rows = table.find_elements(By.TAG_NAME, "tr")
                container_data = []
                
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 5:
                        container_data.append({
                            'Container_Number': container,
                            'Status': cells[0].text.strip(),
                            'Place_of_Activity': cells[1].text.strip(),
                            'Date': cells[2].text.strip(),
                            'Time': cells[3].text.strip(),
                            'Transport': cells[4].text.strip()
                        })
                
                if container_data:
                    all_data.extend(container_data)
                    successful += 1
                    print(f"   ✓ Scraped {len(container_data)} events")
                    print(f"   📍 Latest: {container_data[0]['Status']} @ {container_data[0]['Place_of_Activity']}")
                else:
                    print(f"   ⚠ No tracking data available")
                    failed += 1
                
                # Progress update
                if idx % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = idx / elapsed
                    remaining = (len(containers) - idx) / rate
                    print(f"\n   📊 Progress: {idx}/{len(containers)} ({idx/len(containers)*100:.1f}%)")
                    print(f"   ⚡ Est. time remaining: {int(remaining/60)} min {int(remaining%60)} sec")
                    print(f"   ⚡ Current speed: {60/rate:.1f} containers/min")
                
                time.sleep(0.8)
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                failed += 1
        
        # Export and process results
        if all_data:
            df = pd.DataFrame(all_data)
            
            print("\n🔄 Processing data and adding tracking type classification...")
            
            # Convert Date and Time to datetime for proper sorting and classification
            df['Date_DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], 
                                                   format='%Y-%m-%d %H:%M', 
                                                   errors='coerce')
            
            # Add Type_of_Tracking column
            df['Type_of_Tracking'] = ''
            today = pd.Timestamp.now()
            
            print(f"   ℹ Today's date for comparison: {today.strftime('%Y-%m-%d %H:%M')}")
            
            # Group by container and classify tracking type
            grouped = df.groupby('Container_Number')
            
            for container_id, group in grouped:
                # Separate valid and invalid dates
                valid_dates = group[group['Date_DateTime'].notna()].copy()
                invalid_dates = group[group['Date_DateTime'].isna()].copy()
                
                # Debug: Show what we're processing
                if len(invalid_dates) > 0:
                    print(f"   ⚠ Container {container_id}: Found {len(invalid_dates)} rows with unparseable dates")
                    print(f"      Statuses: {invalid_dates['Status'].tolist()}")
                    print(f"      Original dates: {invalid_dates['Date'].tolist()}")
                
                if len(valid_dates) > 0:
                    # Separate past and future events (valid dates only)
                    past_events = valid_dates[valid_dates['Date_DateTime'] <= today]
                    future_events = valid_dates[valid_dates['Date_DateTime'] > today]
                    
                    print(f"   📊 Container {container_id}: {len(past_events)} past, {len(future_events)} future (valid dates)")
                    
                    # Mark ALL future events as "Future Tracking"
                    if len(future_events) > 0:
                        df.loc[future_events.index, 'Type_of_Tracking'] = 'Future Tracking'
                        print(f"      ✓ Marked {len(future_events)} events as Future Tracking")
                    
                    # For past events, find the most recent one
                    if len(past_events) > 0:
                        # Sort past events by date (most recent first)
                        past_events_sorted = past_events.sort_values('Date_DateTime', ascending=False)
                        
                        # The first one (most recent past) is "Current Tracking"
                        current_idx = past_events_sorted.index[0]
                        df.loc[current_idx, 'Type_of_Tracking'] = 'Current Tracking'
                        print(f"      ✓ Marked 1 event as Current Tracking: {df.loc[current_idx, 'Status']}")
                        
                        # All other past events are "Historic Tracking"
                        if len(past_events_sorted) > 1:
                            historic_indices = past_events_sorted.index[1:]
                            df.loc[historic_indices, 'Type_of_Tracking'] = 'Historic Tracking'
                            print(f"      ✓ Marked {len(historic_indices)} events as Historic Tracking")
                    else:
                        # If no past events but there are future events
                        print(f"      ℹ No past events - all {len(future_events)} future events remain as Future Tracking")
                
                # Handle rows with unparseable dates
                if len(invalid_dates) > 0:
                    df.loc[invalid_dates.index, 'Type_of_Tracking'] = 'Future Tracking'
                    print(f"      ⚠ Marked {len(invalid_dates)} unparseable dates as Future Tracking (assumed scheduled)")
                
                # If somehow no dates at all (valid or invalid), mark first as Current
                if len(valid_dates) == 0 and len(invalid_dates) == 0:
                    df.loc[group.index[0], 'Type_of_Tracking'] = 'Current Tracking'
            
            # Create Concat columns with Transport included for specific statuses
            df['Concat_1'] = df.apply(lambda row: 
                row['Container_Number'] + row['Status'] + 
                (row['Transport'] if 'Arrival in' in row['Status'] or 'Departure from' in row['Status'] else '') + 
                row['Type_of_Tracking'], 
                axis=1
            )
            df['Concat_2'] = df.apply(lambda row: 
                row['Container_Number'] + row['Status'] + 
                (row['Transport'] if 'Arrival in' in row['Status'] or 'Departure from' in row['Status'] else ''), 
                axis=1
            )
            df['Concat_3'] = df['Container_Number'] + df['Type_of_Tracking']
            
            # Add Duplicates column with proper error handling
            df['Duplicates'] = ''
            grouped = df.groupby('Concat_2')
            
            for name, group in grouped:
                if len(group) > 1:
                    valid_dates = group[group['Date_DateTime'].notna()]
                    if len(valid_dates) > 0:
                        latest_idx = valid_dates['Date_DateTime'].idxmax()
                        df.loc[latest_idx, 'Duplicates'] = 'Latest'
                    else:
                        df.loc[group.index[0], 'Duplicates'] = 'Latest'
            
            # Drop the temporary datetime column
            df.drop(columns=['Date_DateTime'], inplace=True)
            
            # Reorder columns
            columns_order = [
                'Container_Number',
                'Concat_1',
                'Concat_2',
                'Concat_3',
                'Type_of_Tracking',
                'Status', 
                'Place_of_Activity',
                'Date',
                'Time',
                'Transport',
                'Duplicates'
            ]
            df = df[columns_order]
            
            # Timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # ── Save Excel (unchanged) ───────────────────────────────────────
            output_filename = f"hapag_lloyd_tracking_{timestamp}.xlsx"
            output_file = os.path.join(output_dir, output_filename)
            df.to_excel(output_file, index=False)

            # ── Save JSON ────────────────────────────────────────────────────  ← NEW
            records = df.to_dict(orient="records")

            json_payload = {
                "carrier":       "HLCU",
                "scraped_at":    timestamp,
                "total_events":  len(records),
                "records":       records
            }

            json_filename = f"hapag_lloyd_tracking_{timestamp}.json"
            json_file = os.path.join(output_dir, json_filename)

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(json_payload, f, indent=2, default=str)  # default=str handles any leftover Timestamps
            # ────────────────────────────────────────────────────────────────

            elapsed_total = time.time() - start_time
            
            # Count tracking types
            tracking_counts = df['Type_of_Tracking'].value_counts()
            duplicate_count = (df['Duplicates'] == 'Latest').sum()
            
            print("\n" + "="*70)
            print("✅ SCRAPING COMPLETE!")
            print("="*70)
            print(f"\n📊 SUMMARY:")
            print(f"   • Total containers: {len(containers)}")
            print(f"   • Successful: {successful} ✅")
            print(f"   • Failed: {failed} ❌")
            print(f"   • Success rate: {successful/len(containers)*100:.1f}%")
            print(f"   • Total events: {len(df)}")
            print(f"\n📋 TRACKING TYPES:")
            for tracking_type, count in tracking_counts.items():
                print(f"   • {tracking_type}: {count}")
            print(f"\n🔄 DUPLICATES:")
            print(f"   • Duplicate sets found: {duplicate_count}")
            print(f"\n⏱ PERFORMANCE:")
            print(f"   • Time taken: {int(elapsed_total/60)} min {int(elapsed_total%60)} sec")
            print(f"   • Average speed: {len(containers)/(elapsed_total/60):.1f} containers/min")
            print(f"\n📁 OUTPUT FILES:")
            print(f"   Excel → {output_file}")
            print(f"   JSON  → {json_file}")
            print("="*70)
            
            # Show sample of each tracking type
            print("\n📋 SAMPLE BY TRACKING TYPE:")
            for tracking_type in df['Type_of_Tracking'].unique():
                sample = df[df['Type_of_Tracking'] == tracking_type].head(3)
                print(f"\n{tracking_type}:")
                print(sample[['Container_Number', 'Status', 'Date', 'Time', 'Type_of_Tracking']].to_string(index=False))
            
            # Show sample of duplicates
            duplicates_df = df[df['Duplicates'] == 'Latest']
            if len(duplicates_df) > 0:
                print("\n📋 SAMPLE DUPLICATES (Latest marked):")
                print(duplicates_df[['Container_Number', 'Status', 'Type_of_Tracking', 'Date', 'Time', 'Duplicates']].head(10).to_string(index=False))
            
            # Container summary
            print("\n📋 EVENTS PER CONTAINER:")
            summary = df.groupby('Container_Number').agg({
                'Status': 'count',
                'Date': ['first', 'last'],
                'Type_of_Tracking': lambda x: ', '.join(x.unique())
            })
            summary.columns = ['Events', 'First_Date', 'Last_Date', 'Tracking_Types']
            summary = summary.head(20)
            print(summary.to_string())
            
            if len(df['Container_Number'].unique()) > 20:
                print(f"\n   ... and {len(df['Container_Number'].unique()) - 20} more containers")
            
            return df
        else:
            print("\n❌ No data was scraped")
            return None
    
    except KeyboardInterrupt:
        print("\n\n⚠ Stopped by user (Ctrl+C)")
        return None
    except Exception as e:
        print(f"\n❌ Critical error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        print("\n🔒 Closing browser...")
        try:
            driver.quit()
            print("✓ Browser closed")
        except:
            pass


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚢 HAPAG-LLOYD CONTAINER TRACKING SCRAPER")
    print("⚡ OPTIMIZED + TRACKING TYPES ⚡")
    print("="*70)
    print("\n💡 FEATURES:")
    print("   ✓ Handles chat widgets & feedback popups")
    print("   ✓ Fast processing (30-40% faster)")
    print("   ✓ Historic/Current/Future tracking classification")
    print("   ✓ Duplicate detection")
    print("   ✓ Smart Concat with Transport mode for Arrival/Departure")
    print("   ✓ Concat columns positioned after Container_Number")
    print("   ✓ Exports JSON file alongside Excel")
    print("="*70)
    
    result = scrape_with_deduplication(CONTAINER_LIST_FILE)
    
    if result is not None:
        print("\n✅ SUCCESS! Your data is ready for Power BI")
        print("\n💡 POWER BI TIPS:")
        print("   • Use 'Type_of_Tracking' to filter Historic/Current/Future")
        print("   • Use 'Duplicates' column to filter latest events")
        print("   • Concat_1 includes Transport for Arrival/Departure statuses")
        print("   • Use Concat_2 for Container + Status + Transport grouping")
        print("   • Use Concat_3 for Container + Tracking Type analysis")
        print("   • Build container journey timelines by tracking type")
    else:
        print("\n⚠ Scraping was incomplete")
