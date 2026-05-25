import urllib.request
import os
import ssl

url = "https://openaipublic.azureedge.net/main/whisper/models/d3dd57d32accea0b295c96e26691aa14d8822fac7d9d27d5dc00b4ca2826dd03/tiny.en.pt"
dest = r"C:\Users\Strenght Awa\.cache\whisper\tiny.en.pt"

os.makedirs(os.path.dirname(dest), exist_ok=True)

print(f"Downloading {url} to {dest}...")

# Bypass SSL verification if needed (sometimes helps on some corporate/restricted networks)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def progress(block_num, block_size, total_size):
    read_so_far = block_num * block_size
    if total_size > 0:
        percent = read_so_far * 1e2 / total_size
        print(f"\rProgress: {percent:.2f}% ({read_so_far}/{total_size} bytes)", end="")
    else:
        print(f"\rDownloaded: {read_so_far} bytes", end="")

try:
    urllib.request.urlretrieve(url, dest, reporthook=progress)
    print("\nDownload complete.")
except Exception as e:
    print(f"\nDownload failed: {e}")
