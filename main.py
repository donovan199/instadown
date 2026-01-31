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

    # ÖNCELİKLE ALTERNATİF METODU DENE (Daha Güvenilir)
    print(f"🔥 İSTEK ALINDI - URL: {url}")
    print(f"🎯 Direkt scraping metodu kullanılıyor (Instaloader atlandı)...")
    return try_alternative_method(url)
    
    # Eski Instaloader kodu (şimdilik devre dışı)
    """
    try:
        print(f"🔥 INSTALOADER BAŞLADI - URL: {url}")
        
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

        print(f"📌 Shortcode: {shortcode}")
        
        L = get_loader()
        print(f"🔧 Loader oluşturuldu, Post çekiliyor...")
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        print(f"✅ Post başarıyla çekildi!")
        
        # Orijinal (Zoomsuz) medyayı al
        if post.is_video:
            media_url = post.video_url
            thumbnail_url = post.display_url  # Video thumbnail (tam boyut)
            print(f"📹 Video URL alındı")
            print(f"🖼️ Thumbnail URL: {thumbnail_url}")
            return jsonify({
                "success": True,
                "media_url": media_url,
                "thumbnail_url": thumbnail_url,
                "type": "video"
            })
        else:
            # Çoklu fotoğraf kontrolü (Carousel/Sidecar)
            if post.typename == 'GraphSidecar':
                print(f"📸 Çoklu fotoğraf tespit edildi!")
                media_urls = []
                for node in post.get_sidecar_nodes():
                    if node.is_video:
                        media_urls.append(node.video_url)
                    else:
                        media_urls.append(node.display_url)
                print(f"✅ {len(media_urls)} medya bulundu")
                return jsonify({
                    "success": True,
                    "media_urls": media_urls,
                    "type": "carousel"
                })
            else:
                # Tek fotoğraf - display_url kullan (tam boyut, kırpılmamış)
                media_url = post.display_url
                print(f"✅ Tek fotoğraf - display_url kullanıldı (tam boyut)")
                return jsonify({
                    "success": True,
                    "media_url": media_url,
                    "type": "image"
                })

    except Exception as e:
        print(f"❌ INSTALOADER BAŞARISIZ!")
        print(f"❌ Hata tipi: {type(e).__name__}")
        print(f"❌ Hata mesajı: {str(e)}")
        print(f"⚠️ Alternatif metoda geçiliyor...")
        return try_alternative_method(url)
    """

def try_alternative_method(url):
    print(f"🔄 ALTERNATIF METOD BAŞLADI")
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        print(f"🌐 HTML scraping yapılıyor...")
        response = requests.get(url, headers=headers, timeout=10)
        print(f"✅ HTML alındı, parse ediliyor...")
        
        # === VİDEO KONTROLÜ (Önce video kontrol et) ===
        video_match = re.search(r'property="og:video" content="([^"]+)"', response.text)
        if video_match:
            return jsonify({"success": True, "media_url": video_match.group(1), "type": "video"})

        # === RESİM (ORİJİNAL ORANLI) - YENİ MANTIK ===
        all_image_urls = []
        
        # 1. display_resources array'ini bul (EN KALİTELİ KAYNAK)
        display_resources_match = re.search(r'"display_resources":\[(.*?)\]', response.text, re.DOTALL)
        if display_resources_match:
            resources_json = display_resources_match.group(1)
            src_urls = re.findall(r'"src":"([^"]+)"', resources_json)
            print(f"📊 display_resources'dan {len(src_urls)} URL bulundu")
            all_image_urls.extend(src_urls)
        
        # 2. display_url'leri bul (YEDEK)
        display_urls = re.findall(r'"display_url":"([^"]+)"', response.text)
        print(f"📊 display_url'den {len(display_urls)} URL bulundu")
        all_image_urls.extend(display_urls)
        
        print(f"📊 Toplam {len(all_image_urls)} görsel URL bulundu")
        
        if all_image_urls:
            # URL'leri temizle
            clean_urls = [u.replace("\\u0026", "&").replace("&amp;", "&") for u in all_image_urls]
            
            # URL'lerdeki çözünürlüğü parse et ve en yüksek olanı seç
            def get_resolution_from_url(url):
                # URL'de /1080x1350/ gibi boyut bilgisi ara
                match = re.search(r'/(\d+)x(\d+)/', url)
                if match:
                    width = int(match.group(1))
                    height = int(match.group(2))
                    # Kare olanları cezalandır (düşük skor)
                    if width == height:
                        return width * height * 0.1  # Kare ise skorunu düşür
                    return width * height
                # Boyut bilgisi yoksa URL uzunluğuna göre (genelde uzun URL = kaliteli)
                return len(url)
            
            # En yüksek çözünürlüklü URL'yi seç
            best_image = max(clean_urls, key=get_resolution_from_url)
            
            # Seçilen URL'nin boyutunu logla
            match = re.search(r'/(\d+)x(\d+)/', best_image)
            if match:
                print(f"✅ Seçilen görsel: {match.group(1)}x{match.group(2)}")
            else:
                print(f"✅ Seçilen görsel: {best_image[:100]}...")
            
            return jsonify({
                "success": True,
                "media_url": best_image,
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
