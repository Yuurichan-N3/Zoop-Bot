import json
import requests
from datetime import datetime, timezone
import urllib.parse
import time
import logging
import random
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler

# Banner untuk Zoop Bot
console = Console()
console.print("""
[bold cyan]╔══════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║       🌟 ZOOP BOT - Automated Spinning       ║[/bold cyan]
[bold cyan]║   Automate your Zoop spin tasks with ease!   ║[/bold cyan]
[bold cyan]║  Developed by: https://t.me/sentineldiscus   ║[/bold cyan]
[bold cyan]╚══════════════════════════════════════════════╝[/bold cyan]
""")

# Setup logging dengan RichHandler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]  # Aktifkan markup
)
logger = logging.getLogger("zoop_bot")

# Fungsi untuk membaca query dari file data.txt
def get_queries(filename="data.txt"):
    try:
        with open(filename, 'r') as file:
            queries = [line.strip() for line in file.readlines() if line.strip()]
            if not queries:
                raise ValueError("File data.txt kosong!")
            return queries
    except FileNotFoundError:
        logger.error("File data.txt tidak ditemukan!")
        return []

# Fungsi untuk ekstrak user_id dari query
def extract_user_id(query):
    try:
        parsed = urllib.parse.parse_qs(query)
        user_str = parsed.get('user', [None])[0]
        if not user_str:
            raise ValueError("Field 'user' tidak ditemukan di query!")
        user_data = json.loads(user_str)
        user_id = user_data.get('id', None)
        if not user_id:
            raise ValueError("ID tidak ditemukan di dalam field 'user'!")
        return int(user_id)
    except Exception as e:
        logger.error(f"Gagal memparse query: {e}")
        return None

# Fungsi untuk membaca dan memilih proxy dari file proxy.txt
def load_proxies(filename="proxy.txt"):
    try:
        with open(filename, 'r') as file:
            proxies = [line.strip() for line in file.readlines() if line.strip()]
            if not proxies:
                logger.warning("File proxy.txt kosong. Menjalankan tanpa proxy.")
                return None
            proxy = random.choice(proxies)
            return parse_proxy(proxy)
    except FileNotFoundError:
        logger.warning("File proxy.txt tidak ditemukan. Menjalankan tanpa proxy.")
        return None

# Fungsi untuk memparse string proxy menjadi format yang diterima requests
def parse_proxy(proxy_string):
    try:
        # Contoh format proxy: http://username:password@host:port atau http://host:port
        protocol = 'http'  # Default protocol
        if proxy_string.startswith('http://') or proxy_string.startswith('https://'):
            protocol, rest = proxy_string.split('://', 1)
        else:
            rest = proxy_string

        # Pisahkan host:port dan username:password (jika ada)
        if '@' in rest:
            auth, host_port = rest.split('@', 1)
            username, password = auth.split(':', 1)
            host, port = host_port.split(':', 1)
            proxy_url = f"{protocol}://{username}:{password}@{host}:{port}"
        else:
            host, port = rest.split(':', 1)
            proxy_url = f"{protocol}://{host}:{port}"

        logger.info(f"Menggunakan proxy: {proxy_url}")
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    except Exception as e:
        logger.error(f"Format proxy tidak valid: {proxy_string}. Error: {e}")
        return None

# Fungsi untuk mendapatkan token dari query dengan initData
def get_token_from_query(query, proxies=None):
    url = "https://tgapi.zoop.com/api/oauth/telegram"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "origin": "https://tgapp.zoop.com",
        "referer": "https://tgapp.zoop.com/",
    }
    data = json.dumps({"initData": query})
    try:
        response = requests.post(url, headers=headers, data=data, proxies=proxies)
        if response.status_code == 201:
            response_data = response.json()
            token = response_data.get("data", {}).get("access_token")
            if token:
                logger.info("Token berhasil diperoleh!")
                return token
            else:
                logger.error(f"Response tidak berisi access_token di 'data': {response.text}")
                return None
        else:
            logger.error(f"Gagal mendapatkan token: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error saat mendapatkan token: {e}")
        return None

# Headers dengan token
def get_headers(token):
    headers = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9",
        "authorization": f"Bearer {token}",
        "cache-control": "no-cache",
        "connection": "keep-alive",
        "content-type": "application/json",
        "host": "tgapi.zoop.com",
        "origin": "https://tgapp.zoop.com",
        "pragma": "no-cache",
        "referer": "https://tgapp.zoop.com/",
        "sec-ch-ua": '"Chromium";v="133", "Microsoft Edge WebView2";v="133", "Not(A:Brand";v="99", "Microsoft Edge";v="133"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"
    }
    return headers

# Fungsi untuk memeriksa informasi daily task
def check_daily_info(user_id, token, proxies=None):
    url = f"https://tgapi.zoop.com/api/tasks/{user_id}"
    headers = get_headers(token)
    try:
        response = requests.get(url, headers=headers, proxies=proxies)
        if response.status_code == 200:
            response_data = response.json()
            daily_info = {
                "daily_claimed": response_data.get("data", {}).get("claimed", False),
                "day_claim": response_data.get("data", {}).get("dayClaim", 0)
            }
            logger.info(f"Daily Info untuk user ID {user_id}: Claimed={daily_info['daily_claimed']}, Day={daily_info['day_claim']}")
            return daily_info
        else:
            logger.error(f"Gagal memeriksa daily info: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error saat memeriksa daily info: {e}")
        return None

