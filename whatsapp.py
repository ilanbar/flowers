from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
import sys
import os

def scrape_whatsapp_members():
    # Initialize driver for MS Edge (Connect to existing instance)
    options = webdriver.EdgeOptions()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    # NOTE: To use this, you must start Edge from the command line with:
    # "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="C:\selenium\EdgeProfile"
    # Or just --remote-debugging-port=9222 if you want to try identifying the main process (might be tricky with open windows)
    
    print("Attempting to connect to existing MS Edge instance on port 9222...")
    try:
        driver = webdriver.Edge(options=options)
    except Exception as e:
        print("\n" + "="*60)
        print("ERROR: Could not connect to MS Edge.")
        print("To use the current window, you MUST start Edge with this command:")
        print("1. Close ALL open Edge windows.")
        print("2. Open 'Run' (Win+R) or PowerShell and paste:")
        print(r'   "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222')
        print("="*60 + "\n")
        # traceback.print_exc()
        return

    try:
        print("Connected to Edge! checking for WhatsApp tab...")
        # Check if WhatsApp is already open in one of the tabs
        windows = driver.window_handles
        found_whatsapp = False
        
        for window in windows:
            driver.switch_to.window(window)
            if "WhatsApp" in driver.title or "web.whatsapp.com" in driver.current_url:
                print("Found existing WhatsApp tab!")
                found_whatsapp = True
                break
        
        if not found_whatsapp:
            print("WhatsApp not found in open tabs. Opening in current tab...")
            driver.get('https://web.whatsapp.com')

        print("Checking login status...")
        wait = WebDriverWait(driver, 600)  # 10 minutes wait for login
        
        wait = WebDriverWait(driver, 600)  # 10 minutes wait for login
        
        # Wait for the search box to appear (indicating login success)
        search_box_xpath = '//div[@contenteditable="true"][@data-tab="3"]'
        search_box = wait.until(EC.presence_of_element_located((By.XPATH, search_box_xpath)))
        print("Login detected!")
        time.sleep(3)
        
        target_group = "הפרחים של עדי"
        
        # Search for the group
        print(f"Searching for group: {target_group}")
        search_box.click()
        search_box.clear()
        search_box.send_keys(target_group)
        time.sleep(2)
        search_box.send_keys(Keys.ENTER)
        
        print(f"Opened group chat: {target_group}")
        time.sleep(3)
        
        # Click on the group header to open Group Info
        header_xpath = '//header' 
        header = wait.until(EC.element_to_be_clickable((By.XPATH, header_xpath)))
        header.click()
        
        print("Opened Group Info. Waiting for member list to load...")
        time.sleep(3)
        
        # Find the member list container
        # Determining the scrollable element in the side panel is tricky as classes change.
        
        # Strategy: Find the 'Group info' header, then find the distinct side panel container.
        print("Locating Group Info panel...")
        try:
            # Try English 'Group info' or Hebrew 'פרטי קבוצה'
            side_panel_xpath = "//div[.//div[text()='Group info'] or .//div[text()='פרטי קבוצה']]"
            # This selects the outer wrapper of the side panel usually
            side_panel = driver.find_element(By.XPATH, side_panel_xpath)
            print("Found side panel container.")
        except:
            print("Could not locate side panel by text. Using fallback (right-most main container).")
            # Fallback: The side panel is usually the last child of the main content wrapper
            side_panel = driver.find_element(By.TAG_NAME, "body") # Worst case fallback
        
        collected_contacts = set()
        print("Scraping members from side panel...")
        
        # Try to find "View all" matches
        print("Checking for 'View all' participants button...")
        try:
            # Look for button that says "View all" or "הכל"
            view_all_btns = driver.find_elements(By.XPATH, "//div[contains(text(), 'View all') or contains(text(), 'הכל')]")
            for btn in view_all_btns:
                # Click it if it's visible
                if btn.is_displayed():
                    print("Clicking 'View all' button...")
                    btn.click()
                    time.sleep(2)
                    # Relocate side panel to the new modal which is likely a div[role='dialog'] or similar
                    # Actually, the modal usually becomes the top-level focused element.
                    # We will search for listitems globally as the modal covers the rest.
                    break
        except:
            pass
        
        collected_data = {} # Map name -> phone (if available) or raw string

        last_len = 0
        unchanged_iterations = 0
        
        print("Scraping rows using role='listitem'...")
        
        # We need to find the scrollable container again because if we opened a modal, it's different.
        # Simplest approach: Find the scrollable div that contains the listitems.
        
        scrollable_div = None
        
        for i in range(40):
            # Find all list items currently visible
            # role="listitem" is standard for WhatsApp Web contact lists
            rows = driver.find_elements(By.CSS_SELECTOR, "div[role='listitem']")
            
            # If no rows found with listitem, try fallback to broad class search if needed, but listitem is usually reliable.
            if not rows:
                 # Fallback: look for divs with specific structure (child span with dir auto)
                 rows = driver.find_elements(By.XPATH, "//div[.//span[@dir='auto']]")

            # Identify the scrollable container dynamically if we haven't yet
            if not scrollable_div and rows:
                # The scrollable div is usually a parent of these rows.
                # We can try to get the parent of the first row and check if it scrolls.
                first_row = rows[0]
                scrollable_div = driver.execute_script("""
                    var el = arguments[0];
                    while (el && el !== document.body) {
                        var style = window.getComputedStyle(el);
                        if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
                            return el;
                        }
                        el = el.parentElement;
                    }
                    return null;
                """, first_row)
                if scrollable_div:
                    print("Located scrollable container dynamically from list items.")

            for row in rows:
                try:
                    full_text = row.text.strip()
                    if not full_text: continue
                    
                    lines = full_text.split('\n')
                    primary = lines[0]
                    
                    # FILTERS
                    if primary in ["Add member", "Invite to group via link", "You", "Group info", "פרטי קבוצה", "Report group", "Exit group", "Medias, links and docs"]: continue
                    if "participant" in primary.lower() or "משתתפים" in primary: continue
                    
                    # Filter timestamps 
                    import re
                    if re.match(r'^\d{1,2}:\d{2}$', primary): continue
                    if primary in ["Yesterday", "Today", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]: continue
                    
                    if "Admin" in primary or "מנהל" in primary: continue

                    secondary = lines[1] if len(lines) > 1 else ""
                    
                    collected_data[primary] = secondary
                except:
                    pass
            
            print(f"Collected {len(collected_data)} members (last was {last_len})...")
            
            if len(collected_data) == last_len and len(collected_data) > 0:
                unchanged_iterations += 1
            else:
                unchanged_iterations = 0
            last_len = len(collected_data)
            
            if unchanged_iterations > 5:
                break

            # Scroll
            if scrollable_div:
                driver.execute_script("arguments[0].scrollTop += 500;", scrollable_div)
            else:
                webdriver.ActionChains(driver).send_keys(Keys.PAGE_DOWN).perform()
            time.sleep(0.5)

        # Save to Excel
        final_list = []
        for name, extra in collected_data.items():
            final_list.append({"Contact Name/Number": name, "Status/Info": extra})
            
        df = pd.DataFrame(final_list)
        output_file = "whatsapp_group_members_v2.xlsx"
        df.to_excel(output_file, index=False)
        print(f"Successfully saved {len(final_list)} contacts to {output_file}")

        print(f"Successfully saved {len(final_list)} contacts to {output_file}")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("Closing in 5 seconds...")
        time.sleep(5)
        driver.quit()

if __name__ == "__main__":
    scrape_whatsapp_members()
