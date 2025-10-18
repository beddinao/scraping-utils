from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.firefox.options import Options
from urllib.parse import urlparse
import mimetypes, os, threading, sys, re, copy, subprocess

phone_pattern = re.compile(r"(?:\+212|0)(6\d{8})")
email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
url_pattern = "https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)"
email_prefixes = ['contact', 'info', 'careers', 'jobs', 'hiring', 'hello', 'team', 'hr', 'talent', 'people', 'join', 'sales', 'office']
common_email_domains = ['gmail.com', 'outlook.com', 'yahoo.com', 'icloud.com']
allowed_mime_types = ['text/html', 'text/plain', 'application/xhtml+xml', 'application/pdf', 'text/xml']
unallowed_wordpress_paths = [ "/wp-admin/", "/wp-includes/", "/wp-content/themes/", "/wp-content/plugins/", "/wp-content/mu-plugins/",
    "/wp-content/languages/", "/wp-content/upgrade/", "/wp-content/cache/", "/wp-content/backups/", "/wp-content/w3tc-config/",
    "/wp-login.php", "/wp-config.php",  "/xmlrpc.php", "/wp-cron.php", "/wp-trackback.php", "/wp-comments-post.php",
    "/wp-mail.php", "/wp-settings.php", "/wp-blog-header.php", "/wp-load.php", "/wp-links-opml.php",
    "/wp-admin/admin-ajax.php", "/wp-admin/admin-post.php", "/wp-admin/edit.php", "/wp-admin/post.php", "/wp-admin/edit-tags.php",
    "/wp-admin/users.php", "/wp-admin/options-general.php", "/wp-admin/themes.php", "/wp-admin/plugins.php", "/wp-json/",
    "/feed/", "/rss/", "/rdf/", "/atom/", "/comments/feed/", "/wp-content/uploads/wp-rocket/", "/wp-content/cache/",
    "/wp-content/et-cache/", "/wp-content/litespeed/", "/wp-content/plugins/akismet/", "/wp-content/plugins/jetpack/",
    "/wp-content/plugins/yoast-seo/", "/wp-content/plugins/elementor/", "/wp-content/plugins/wordfence/",
    "/wp-content/plugins/wp-rocket/", "/wp-content/plugins/w3-total-cache/", "/wp-content/plugins/wp-super-cache/",
    "/wp-content/plugins/jetpack/", "/wp-content/plugins/google-analytics/", "/wp-content/plugins/mailchimp/",
    "/wp-content/plugins/ninja-forms/", "/wp-content/plugins/gravityforms/", "/wp-content/plugins/wpcf7/",
    "/wp-content/themes/*/css/", "/wp-content/themes/*/js/",  "/wp-content/themes/*/images/", "/wp-content/themes/*/fonts/", "/wp-content/themes/*/style.css",
    "/wp-content/themes/*/functions.php", "/wp-content/themes/*/index.php", "/readme.html", "/license.txt", "/wp-config-sample.php", "/wp-content/uploads/*/css/",
    "/wp-content/uploads/*/js/", "/wp-includes/css/", "/wp-includes/js/", "/wp-includes/images/", "/wp-includes/fonts/", "/page/", "/search/",
    "/?s=", "/?p=", "/?page_id=", "/?cat=", "/?tag=", "/?author=", "/?m=", "/2024/", "/2023/", "/2022/",  "/2021/", "/2020/", "/wp-content/blogs.dir/",
    "/files/", "/wp-content/debug.log", "/error_log", ".git/", ".svn/", ".sql", ".zip", ".tar.gz", ".bak","~",
]
unallowed_wordpress_patterns = [ r"wp-content/themes/.+\.(css|js|png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot)$", r"wp-content/plugins/.+\.(css|js|png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot)$",
    r"wp-includes/.+\.(css|js|png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot)$", r"wp-content/uploads/\d{4}/\d{2}/.+\.(css|js)$",
    r"\?ver=[\d\.]+$", r"wp-json/wp/v\d+/", r"xmlrpc\.php\?", r"wp-admin/.*", r"wp-content/cache/.*",
]
priority_paths = [ "/contact/", "/contact-us/", "/about/",  "/about-us/", "/team/", "/staff/", "/people/", "/leadership/", "/management/",
    "/support/", "/help/", "/press/", "/media/", "/privacy-policy/", "/terms/", "/legal/", "/impressum/", "/careers/"
]

file_lock = threading.Lock()
threads_list = []
all_emails = []

