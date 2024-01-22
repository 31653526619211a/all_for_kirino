# main.py

from ehentai_utils import create_ehentai_database, get_metadata_and_save, get_download_urls

# 创建E-Hentai数据库
create_ehentai_database()

# 使用示例
api_url = "https://api.e-hentai.org/api.php"
input_json_path = "main.json"
output_json_path = "all_metadata.json"

get_metadata_and_save(api_url, input_json_path, output_json_path)

get_download_urls("username", "password", "all_metadata.json", "dl_url.txt")
