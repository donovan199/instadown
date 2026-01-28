import instaloader
from flask import Flask, request, jsonify
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app)

# Instagram'ın bot algılamasını zorlaştırmak için mobil tarayıcı kimliği
USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
L = instaloader.Instaloader(user_agent=USER_AGENT)

def extract_shortcode(url):
    # Instagram linkinden kısa kodu (p/abcde/ veya reels/abcde/) güvenli şekilde ayıklar
    match = re.search(r'/(?:p|reels|tv|share/v)/([^/?#&]+)', url)
    return match.group(1) if match else None

@app.route('/coz', methods=['GET'])
def coz():
    url = request.args.get('url')
    if not url:
        return jsonify({"success": False, "error": "URL parametresi eksik"}), 400

    try:
        shortcode = extract_shortcode(url)
        if not shortcode:
            return jsonify({"success": False, "error": "Geçersiz Instagram linki"}), 400
        
        # Post verisini çek
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # Video ise video_url, resim ise display_url döndür
        media_url = post.video_url if post.is_video else post.display_url
        
        return jsonify({
            "success": True,
            "media_url": media_url,
            "type": "video" if post.is_video else "image",
            "shortcode": shortcode
        })
    except instaloader.exceptions.InstaloaderException as e:
        return jsonify({"success": False, "error": f"Instagram hatası: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": f"Sistem hatası: {str(e)}"}), 500

if __name__ == '__main__':
    # Render portu için 10000 varsayılandır
    app.run(host='0.0.0.0', port=10000)
