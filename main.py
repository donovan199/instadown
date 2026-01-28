from flask import Flask, request, jsonify
import instaloader
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Flutter uygulamasının sunucuya erişmesine izin verir
L = instaloader.Instaloader()

@app.route('/coz', methods=['GET'])
def coz():
    url = request.args.get('url')
    if not url:
        return jsonify({"success": False, "error": "URL eksik"}), 400

    try:
        # URL'den shortcode'u çıkar (Örn: https://www.instagram.com/p/C6kL_O.../ -> C6kL_O)
        parts = [p for p in url.split("/") if p]
        shortcode = parts[-1] if "instagram.com" in parts[-2] else parts[-1]
        
        # Daha güvenli shortcode çıkarma
        if "/p/" in url:
            shortcode = url.split("/p/")[1].split("/")[0]
        elif "/reel/" in url:
            shortcode = url.split("/reel/")[1].split("/")[0]
        elif "/tv/" in url:
            shortcode = url.split("/tv/")[1].split("/")[0]

        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # En yüksek çözünürlüklü linki yakala
        media_url = post.video_url if post.is_video else post.display_url
        
        return jsonify({
            "success": True,
            "media_url": media_url,
            "type": "video" if post.is_video else "image",
            "thumbnail": post.display_url
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
