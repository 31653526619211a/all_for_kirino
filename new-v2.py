
import requests
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm
import sqlite3
# 创建SQLite数据库连接
conn = sqlite3.connect('metadata.db')

# 创建游标对象以执行SQL查询
cursor = conn.cursor()
MAX_RETRIES = 50
WAIT_TIME_SECONDS = 10
# 执行一次以在数据库中创建metadata表
cursor.execute("CREATE TABLE IF NOT EXISTS metadata (gid INTEGER, token TEXT, archive_download TEXT)")

def load_galleries_from_json(file_path):
    """Load gallery information from JSON file."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        return json.load(file)
def save_to_database(data):
    """将数据保存到SQLite数据库中。"""
    for item in data['gmetadata']:
        gid = item['gid']
        token = item['token']
       archiver_key = item.get('archiver_key', '')  # 如果需要，替换为您的archiver_key
        archive_download = f'https://e-hentai.org/archiver.php?gid={gid}&token={token}&or={archiver_key}'

        # 将数据插入数据库
        cursor.execute("INSERT INTO metadata (gid, token, archive_download) VALUES (?, ?, ?)", (gid, token, archive_download))

    # 将更改提交到数据库
    conn.commit()
def add_archive_download(metadata):
    """Add 'archive_download' key to each metadata item."""
    for item in metadata['gmetadata']:
        gid = item['gid']
        token = item['token']
        archiver_key = item.get('archiver_key', '')  # Replace with your archiver_key if needed
        item['archive_download'] = f'https://e-hentai.org/archiver.php?gid={gid}&token={token}&or={archiver_key}'

def send_api_request(api_url, data):
    """Send API request and return JSON response."""
    try:
        response = requests.post(api_url, json=data)
        response.raise_for_status()  # Check for HTTP errors
        return response.json()
    except requests.RequestException as e:
        print(f"API request failed: {e}")
        return None

def get_metadata(api_url, gidlist):
    """Get metadata from API for given gidlist."""
    all_responses = []

    for i in range(0, len(gidlist), 25):
        data = {
            "method": "gdata",
            "namespace": 1,
            "gidlist": gidlist[i:i+25]
        }

        # Send API request
        metadata = send_api_request(api_url, data)

        if metadata:
            add_archive_download(metadata)
            all_responses.extend(metadata['gmetadata'])

            # If not the last batch, wait for 5 seconds
            if i + 25 < len(gidlist):
                print(f"Waiting {WAIT_TIME_SECONDS} seconds before the next batch...")
                time.sleep(WAIT_TIME_SECONDS)

    return all_responses
def get_metadata_and_save(api_url, input_json_path):
    """从API获取元数据并保存到SQLite数据库中。"""
    galleries = load_galleries_from_json(input_json_path)

    # 准备用于API请求的gidlist
    gidlist = [[gallery["gid"], gallery["token"]] for gallery in galleries]

    # 获取元数据
    all_metadata = get_metadata(api_url, gidlist)

    # 将元数据保存到SQLite数据库
    save_to_database({"gmetadata": all_metadata})

    print("所有请求完成，响应保存到数据库中")


def login(driver, username, password):
    """Login to the website."""
    driver.get("https://e-hentai.org/bounce_login.php")

    username_field = driver.find_element(By.NAME, "UserName")
    password_field = driver.find_element(By.NAME, "PassWord")

    username_field.send_keys(username)
    password_field.send_keys(password)

    login_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.NAME, "ipb_login_submit"))
    )
    login_button.click()

    time.sleep(10)
def process_target_pages(driver, json_file_path, output_file_path):
    """Process target pages from a JSON file."""
    with open(json_file_path, "r", errors="ignore") as json_file:
        data = json.load(json_file)

    total_entries = sum(1 for entry in data['gmetadata'] if 'archive_download' in entry)

    for entry in tqdm(data['gmetadata'], total=total_entries, desc="Processing Pages"):
        if 'archive_download' in entry:
            target_page = entry['archive_download']
            process_single_target_page(driver, target_page, output_file_path)
def process_single_target_page(driver, target_page):
    """处理单个目标页面。"""
    driver.get(target_page)

    for _ in range(MAX_RETRIES):
        try:
            button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//input[contains(@value, 'Download Original Archive')]"))
            )

            button.click()

            time.sleep(WAIT_TIME_SECONDS)

            current_url = driver.current_url

            print(f"点击 {target_page} 的 Download Original Archive 按钮后的URL：", current_url)

            # 在 process_single_target_page 函数中
            # 将下载信息插入 download_info 表
            cursor.execute("INSERT INTO download_info (gid, token, gallery_url, archive_download, target_page_url, processed_url) VALUES (?, ?, ?, ?, ?, ?)",
                           (gid, token, f'https://e-hentai/g/{gid}/{token}', archive_download, target_page, f"{current_url}?star=1"))
            conn.commit()


            break
        except Exception as e:
            print(f"发生错误：{e}")
            print(f"重试... ({MAX_RETRIES} 次)")
def get_download_urls(username, password, json_file_path, output_file_path):
    """Main function to get download URLs."""
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    try:
        login(driver, username, password)
        process_target_pages(driver, json_file_path, output_file_path)

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        driver.quit()
# 关闭SQLite连接
conn.close()
# 使用示例
api_url = "https://api.e-hentai.org/api.php"
input_json_path = "main.json"
output_json_path = "all_metadata.json"

get_metadata_and_save(api_url, input_json_path, output_json_path)

get_download_urls("username", "password", "all_metadata.json", "dl_url.txt")


#MAX_RETRIES = 50表示最大重试次数

#WAIT_TIME_SECONDS = 10表示每次重试之间的等待时间
