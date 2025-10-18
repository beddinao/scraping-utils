from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.firefox.options import Options
from urllib.parse import urlparse
import threading
import requests
import re

phone_pattern = re.compile(r"(?:\+212|0)(6\d{8})")
link_pattern = r'https?://\S+|www\.\S+'
email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
url_pattern = "https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)"

file_lock = threading.Lock()
firefox_options = Options()
firefox_options.add_argument("--headless")

main_target = "some useful target"
main_target_start_page = 136
main_target_end_page = 504
main_target_current_page = main_target_start_page

def hunt_page(url, links_file):
    print(f"===== getting {url}")
    driver = webdriver.Firefox(options=firefox_options)
    driver.set_page_load_timeout(30)
    try:
        driver.get(url)
    except Exception as e:
        print(f"=====> exceptions getting {url}, ignoring..")
        driver.close()
        driver.quit()
        return
    elements = driver.find_elements(By.CSS_SELECTOR, ".wpbdp-field-value > .value")
    if len(elements) != 0:
        for elem in elements:
            text = elem.get_attribute("textContent")
            if text.startswith(("http://", "https://")):
                print(f"     -> [{text}]")
                with file_lock:
                    links_file.write(f"{text}\n")
    driver.close()
    driver.quit()

try:
    with open(str(main_target_start_page) + "-" + str(main_target_end_page), 'w') as links_file:
        driver = webdriver.Firefox(options=firefox_options)
        driver.set_page_load_timeout(30)
        threads_list = []
        while True:
            current_url = main_target + "page/" + str(main_target_current_page)
            print(f"--- looking up page {current_url}")
            try:
                driver.get(current_url)
                status_code = requests.get(driver.current_url).status_code
                if status_code != 200:
                    raise Exception("skip")
            except Exception as e:
                print(f"==> exception getting {current_url}, ignorring")
                continue

            elements = driver.find_elements(By.CSS_SELECTOR, ".wpbdp-listing-excerpt > .listing-title > h3 > a")
            elements = list(map(lambda elem: elem.get_attribute("href").strip(), elements))

            for href in elements:
                thread = threading.Thread(target=hunt_page, args=(href, links_file,))
                threads_list.append(thread)
                thread.start()

            for thread in threads_list:
                thread.join()
            threads_list.clear()

            main_target_current_page = main_target_current_page + 1
            if main_target_current_page == main_target_end_page:
                break

        driver.close()
        driver.quit()

except Exception as e:
    print(f"just caught exception ({e})")
    for thread in threads_list:
        thread.join()

links_file.close()
