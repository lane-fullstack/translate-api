import os
import threading
import re
import yaml
from functools import wraps

from flask import Flask, request, jsonify
from opencc import OpenCC
from langdetect import detect
from argostranslate import translate, package

# =============================================================================
# Configuration & Initialization
# =============================================================================

# Set the model directory. This MUST be done before importing argostranslate
# or using any of its functions if you want to customize the path.
if "ARGOS_PACKAGES_DIR" not in os.environ:
    os.environ["ARGOS_PACKAGES_DIR"] = "./models"

# Initialize Flask application
app = Flask(__name__)

def load_config():
    """
    Loads configuration from 'config.yaml'.
    Returns an empty dict if the file is not found.
    """
    try:
        with open("config.yaml", "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}

# Load config and API key
config = load_config()
API_KEY = config.get("api_key")

# Initialize Chinese converter (Traditional -> Simplified)
# This is used to normalize Chinese input before translation.
re_chinese = re.compile(r'[\u4e00-\u9fff]')
cc_to_simplified = OpenCC('t2s')

# Define required language pairs for initial setup
# These pairs will be checked and installed on startup if missing.
required_pairs = [
    ("zh", "en"), ("en", "zh"),
    ("en", "es"), ("es", "en"),
]

# =============================================================================
# Helper Functions
# =============================================================================

def require_api_key(f):
    """
    Decorator to require an API key for endpoints.
    Checks 'X-API-KEY' header or 'key' query parameter.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not API_KEY:
            return f(*args, **kwargs)
        
        request_key = request.headers.get("X-API-KEY") or request.args.get("key")
        
        if request_key != API_KEY:
            return jsonify({"code": 401, "msg": "Unauthorized: Invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return decorated_function

def success_response(data=None, msg="ok"):
    """Standardized success response format."""
    return jsonify({
        "code": 0,
        "msg": msg,
        "data": data if data is not None else {}
    })

def error_response(msg="error", code=500):
    """Standardized error response format."""
    return jsonify({
        "code": code,
        "msg": msg
    })

def is_installed(from_code, to_code):
    """
    Checks if a translation model from 'from_code' to 'to_code' is installed.
    """
    for lang in translate.get_installed_languages():
        if lang.code == from_code:
            return any(t.to_lang.code == to_code for t in lang.translations_to)
    return False

def _install_packages_async(packages_to_install):
    """
    Background task to download and install a list of packages.
    Updates the global 'installed_languages' list upon completion.
    """
    count = 0
    for pkg_info in packages_to_install:
        print(f"⬇️ Installing: {pkg_info['from_code']} → {pkg_info['to_code']}")
        try:
            # Re-fetch available packages to get the package object for downloading
            available_packages = package.get_available_packages()
            pkg = next((p for p in available_packages
                        if p.from_code == pkg_info['from_code'] and p.to_code == pkg_info['to_code']), None)
            if pkg:
                downloaded_path = pkg.download()
                package.install_from_path(downloaded_path)
                count += 1
        except Exception as e:
            print(f"❌ Failed to install {pkg_info['from_code']} → {pkg_info['to_code']}: {e}")
    
    if count > 0:
        # Reload installed languages to reflect changes
        translate.load_installed_languages()
        global installed_languages
        installed_languages = translate.get_installed_languages()
        print(f"\n✅ Done. Installed {count} new language models.")

def get_models_to_install():
    """
    Fetches all available packages and filters out the ones that are already installed.
    Returns a list of dictionaries containing package info.
    """
    print("🌐 Fetching all available language packages...")
    packages_to_install = []
    try:
        available_packages = package.get_available_packages()
        for pkg in available_packages:
            if not is_installed(pkg.from_code, pkg.to_code):
                packages_to_install.append({
                    "from_code": pkg.from_code,
                    "to_code": pkg.to_code,
                    "from_name": pkg.from_name,
                    "to_name": pkg.to_name,
                })
    except Exception as e:
        print(f"❌ Failed to fetch packages: {e}")
    return packages_to_install

def install_initial_models():
    """
    Installs the required language pairs defined in 'required_pairs' on startup.
    """
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
            print(f"⬇️ Installing required model: {from_lang} → {to_lang}")
            downloaded_path = pkg.download()
            package.install_from_path(downloaded_path)
    
    translate.load_installed_languages()

def detect_language(text):
    """
    Detects the language of the input text.
    Special handling for Chinese to normalize Traditional to Simplified.
    """
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

def trans(from_code, to_code, text):
    """
    Core translation logic.
    Finds the source and target languages and executes translation.
    Raises Exception if models are missing.
    """
    from_lang = next((lang for lang in installed_languages if lang.code == from_code), None)
    to_lang = next((lang for lang in installed_languages if lang.code == to_code), None)

    if not from_lang:
        raise Exception(f"Model for source language '{from_code}' not installed.")
    if not to_lang:
        raise Exception(f"Model for target language '{to_code}' not installed.")

    translation = from_lang.get_translation(to_lang)
    return translation.translate(text)

# =============================================================================
# Application Startup
# =============================================================================

# Install initial required models
install_initial_models()

# Load installed languages into memory
installed_languages = translate.get_installed_languages()

# =============================================================================
# API Routes
# =============================================================================

@app.route("/translate", methods=["POST"])
@require_api_key
def api_translate():
    """
    Endpoint for single or batch translation.
    Supports 'text' (string) or 'texts' (list of strings).
    """
    data = request.get_json()
    if not data:
        return error_response("Invalid JSON", 400)

    source = data.get("source")
    target = data.get("target")
    text = data.get("text")
    texts = data.get("texts")

    if not source or not target:
        return error_response("Missing 'source' or 'target' language code", 400)

    if text is None and texts is None:
         return error_response("Missing 'text' or 'texts' field", 400)

    try:
        # Single text translation
        if text is not None:
            if source == 'zh':
                text = cc_to_simplified.convert(text)
            
            translated_text = trans(source, target, text)
            return success_response({
                "translated_text": translated_text,
                "source": source,
                "target": target
            })
        
        # Batch translation
        if texts is not None:
            if not isinstance(texts, list):
                return error_response("'texts' must be a list", 400)
            
            results = []
            for t in texts:
                if source == 'zh':
                    t = cc_to_simplified.convert(t)
                results.append(trans(source, target, t))
            
            return success_response({
                "translations": results,
                "source": source,
                "target": target
            })

    except Exception as e:
        return error_response(str(e))

@app.route("/translate/multi", methods=["POST"])
@require_api_key
def api_translate_multi():
    """
    Endpoint for translating one text into multiple target languages.
    """
    data = request.get_json()
    if not data:
        return error_response("Invalid JSON", 400)

    source = data.get("source")
    targets = data.get("targets") # Expected list: ["en", "es", "ja"]
    text = data.get("text")

    if not source or not targets:
        return error_response("Missing 'source' or 'targets' field", 400)
    
    if not isinstance(targets, list):
        return error_response("'targets' must be a list of language codes", 400)

    if not text:
        return error_response("Missing 'text' field", 400)

    # Normalize Chinese if source is 'zh'
    if source == 'zh':
        text = cc_to_simplified.convert(text)

    results = {}
    errors = {}

    for target in targets:
        try:
            translated_text = trans(source, target, text)
            results[target] = translated_text
        except Exception as e:
            errors[target] = str(e)
            results[target] = None

    return success_response({
        "source": source,
        "text": text,
        "translations": results,
        "errors": errors if errors else None
    })

@app.route("/detect", methods=["POST"])
@require_api_key
def api_detect():
    """
    Endpoint to detect the language of the input text.
    """
    data = request.get_json()
    text = data.get("text", "")
    if not text:
        return error_response("Missing text", 400)
        
    result = detect_language(text)
    return success_response({
        "language": result['detected_lang'],
        "confidence": 0.99 # Placeholder confidence
    })

@app.route("/languages", methods=["GET"])
@require_api_key
def api_languages():
    """
    Returns a list of installed languages and available (installable) languages.
    """
    # Get installed languages
    installed = []
    for lang in installed_languages:
        installed.append({
            "code": lang.code,
            "name": lang.name,
            "translations_to": [t.to_lang.code for t in lang.translations_to]
        })
    
    # Get available packages (not installed)
    try:
        available_packages = package.get_available_packages()
        available = []
        seen_codes = set()
        for pkg in available_packages:
            if pkg.from_code not in seen_codes:
                available.append({"code": pkg.from_code, "name": pkg.from_name})
                seen_codes.add(pkg.from_code)
            if pkg.to_code not in seen_codes:
                available.append({"code": pkg.to_code, "name": pkg.to_name})
                seen_codes.add(pkg.to_code)
                
    except Exception as e:
        available = []
        print(f"Error fetching available packages: {e}")

    return success_response({
        "installed": installed,
        "available": available
    })

@app.route("/models", methods=["GET"])
@require_api_key
def api_models():
    """
    Returns a list of all installed translation models (pairs).
    """
    models_list = []
    for lang in installed_languages:
        for t in lang.translations_to:
             models_list.append({
                 "from_code": lang.code,
                 "from_name": lang.name,
                 "to_code": t.to_lang.code,
                 "to_name": t.to_lang.name
             })
    return success_response({"models": models_list})

@app.route("/models/install-all", methods=["GET"])
@require_api_key
def api_install_all_models():
    """
    Triggers an asynchronous background job to install ALL available models.
    Returns the list of models queued for installation.
    """
    packages_to_install = get_models_to_install()
    if not packages_to_install:
        return success_response(data={"packages": []}, msg="All models are already installed.")

    # Run installation in a background thread
    install_thread = threading.Thread(target=_install_packages_async, args=(packages_to_install,))
    install_thread.start()

    return success_response(
        data={"packages": packages_to_install},
        msg=f"Queued {len(packages_to_install)} models for installation."
    )

@app.route("/models/install", methods=["POST"])
@require_api_key
def api_install_model():
    """
    Installs a specific language model pair (e.g., from 'en' to 'es').
    This is a synchronous operation (blocks until download completes).
    """
    data = request.get_json()
    from_code = data.get("from")
    to_code = data.get("to")
    
    if not from_code or not to_code:
        return error_response("Missing 'from' or 'to' language code", 400)

    try:
        available_packages = package.get_available_packages()
        pkg = next((p for p in available_packages
                    if p.from_code == from_code and p.to_code == to_code), None)
        if pkg:
            downloaded_path = pkg.download()
            package.install_from_path(downloaded_path)
            
            # Reload languages
            translate.load_installed_languages()
            global installed_languages
            installed_languages = translate.get_installed_languages()
            
            return success_response({"status": "installed"})
        else:
            return error_response("Model not found", 404)
    except Exception as e:
        return error_response(str(e))

@app.route("/models", methods=["DELETE"])
@require_api_key
def api_delete_model():
    """
    Placeholder for deleting a model. Not implemented yet.
    """
    return error_response("Delete model not implemented yet", 501)

@app.route("/health", methods=["GET"])
def api_health():
    """
    Health check endpoint.
    """
    return success_response({"status": "ok"})

@app.route("/info", methods=["GET"])
@require_api_key
def api_info():
    """
    Returns service information.
    """
    return success_response({
        "service": "translate-api",
        "version": "1.0",
        "engine": "argos"
    })

@app.route("/translate_zh_en", methods=["POST"])
@require_api_key
def api_translate_zh_en():
    """
    Legacy endpoint for Chinese to English translation.
    Maintained for backward compatibility.
    """
    data = request.get_json()
    input_data = data
    if isinstance(data, dict) and "text" in data:
        input_data = data["text"]

    def translate_text(text):
        if not text: return ""
        normalized_text = cc_to_simplified.convert(str(text))
        try:
            return trans('zh', 'en', normalized_text)
        except:
            return text

    if isinstance(input_data, list):
        results = [translate_text(t) for t in input_data]
        return success_response(results)
    else:
        result = translate_text(input_data)
        return success_response(result)

# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
