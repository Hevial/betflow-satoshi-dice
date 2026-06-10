import pandas as pd
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_webdriver():
    """Set up a headless Chrome WebDriver with optimized options for scraping."""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # Standard user-agent to avoid basic bot blocking
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
    
    # Use Service with ChromeDriverManager for automatic driver management
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def scrape_address_wallet(driver, address):
    """
    Scrape the wallet ID associated with a given address from walletexplorer.com.
    Returns:
        - wallet_id (str): The name/ID of the wallet if found, "Address Not Found" if the address does not exist, "Unknown" if the page structure is unexpected, or None if an error occurs during scraping.
    """

    url = f"https://www.walletexplorer.com/address/{address}"
    try:
        driver.get(url)
        # Wait for the DOM to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        try:
            wallet_elem = driver.find_element(By.CLASS_NAME, "wallet_renamer_item")
            # We look for the anchor tag inside the wallet div which contains the name/ID
            link = wallet_elem.find_element(By.TAG_NAME, "a")
            wallet_id = link.find_element(By.CLASS_NAME, "wallet_name").text.strip()
            if wallet_id:
                return wallet_id
        except Exception:
            pass
            
        # Fallback to checking the page content if "wallet" class fails
        if "No such address" in driver.page_source:
            return "Address Not Found"
            
        return "Unknown"
    except Exception as e:
        print(f"Error during scraping for {address}: {e}")
        return None

def build_wallet_mapping(addresses, mapping_file='../data/wallet_mapping.csv', force_refresh=False):
    """
    Scrapes a list of addresses.
    Uses a CSV file for caching, prevents duplicates, and provides a force_refresh option.
    Parameters:
        - addresses (list): List of addresses to scrape.
        - mapping_file (str): Path to the CSV file used for caching the results.
        - force_refresh (bool): If True, forces re-scraping of all addresses by renaming the existing cache file as a backup.
    Returns:
        - scraped_dict (dict): A dictionary mapping addresses to their corresponding wallet IDs.
    """
    os.makedirs(os.path.dirname(mapping_file), exist_ok=True)
    
    # If a forced refresh is requested, rename the old cache as a backup
    if force_refresh and os.path.exists(mapping_file):
        # os.replace is safer on Windows as it overwrites the destination if it exists
        os.replace(mapping_file, mapping_file + ".bak")
        
    scraped_dict = {}
    
    # Safe cache loading
    if os.path.exists(mapping_file):
        try:
            cache_df = pd.read_csv(mapping_file)
            # Remove duplicate rows keeping the last one in case of interrupted appends
            cache_df = cache_df.drop_duplicates(subset=['address'], keep='last')
            scraped_dict = dict(zip(cache_df['address'], cache_df['wallet']))
        except pd.errors.EmptyDataError:
            # File exists but is empty
            pd.DataFrame(columns=['address', 'wallet']).to_csv(mapping_file, index=False)
    else:
        # Create the file and header row
        pd.DataFrame(columns=['address', 'wallet']).to_csv(mapping_file, index=False)
        
    # Identify only the addresses that haven't been processed yet
    to_scrape = [addr for addr in addresses if addr not in scraped_dict]
    
    if not to_scrape:
        print("All addresses are already cached. Use force_refresh=True to download them again.")
        return scraped_dict
        
    print(f"Starting scraping for {len(to_scrape)} new addresses...")
    
    driver = get_webdriver()
    try:
        for i, addr in enumerate(to_scrape):
            print(f"Scraping [{i+1}/{len(to_scrape)}]: {addr}")
            wallet_id = scrape_address_wallet(driver, addr)
            
            if wallet_id is not None:
                scraped_dict[addr] = wallet_id
                # Atomic append for each row (extremely safe against crashes)
                pd.DataFrame([{'address': addr, 'wallet': wallet_id}]).to_csv(mapping_file, mode='a', header=False, index=False)
            
    finally:
        driver.quit()
        
    return scraped_dict