def extract_emails(hostname, page_source, all_emails, file_lock):
    try:
        found_emails = re.findall(email_pattern, page_source)
        if len(found_emails) != 0:
            email_domain = hostname.replace("www.", "")
            for email in found_emails:
                if email.endswith(email_domain):
                    with file_lock:
                        all_emails.append(email) 
    except Exception as e:
        pass

def validate_url(hostname, hosts_history, stack, url):
    host = urlparse(url).hostname
    mime_type, encoding = mimetypes.guess_type(url)
    if (url in stack or host != hostname or hosts_history[hostname] > 30 
            or (mime_type is not None and mime_type not in allowed_mime_types)):
        return False
    for subpath in unallowed_wordpress_paths:
        if subpath in url:
            return False
    for subpattern in unallowed_wordpress_patterns:
        if len(re.findall(subpattern, url)) != 0:
            return False
    print(f"[{host}] === ({url}) [{mime_type}]")
    return True

def hunt_site(driver, url, all_emails, file_lock, current_host, stack, hosts_history):
    try:
        driver.get(url)
    except Exception as e:
        return
    extract_emails(current_host, driver.page_source, all_emails, file_lock)
    found_links = re.findall(url_pattern, driver.page_source)
    for link in found_links:
         sec_url = link.strip()
         print(f"----> hunt_site trying url {sec_url}")
         if validate_url(current_host, hosts_history, stack, sec_url):
              stack.append(sec_url)
              hosts_history[current_host] = hosts_history[current_host] + 1
              hunt_site(driver, sec_url, all_emails, file_lock, current_host, stack, hosts_history)

def search_common_paths(driver, url, all_emails, file_lock, hostname, index):
    if index >= len(priority_paths) - 1:
        return

    target_page = url + priority_paths[index]
    target_page = target_page.replace("//", "/")

    try:
        driver.get(target_page)
    except Exception as e:
        return

    print(f"[{hostname}] === ({target_page})")
    extract_emails(hostname, driver.page_source, all_emails, file_lock)
    search_common_paths(driver, url, all_emails, file_lock, hostname, index + 1)

def thread_routine(lines, all_emails, file_lock, visited_urls):

    hosts_history = {}

    try:
        webdriver_options = Options()
        webdriver_options.add_argument("--headless")
        driver = webdriver.Firefox(options=webdriver_options)
        driver.set_page_load_timeout(30)

        for line in lines:
            url = line.strip()
            hostname = urlparse(url).hostname
            print(f"====> going for main url [{url}]:")
            visited_urls.append(url)
            hosts_history[hostname] = 1

            search_common_paths(driver, url, all_emails, file_lock, hostname, 0)
            hunt_site(driver, url, all_emails, file_lock, hostname, visited_urls, hosts_history)

        driver.close()
        driver.quit()
    except Exception as e:
        pass

if __name__ == "__main__":
    try:
        with (open("target_sites", 'r') as in_file,
            open("current_emails", 'w') as emails_file):
            counter = 0
            visited_urls = []
            lines = []
            for line in in_file:
                lines.append(line)
                if len(lines) >= 5:
                    thread = threading.Thread(target=thread_routine, args=(copy.deepcopy(lines), all_emails, file_lock, visited_urls,))
                    threads_list.append(thread)
                    thread.start()
                    if len(threads_list) >= 3:
                        for thread in threads_list:
                            thread.join()
                        threads_list.clear()
                    lines.clear()
                    try:
                        counter = counter + 1
                        if counter >= 30:
                            subprocess.run(["git", "add", "."])
                            subprocess.run(["git", "commit", "-m", "fucking_update"])
                            subprocess.run(["git", "push"])
                            counter = 0
                    except Exception as e:
                        pass
                    for email in all_emails:
                        emails_file.write(f"{email}\n")
                        emails_file.flush()
            if len(lines) != 0:
                thread = threading.Thread(target=thread_routine, args=(copy.deepcopy(lines), all_emails, file_lock, visited_urls,))
                threads_list.append(thread)
                thread.start()
                lines.clear()
                for email in all_emails:
                    emails_file.write(f"{email}\n")
                    emails_file.flush()

    except KeyboardInterrupt:
        print("catched keyboard interrupt!! FUCK YOU")
    except Exception as e:
        print(f"caught exception: {e}")
    finally:
        for thread in threads_list:
            thread.join()
        in_file.close()
        #os.fsync(all_emails.fileno())
        emails_file.close()
