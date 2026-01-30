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
            # Fotoğraf için en iyi kaliteyi bul
            if post.display_resources:
                # En yüksek çözünürlüklü kaynağı al
                best_resource = max(post.display_resources, key=lambda x: x.width * x.height)
                media_url = best_resource.src
                print(f"✅ Instaloader - En yüksek çözünürlük: {best_resource.width}x{best_resource.height}")
            else:
                # display_resources yoksa display_url kullan
                media_url = post.display_url
                print(f"⚠️ Instaloader - display_resources yok, display_url kullanıldı")

        print(f"📦 Final URL: {media_url}")
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
        
        # === VİDEO KONTROLÜ (Önce video kontrol et) ===
        video_match = re.search(r'property="og:video" content="([^"]+)"', response.text)
        if video_match:
            return jsonify({"success": True, "media_url": video_match.group(1), "type": "video"})

        # === RESİM (ORİJİNAL ORANLI) - GELIŞMIŞ ARAMA ===
        # 1. display_resources içindeki en büyük boyutlu resmi bul
        all_image_urls = []
        
        # display_resources array'ini bul
        display_resources_match = re.search(r'"display_resources":\[(.*?)\]', response.text, re.DOTALL)
        if display_resources_match:
            resources_json = display_resources_match.group(1)
            # Her bir resource'daki src'yi bul
            src_urls = re.findall(r'"src":"([^"]+)"', resources_json)
            all_image_urls.extend(src_urls)
        
        # 2. Tüm display_url'leri bul
        display_urls = re.findall(r'"display_url":"([^"]+)"', response.text)
        all_image_urls.extend(display_urls)
        
        # 3. Kare (1080x1080) olmayan en yüksek çözünürlüklü resmi seç
        if all_image_urls:
            # Kare olmayan resimleri filtrele (genişlik != yükseklik)
            non_square_images = []
            for img_url in all_image_urls:
                img_url = img_url.replace("\\u0026", "&").replace("&amp;", "&")
                # 1080x1080, 150x150 gibi kare boyutları atla
                if "1080x1080" not in img_url and "150x150" not in img_url and "320x320" not in img_url:
                    non_square_images.append(img_url)
            
            # Kare olmayan resim varsa en yüksek çözünürlüklüyü al
            if non_square_images:
                # URL'deki çözünürlüğü parse et (örn: 1080x1350)
                def get_resolution(url):
                    match = re.search(r'/(\d+)x(\d+)/', url)
                    if match:
                        return int(match.group(1)) * int(match.group(2))
                    return 0
                
                best_image = max(non_square_images, key=get_resolution)
                print(f"✅ Orijinal oranlı resim bulundu: {best_image}")
                return jsonify({
                    "success": True,
                    "media_url": best_image,
                    "type": "image"
                })
            else:
                # Kare olmayan bulunamadıysa en sonuncuyu al (genelde en yüksek kalite)
                img_url = all_image_urls[-1].replace("\\u0026", "&").replace("&amp;", "&")
                print(f"⚠️ Sadece kare resimler bulundu, en yükseği alındı: {img_url}")
                return jsonify({
                    "success": True,
                    "media_url": img_url,
                    "type": "image"
                })

        # === SON ÇARE: og:image (KARE PREVIEW) ===
        image_match = re.search(r'property="og:image" content="([^"]+)"', response.text)
        if image_match:
            img_url = image_match.group(1).replace("\\u0026", "&").replace("&amp;", "&")
            print(f"⚠️ Sadece og:image bulundu (kare): {img_url}")
            return jsonify({
                "success": True,
                "media_url": img_url,
                "type": "image"
            })
            
        return jsonify({"success": False, "error": "Medya bulunamadı."}), 403
    except Exception as e:
        print(f"try_alternative_method hatası: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