# Fungsi untuk mengklaim daily task
def claim_daily_task(user_id, token, proxies=None, index=1):
    url = f"https://tgapi.zoop.com/api/tasks/rewardDaily/{user_id}"
    headers = get_headers(token)
    payload = {"index": index}
    try:
        response = requests.post(url, headers=headers, json=payload, proxies=proxies)
        if response.status_code == 201:
            response_data = response.json()
            logger.info(f"Daily task untuk user ID {user_id} berhasil diklaim! Response: {response_data}")
            return True
        else:
            logger.error(f"Gagal mengklaim daily task: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error saat mengklaim daily task: {e}")
        return False

# Fungsi untuk mengirim request ke /api/users/spin terus menerus
def send_spin_request(user_id, token, proxies=None):
    url = "https://tgapi.zoop.com/api/users/spin"
    headers = get_headers(token)
    payload = {
        "userId": user_id,
        "date": datetime.now(timezone.utc).isoformat()
    }
    
    while True:
        try:
            response = requests.post(url, headers=headers, json=payload, proxies=proxies)
            if response.status_code == 201:
                response_data = response.json()
                reward = response_data.get("data", {}).get("circle", {}).get("name", "Unknown")
                logger.info(f"Spin request untuk user ID {user_id} berhasil! ({response.status_code}) Reward: {reward} points")
            else:
                logger.warning("Spin habis, menunggu loop")
                break
            time.sleep(0)  # Tunggu 3 detik sebelum request berikutnya
        except Exception as e:
            logger.error(f"Error saat mengirim spin request: {e}")
            break

# Fungsi untuk memproses satu akun
def process_account(query, index):
    logger.info(f"[bold cyan]=== Memproses Akun {index} ===[/bold cyan]")
    user_id = extract_user_id(query)
    if user_id is None:
        logger.error(f"Akun {index}: Gagal mendapatkan user ID, skip.")
        return {"index": index, "user_id": "N/A", "status": "Gagal (User ID)"}

    # Muat proxy untuk akun ini
    proxies = load_proxies()

    token = get_token_from_query(query, proxies=proxies)
    if token:
        logger.info(f"Akun {index}: Token diperoleh dari query.")
        
        # Periksa informasi daily task
        daily_info = check_daily_info(user_id, token, proxies=proxies)
        if daily_info and not daily_info["daily_claimed"]:
            logger.info(f"Akun {index}: Daily task belum diklaim, mencoba mengklaim...")
            claim_success = claim_daily_task(user_id, token, proxies=proxies)
            if claim_success:
                logger.info(f"Akun {index}: Daily task berhasil diklaim!")
            else:
                logger.error(f"Akun {index}: Gagal mengklaim daily task.")
        elif daily_info:
            logger.info(f"Akun {index}: Daily task sudah diklaim hari ini.")
        else:
            logger.error(f"Akun {index}: Gagal memeriksa status daily task.")

        # Lanjutkan ke proses spin
        send_spin_request(user_id, token, proxies=proxies)
        return {"index": index, "user_id": user_id, "status": "Selesai"}
    else:
        logger.error(f"Akun {index}: Gagal mendapatkan token, skip.")
        return {"index": index, "user_id": user_id, "status": "Gagal (Token)"}

# Fungsi untuk menampilkan tabel hasil
def display_results(results):
    table = Table(title="Hasil Pemrosesan Akun", show_header=True, header_style="bold magenta")
    table.add_column("No", style="cyan", justify="center")
    table.add_column("User ID", style="green")
    table.add_column("Status", style="yellow")
    
    for result in results:
        table.add_row(
            str(result["index"]),
            str(result["user_id"]),
            result["status"]
        )
    console.print(table)

# Fungsi untuk mendapatkan jumlah thread dari user
def get_thread_count():
    while True:
        try:
            thread_count = int(input("Masukkan jumlah thread (default 5): ") or 5)
            if thread_count < 1:
                console.print("[bold red]Jumlah thread harus minimal 1![/bold red]")
                continue
            return thread_count
        except ValueError:
            console.print("[bold red]Masukkan angka yang valid![/bold red]")

# Main execution dengan ThreadPoolExecutor dan loop 6 jam
if __name__ == "__main__":
    # Dapatkan jumlah thread dari user di awal
    max_threads = get_thread_count()
    console.print(f"[bold green]Menggunakan {max_threads} thread untuk pemrosesan.[/bold green]")

    queries = get_queries()
    if not queries:
        logger.error("Tidak ada query untuk diproses!")
    else:
        while True:  # Loop utama tanpa henti
            console.print("[bold green]Memulai pemrosesan akun...[/bold green]")
            results = []
            
            # Gunakan ThreadPoolExecutor dengan jumlah thread dari input user
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = [executor.submit(process_account, query, i) for i, query in enumerate(queries, 1)]
                for future in futures:
                    results.append(future.result())
            
            # Tampilkan hasil dalam tabel
            display_results(results)

            # Tunggu 6 jam sebelum loop berikutnya
            console.print("\n[bold blue]Menunggu 6 jam untuk loop berikutnya...[/bold blue]")
            for remaining in range(21600, 0, -1):  # 6 jam = 21.600 detik
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                seconds = remaining % 60
                console.print(f"Sisa waktu: {hours} jam {minutes} menit {seconds} detik", end="\r")
                time.sleep(1)
            console.print("\n[bold green]Loop berikutnya dimulai![/bold green]\n")
