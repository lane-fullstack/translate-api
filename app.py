from flask import Flask, request, jsonify
import re
import yaml
from opencc import OpenCC
from langdetect import detect
from argostranslate import translate, package
from functools import wraps

# 初始化 Flask 应用
app = Flask(__name__)

# 加载配置
def load_config():
    try:
        with open("config.yaml", "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}

config = load_config()
API_KEY = config.get("api_key")

# 鉴权装饰器
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not API_KEY:
            return f(*args, **kwargs)
        
        # 尝试从 Header 或 Query Parameter 获取 key
        request_key = request.headers.get("X-API-KEY") or request.args.get("key")
        
        if request_key != API_KEY:
            return jsonify({"error": "Unauthorized: Invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return decorated_function

# 初始化转换器与模型
re_chinese = re.compile(r'[\u4e00-\u9fff]')
cc_to_simplified = OpenCC('t2s')  # 繁 → 简

# 语言对
required_pairs = [
    ("zh", "en"), ("en", "zh"),
    ("en", "es"), ("es", "en"),
]

# 加载模型
def is_installed(from_code, to_code):
    for lang in translate.get_installed_languages():
        if lang.code == from_code:
            return any(t.to_lang.code == to_code for t in lang.translations_to)
    return False

def install_all_models():
    print("🌐 Fetching all available language packages...")
    try:
        available_packages = package.get_available_packages()
    except Exception as e:
        print(f"❌ Failed to fetch packages: {e}")
        return

    count = 0
    for pkg in available_packages:
        from_code = pkg.from_code
        to_code = pkg.to_code

        # 检查是否已安装
        if is_installed(from_code, to_code):
            continue

        print(f"⬇️ Installing: {from_code} → {to_code}")
        try:
            downloaded_path = pkg.download()
            package.install_from_path(downloaded_path)
            count += 1
        except Exception as e:
            print(f"❌ Failed to install {from_code} → {to_code}: {e}")

    translate.load_installed_languages()
    print(f"\n✅ Done. Installed {count} new language models.")


def install_models():
    try:
        available_packages = package.get_available_packages()
    except Exception as e:
        print(f"Failed to fetch packages: {e}")
        return

    for from_lang, to_lang in required_pairs:
        if is_installed(from_lang, to_lang):
            continue
        pkg = next((p for p in available_packages
                    if p.from_code == from_lang and p.to_code == to_lang), None)
        if pkg:
            downloaded_path = pkg.download()
            package.install_from_path(downloaded_path)
    translate.load_installed_languages()

install_models()
installed_languages = translate.get_installed_languages()

# 🔍 检测语言
def detect_language(text):
    has_chinese = bool(re_chinese.search(text))
    lang_code = 'unknown'
    normalized_text = text

    try:
        lang_code = detect(text)
    except:
        pass

    if has_chinese:
        normalized_text = cc_to_simplified.convert(text)
        lang_code = 'zh'
    return {
        'detected_lang': lang_code,
        'normalized_text': normalized_text
    }

# 🔁 翻译接口
def trans(detected_lang, text):
    from_lang = next((lang for lang in installed_languages if lang.code.startswith(detected_lang)), None)
    if not from_lang:
        raise Exception(f"Model for source language '{detected_lang}' not installed.")

    results = {}
    for target_code in ['en', 'es', 'zh']:
        to_lang = next((lang for lang in installed_languages if lang.code == target_code), None)
        if not to_lang:
            results[target_code] = f"Model for '{target_code}' not installed."
            continue
        try:
            translation = from_lang.get_translation(to_lang)
            translated_text = translation.translate(text)
            results[target_code] = translated_text
        except Exception as e:
            results[target_code] = f"Translation error: {str(e)}"
    return results

# 📌 API 路由 检测语言
@app.route("/detect", methods=["POST"])
@require_api_key
def api_detect():
    data = request.get_json()
    text = data.get("text", "")
    result = detect_language(text)
    return jsonify(result)


@app.route("/down", methods=["GET"])
@require_api_key
def api_down():
    try:
        install_all_models()
        return jsonify({"status": "success", "message": "All models installed successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/translate", methods=["POST"])
@require_api_key
def api_translate():
    data = request.get_json()
    text = data.get("text", "")
    info = detect_language(text)
    try:
        translations = trans(info['detected_lang'], info['normalized_text'])
        return jsonify({
            'detected': info['detected_lang'],
            'normalized': info['normalized_text'],
            'translations': translations
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 新增接口：中文（简/繁）转英文
@app.route("/translate_zh_en", methods=["POST"])
@require_api_key
def api_translate_zh_en():
    data = request.get_json()
    
    # 兼容 {"text": ...} 格式
    input_data = data
    if isinstance(data, dict) and "text" in data:
        input_data = data["text"]

    def translate_text(text):
        if not text:
            return ""
        # 繁体转简体
        normalized_text = cc_to_simplified.convert(str(text))
        
        from_lang = next((lang for lang in installed_languages if lang.code == 'zh'), None)
        to_lang = next((lang for lang in installed_languages if lang.code == 'en'), None)
        
        if from_lang and to_lang:
            try:
                translation = from_lang.get_translation(to_lang)
                return translation.translate(normalized_text)
            except Exception:
                return text
        return text

    if isinstance(input_data, list):
        results = [translate_text(t) for t in input_data]
        return jsonify(results)
    else:
        result = translate_text(input_data)
        return jsonify(result)

# 启动服务
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)