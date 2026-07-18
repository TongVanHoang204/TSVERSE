"""
Công cụ cuối cùng để lấy video từ streamfree.vip.
Sử dụng nodriver (Chrome thật, ẩn automation) để vượt tường Access Denied,
tự động bắt link video hoặc blob.

Cài đặt một lần duy nhất:
    pip install nodriver yt-dlp
    python -m nodriver install    # Cài Chrome ẩn danh

Chạy: python lay_video_nodriver.py
"""

import asyncio
import base64
import re
import yt_dlp

EMBED_URL = "https://streamfree.vip/embed/v/jmAzrEHD"
OUTPUT = "video.mp4"

async def main():
    # Khởi tạo trình duyệt nodriver (chế độ ẩn, chống phát hiện tự động)
    from nodriver import start
    browser = await start(headless=False)  # headless=False để bạn giải captcha nếu có
    page = await browser.get(EMBED_URL)

    print("[*] Đã mở trang. Nếu cần giải captcha, hãy làm và chờ video phát.")
    print("[*] Nhấn Enter sau khi video bắt đầu chạy (có thể tua nhanh để chắc chắn)...")
    input()

    # Phương án 1: Tìm request mạng có .m3u8 / .mp4
    video_links = set()
    async def log_request(event):
        req = event.request
        if re.search(r'\.(m3u8|mp4)(\?|$)', req.url):
            video_links.add(req.url)
    page.add_handler(log_request, 'Network.requestWillBeSent')

    # Reload trang để bắt request (sau khi đã có cookie/captcha)
    await page.reload()
    await asyncio.sleep(5)

    if video_links:
        link = sorted(video_links)[0]
        print(f"[+] Bắt được link: {link}")
        ydl_opts = {'outtmpl': OUTPUT, 'format': 'best', 'merge_output_format': 'mp4', 'quiet': False}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
        print(f"[+] Đã lưu {OUTPUT}")
    else:
        # Phương án 2: Lấy blob từ thẻ video
        print("[*] Không thấy request mạng, thử trích xuất blob...")
        blob_url = await page.evaluate('''
            () => {
                const v = document.querySelector('video');
                return v ? v.src : null;
            }
        ''')
        if blob_url and blob_url.startswith('blob:'):
            data_b64 = await page.evaluate('''
                async (blobUrl) => {
                    const resp = await fetch(blobUrl);
                    const blob = await resp.blob();
                    return new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onload = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                    });
                }
            ''', blob_url)
            if data_b64 and ',' in data_b64:
                _, encoded = data_b64.split(',', 1)
                video_bytes = base64.b64decode(encoded)
                with open(OUTPUT, 'wb') as f:
                    f.write(video_bytes)
                print(f"[+] Đã lưu video từ blob vào {OUTPUT}")
            else:
                print("[-] Không decode được blob.")
        else:
            print("[-] Không tìm thấy video. Trang có thể dùng DRM không thể tải.")

    await browser.stop()

if __name__ == '__main__':
    asyncio.run(main())