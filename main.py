import os
import time
import threading
import requests
from collections import Counter
from deep_translator import GoogleTranslator

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
# BrowserStack Credentials
BS_USER = 'YOUR_USERNAME_HERE'
BS_KEY = 'YOUR_ACCESS_KEY_HERE'


TARGET_URL = "https://elpais.com/opinion/"
IMAGE_DIR = "./images"

def get_driver(env="local", thread_name="Main"):
    """Initialize WebDriver. Supports local Chrome or remote BrowserStack."""
    
    if env == "local":
        options = ChromeOptions()
        # options.add_argument('--headless') # Debugging mode
        return webdriver.Chrome(options=options)
    
    elif env == "remote":
        print(f"[{thread_name}] Connecting to BrowserStack Grid...")
        
        bstack_options = {
            "os": "Windows",
            "osVersion": "10",
            "projectName": "El Pais Scraper",
            "buildName": "Production Build 1.0",
            "sessionName": f"Session - {thread_name}",
            "userName": BS_USER,
            "accessKey": BS_KEY
        }
        
        options = ChromeOptions()
        options.set_capability('bstack:options', bstack_options)
        
        return webdriver.Remote(
            command_executor="https://hub-cloud.browserstack.com/wd/hub",
            options=options
        )

def translate_title(text):
    """Wrapper for Google Translate API"""
    try:
        return GoogleTranslator(source='es', target='en').translate(text)
    except Exception as e:
        print(f"Warning: Translation failed for '{text[:10]}...' - {e}")
        return text

def save_image(url, filename):
    try:
        if not os.path.exists(IMAGE_DIR):
            os.makedirs(IMAGE_DIR)
            
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            file_path = os.path.join(IMAGE_DIR, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)
            return True
    except Exception:
        return False
    return False

def analyze_headers(headers):
    """Finds repeated words in headers (>2 occurrences)"""
    print(f"\n{'='*20} ANALYSIS REPORT {'='*20}")
    
    words = []
    for h in headers:
        # Simple tokenization
        clean = "".join([c if c.isalnum() or c.isspace() else "" for c in h])
        words.extend(clean.lower().split())
    
    counts = Counter(words)
    repeats = {w: c for w, c in counts.items() if c > 2}
    
    if repeats:
        for w, c in repeats.items():
            print(f" -> '{w}': {c} times")
    else:
        print("No significant repeated words found.")
    print("="*56 + "\n")

def process_articles(driver, thread_name, env):
    driver.get(TARGET_URL)
    
    # Attempt to close cookie banner
    try:
        wait = WebDriverWait(driver, 5)
        btn = wait.until(EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button")))
        btn.click()
    except:
        pass # Banner might not exist, ignore

    articles = driver.find_elements(By.TAG_NAME, "article")[:5]
    print(f"[{thread_name}] Processing {len(articles)} articles...")
    
    translated_titles = []

    for idx, article in enumerate(articles, 1):
        try:
            # Extract Data
            title_es = article.find_element(By.TAG_NAME, "h2").text
            try:
                content = article.find_element(By.TAG_NAME, "p").text
            except:
                content = "N/A"
            
            # Translation
            title_en = translate_title(title_es)
            translated_titles.append(title_en)
            
            print(f"[{thread_name}] Art. {idx}: {title_en}")

            # Image Handling (Local Only)
            if env == "local":
                try:
                    img_src = article.find_element(By.TAG_NAME, "img").get_attribute("src")
                    if img_src:
                        save_image(img_src, f"article_{idx}.jpg")
                except:
                    pass
                    
        except Exception as e:
            print(f"[{thread_name}] Error parsing article {idx}: {e}")

    return translated_titles

def run_bot(env="local", thread_name="Main"):
    driver = None
    try:
        driver = get_driver(env, thread_name)
        titles = process_articles(driver, thread_name, env)
        
        # Only run analysis on the main thread to keep logs clean
        if thread_name == "Main" or thread_name == "Thread-1":
            analyze_headers(titles)
            
    except Exception as e:
        print(f"[{thread_name}] Critical Failure: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    import sys
    
    print("--- El Pais Automation Tool ---")
    mode = input("Select Mode [1: Local | 2: BrowserStack]: ").strip()
    
    if mode == "1":
        run_bot(env="local")
        
    elif mode == "2":
        if "YOUR_USERNAME" in BS_USER:
            print("Error: BrowserStack credentials not set in config.")
            sys.exit(1)
            
        threads = []
        for i in range(5):
            t = threading.Thread(target=run_bot, args=("remote", f"Thread-{i+1}"))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
        print("\nBatch execution completed.")
    else:
        print("Invalid selection.")