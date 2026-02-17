import os
import time
import requests
import threading
from collections import Counter
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from deep_translator import GoogleTranslator

# ================= CONFIGURATION =================
# We will fill these in later for the BrowserStack part.
BROWSERSTACK_USERNAME = 'YOUR_USERNAME_HERE'
BROWSERSTACK_ACCESS_KEY = 'YOUR_ACCESS_KEY_HERE'


URL = "https://elpais.com/opinion/"

# ================= CORE FUNCTIONS =================

def get_driver(env="local", thread_name="Main"):
    """
    Creates the browser instance.
    If env='local', it opens Chrome on your computer.
    If env='remote', it connects to BrowserStack.
    """
    if env == "local":
        options = ChromeOptions()
        # options.add_argument('--headless') # Uncomment this if you don't want to see the browser pop up
        driver = webdriver.Chrome(options=options)
        return driver
    
    elif env == "remote":
        print(f"[{thread_name}] Connecting to BrowserStack...")
        bstack_options = {
            "os" : "Windows",
            "osVersion" : "10",
            "projectName" : "El Pais Scraper",
            "buildName" : "Build 1",
            "sessionName" : f"Test - {thread_name}",
            "userName": BROWSERSTACK_USERNAME,
            "accessKey": BROWSERSTACK_ACCESS_KEY
        }
        
        options = ChromeOptions()
        options.set_capability('bstack:options', bstack_options)
        
        driver = webdriver.Remote(
            command_executor="https://hub-cloud.browserstack.com/wd/hub",
            options=options
        )
        return driver

def translate_text(text):
    """Translates Spanish text to English."""
    try:
        return GoogleTranslator(source='es', target='en').translate(text)
    except Exception as e:
        print(f"Translation Error: {e}")
        return text

def analyze_headers(headers_list):
    """Counts words in the translated headers."""
    print("\n" + "="*40)
    print("       ANALYZING TRANSLATED HEADERS")
    print("="*40)
    
    all_words = []
    for header in headers_list:
        # 1. Clean the text (remove punctuation like . , !)
        clean_header = "".join([c if c.isalnum() or c.isspace() else "" for c in header])
        # 2. Split into a list of words and make them lowercase
        words = clean_header.lower().split()
        all_words.extend(words)
    
    # 3. Count frequencies
    word_counts = Counter(all_words)
    
    # 4. Filter for words that appear more than 2 times
    repeated_words = {word: count for word, count in word_counts.items() if count > 2}
    
    if repeated_words:
        for word, count in repeated_words.items():
            print(f"Word: '{word}' | Occurrences: {count}")
    else:
        print("No words repeated more than twice.")
    print("="*40 + "\n")

def run_scraper(env="local", thread_name="Main"):
    """
    The main logic: Navigate -> Scrape -> Translate -> Save.
    """
    driver = None
    try:
        driver = get_driver(env, thread_name)
        print(f"[{thread_name}] Navigating to {URL}...")
        driver.get(URL)
        
        # --- HANDLE COOKIES ---
        # European sites often have popups. We try to click "Agree" if it appears.
        try:
            wait = WebDriverWait(driver, 5)
            # We look for the 'Didomi' agree button (standard for El Pais)
            accept_btn = wait.until(EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button")))
            accept_btn.click()
            print(f"[{thread_name}] Cookies accepted.")
        except:
            print(f"[{thread_name}] Cookie banner not found or skipped.")

        # --- GET ARTICLES ---
        # We look for <article> tags on the page.
        articles = driver.find_elements(By.TAG_NAME, "article")[:5]
        translated_titles = []
        
        # Create a folder for images if we are running locally
        if env == "local" and not os.path.exists("images"):
            os.makedirs("images")

        print(f"[{thread_name}] Found {len(articles)} articles. Processing...\n")

        for i, article in enumerate(articles, 1):
            # 1. Get Title (Spanish)
            try:
                title_elm = article.find_element(By.TAG_NAME, "h2")
                title_es = title_elm.text
            except:
                title_es = "No Title"
            
            # 2. Get Content (Spanish snippet)
            try:
                content_elm = article.find_element(By.TAG_NAME, "p")
                content_es = content_elm.text
            except:
                content_es = "No Content Preview"
            
            # 3. Get Image URL
            img_url = None
            try:
                img_elm = article.find_element(By.TAG_NAME, "img")
                img_url = img_elm.get_attribute("src")
            except:
                pass

            # 4. Translate Title (English)
            title_en = translate_text(title_es)
            translated_titles.append(title_en)

            # Print Progress
            print(f"--- Article {i} ---")
            print(f"Title (ES): {title_es}")
            print(f"Title (EN): {title_en}")
            
            # 5. Download Image (Local Only)
            if env == "local" and img_url:
                try:
                    img_data = requests.get(img_url).content
                    with open(f"images/article_{i}_{thread_name}.jpg", "wb") as handler:
                        handler.write(img_data)
                    print(f"Image saved.")
                except:
                    print(f"Failed to save image.")

        # --- ANALYZE HEADERS ---
        # Only analyze if it's the main thread
        if thread_name == "Main" or thread_name == "Thread-1":
            analyze_headers(translated_titles)

    except Exception as e:
        print(f"[{thread_name}] Critical Error: {e}")
    finally:
        # Always close the browser, even if there was an error
        if driver:
            driver.quit()
            print(f"[{thread_name}] Finished.")

# ================= MAIN MENU =================

if __name__ == "__main__":
    print("--- EL PAIS SCRAPER ---")
    print("1. Local Run (Test on your PC)")
    print("2. BrowserStack Run (Parallel Test)")
    
    choice = input("Enter 1 or 2: ")
    
    if choice == "1":
        run_scraper(env="local")
        
    elif choice == "2":
        if "YOUR_USERNAME" in BROWSERSTACK_USERNAME:
            print("ERROR: Please update your BrowserStack credentials in the file 'main.py' first.")
        else:
            threads = []
            print("\nStarting 5 Parallel Threads...")
            for i in range(5):
                t = threading.Thread(target=run_scraper, args=("remote", f"Thread-{i+1}"))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            print("\nAll parallel tests completed.")