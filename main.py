import os
import random
import requests
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
import instaloader

app = Flask(__name__)
CORS(app)

# Farklı User-Agent'lar kullanarak bot algılanmasını zorlaştırıyoruz
USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
]

def get_loader():
    ua = random.choice(USER_AGENTS)
    return instaloader.Instaloader(user_agent=ua)

@app.route('/coz', methods=['GET'])
def coz():
    url = request.args.get('url')
    if not url:
        return jsonify({"success": False, "error": "URL eksik"}), 400

    try:
        # 1. Önce Instaloader ile deneyelim (En profesyonel yöntem)
        shortcode = None
        if "/p/" in url:
            shortcode = url.split("/p/")[1].split("/")[0]
        elif "/reels/" in url:
            shortcode = url.split("/reels/")[1].split("/")[0]
        elif "/reel/" in url:
            shortcode = url.split("/reel/")[1].split("/")[0]
        elif "/tv/" in url:
            shortcode = url.split("/tv/")[1].split("/")[0]
            
        if not shortcode:
            parts = [p for p in url.split("/") if p]
            if len(parts) >= 1:
                shortcode = parts[-1].split("?")[0]

        L = get_loader()
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # Orijinal (Zoomsuz) medyayı al
        if post.is_video:
            media_url = post.video_url
        else:
            if post.display_resources:
                media_url = max(post.display_resources, key=lambda x: x.width * x.height).src
            else:
                media_url = post.display_url

        return jsonify({
            "success": True,
            "media_url": media_url,
            "type": "video" if post.is_video else "image"
        })

    except Exception as e:
        print(f"Instaloader hatası: {e}. Alternatif metod deneniyor...")
        return try_alternative_method(url)

def try_alternative_method(url):
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10)
        
        # === RESİM (ORİJİNAL ORANLI) ===
        # JSON içindeki tüm display_url linklerini bul (og:image kullanmıyoruz)
        # Listenin EN SONUNDAKİ URL, her zaman en yüksek kaliteli ve orijinal oranlıdır.
        display_resources = re.findall(r'"display_url":"([^"]+)"', response.text)
        if display_resources:
            img_url = display_resources[-1].replace("\\u0026", "&").replace("&amp;", "&")
            return jsonify({
                "success": True,
                "media_url": img_url,
                "type": "image"
            })

        # === VİDEO KONTROLÜ ===
        video_match = re.search(r'property="og:video" content="([^"]+)"', response.text)
        if video_match:
            return jsonify({"success": True, "media_url": video_match.group(1), "type": "video"})

        # === SON ÇARE (KARE PREVIEW - Sadece hiçbir şey bulunamazsa) ===
        image_match = re.search(r'property="og:image" content="([^"]+)"', response.text)
        if image_match:
            img_url = image_match.group(1).replace("\\u0026", "&").replace("&amp;", "&")
            return jsonify({
                "success": True,
                "media_url": img_url,
                "type": "image"
            })
            
        return jsonify({"success": False, "error": "Medya bulunamadı."}), 403
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
