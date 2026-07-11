import io
import json
import os
import random
import sqlite3
import hashlib
import secrets
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import urllib.request
import webbrowser
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, simpledialog, filedialog
from time import strftime

# ── Optional dependencies ─────────────────────────────────────────────────────
# Each wrapped individually so one missing package never crashes the whole app.

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

try:
    from PIL import Image as PIL_Image, ImageTk as PIL_ImageTk, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    PIL_Image = None
    PIL_ImageTk = None
    HAS_PIL = False

try:
    import pyttsx3
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

try:
    from deep_translator import GoogleTranslator
    HAS_TRANSLATOR = True
except ImportError:
    HAS_TRANSLATOR = False

try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

try:
    from tkinterweb import HtmlFrame
    HAS_TKWEB = True
except ImportError:
    HAS_TKWEB = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False

try:
    from huggingface_hub import InferenceClient
    HAS_HF = True
except ImportError:
    HAS_HF = False
    InferenceClient = None  # type: ignore

try:
    from tkintermapview import TkinterMapView
except ImportError:
    TkinterMapView = None  # type: ignore

# ── VLC: locate install, patch PATH, then import ──────────────────────────────

if sys.platform.startswith("win"):
    _vlc_candidates = [
        r"C:\Program Files\VideoLAN\VLC",
        r"C:\Program Files (x86)\VideoLAN\VLC",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "VideoLAN", "VLC"),
        os.path.join(os.environ.get("PROGRAMFILES",  r"C:\Program Files"), "VideoLAN", "VLC"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"), "VideoLAN", "VLC"),
        # Bundled next to the EXE (PyInstaller standalone build)
        os.path.join(os.path.dirname(sys.executable), "vlc"),
        os.path.dirname(sys.executable),
    ]
    for _vlc_dir in _vlc_candidates:
        if _vlc_dir and os.path.isfile(os.path.join(_vlc_dir, "libvlc.dll")):
            os.environ["PATH"] = _vlc_dir + os.pathsep + os.environ.get("PATH", "")
            os.environ.setdefault("VLC_PLUGIN_PATH", os.path.join(_vlc_dir, "plugins"))
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(_vlc_dir)
                except Exception:
                    pass
            break

_vlc_error = ""

try:
    import vlc
    HAS_VLC = True
except (ImportError, FileNotFoundError, OSError, Exception) as _e:
    HAS_VLC = False
    _vlc_error = str(_e)

def _vlc_make_instance():
    """Create a VLC instance with safe fallback args."""
    args = ["--quiet"]
    if sys.platform.startswith("linux"):
        args.append("--no-xlib")
    try:
        return vlc.Instance(*args)
    except Exception:
        return vlc.Instance()

# ── pygame init ────────────────────────────────────────────────────────────────

if HAS_PYGAME:
    try:
        pygame.mixer.init()
    except Exception:
        pass


# ---------- Theme colors ----------
DARK_THEME = {
    "bg":        "#0F0F17",
    "panel":     "#1A1A2E",
    "panel2":    "#16213E",
    "input":     "#0D0D1A",
    "text":      "#E8E8F0",
    "subtext":   "#7A7A9A",
    "accent":    "#7C5CFC",
    "accent2":   "#5C8DFC",
    "on_accent": "#FFFFFF",
    "highlight": "#252540",
    "success":   "#4CAF7D",
    "warning":   "#F0A500",
    "danger":    "#FF5370",
    "card1":     "#1E1E3A",
    "card2":     "#1A2840",
    "card3":     "#2A1A3A",
    "card4":     "#1A2A25",
    "border":    "#2A2A45",
}

LIGHT_THEME = {
    "bg":        "#F0F2F8",
    "panel":     "#FFFFFF",
    "panel2":    "#F8F9FF",
    "input":     "#F0F2F8",
    "text":      "#1A1A2E",
    "subtext":   "#6B6B8A",
    "accent":    "#6C47FF",
    "accent2":   "#3B7FFF",
    "on_accent": "#FFFFFF",
    "highlight": "#E8ECFF",
    "success":   "#2E9E5B",
    "warning":   "#E08C00",
    "danger":    "#E53050",
    "card1":     "#EEF0FF",
    "card2":     "#E8F0FF",
    "card3":     "#F0E8FF",
    "card4":     "#E8F5EE",
    "border":    "#DDE0F0",
}

THEMES = {"dark": DARK_THEME, "light": LIGHT_THEME}

# ---------- Languages ----------
LANGUAGES = {
    "English": "en", "Spanish": "es", "French": "fr", "German": "de",
    "Italian": "it", "Portuguese": "pt", "Russian": "ru", "Japanese": "ja",
    "Korean": "ko", "Chinese (Simplified)": "zh-CN", "Hindi": "hi",
    "Arabic": "ar", "Dutch": "nl", "Turkish": "tr", "Polish": "pl",
}

# ---------- Settings ----------
settings = {
    "theme": "dark",
    "language": "English",
    "text_scale": 1.0,
    "tts": False,
    "last_result": "",
    "current_user": None,
}


# ============================================================
# AI CHATBOT  (Hugging Face Inference Providers)
# ============================================================
_HF_API_KEY   = "hf-YOURAPI(i removed mine cuz lol it was a free model and i dont wnna use all mines up)"
_HF_MODEL     = "openai/gpt-oss-120b"

if HAS_HF:
    try:
        _hf_client = InferenceClient(provider="groq", api_key=_HF_API_KEY)
    except Exception:
        _hf_client = None
else:
    _hf_client = None

SYSTEM_PROMPT = (
    "You are a helpful, friendly AI assistant inside a desktop app. "
    "Answer clearly and concisely. Use plain text (no markdown headings)."
)


def get_ai_response(history):
    if not HAS_HF or _hf_client is None:
        return "AI is not available.\n\nTo enable it:\n  pip install huggingface-hub"
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history:
        role = turn.get("role")
        text = (turn.get("content") or "").strip()
        if role in ("user", "assistant") and text:
            messages.append({"role": role, "content": text})
    try:
        completion = _hf_client.chat.completions.create(
            model=_HF_MODEL,
            messages=messages,
            max_tokens=600,
            temperature=0.7,
        )
        reply = (completion.choices[0].message.content or "").strip()
        return reply or "(no response)"
    except Exception as e:
        return f"Error talking to the model: {e}"


APP_NAME = "MultiPurposeApp"


def app_data_folder():
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share"
        )
    folder = os.path.join(base, APP_NAME)
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        folder = tempfile.gettempdir()
    return folder


def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def get_db_path():
    return os.path.join(app_data_folder(), "users.db")


PBKDF2_ITERATIONS = 200_000
SALT_BYTES = 16


def db_connect():
    return sqlite3.connect(get_db_path())


def db_init():
    conn = db_connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                salt          TEXT NOT NULL,
                created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT NOT NULL COLLATE NOCASE,
                title      TEXT NOT NULL DEFAULT 'Untitled',
                content    TEXT NOT NULL DEFAULT '',
                color      TEXT NOT NULL DEFAULT '#7C5CFC',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT NOT NULL COLLATE NOCASE,
                title      TEXT NOT NULL,
                priority   TEXT NOT NULL DEFAULT 'Normal',
                done       INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def hash_password(password, salt_bytes):
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        PBKDF2_ITERATIONS,
    )
    return derived.hex()


def create_user(username, password):
    username = (username or "").strip()
    password = password or ""
    if not username:
        return False, "Username is required."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(username) > 32:
        return False, "Username must be 32 characters or less."
    if not all(c.isalnum() or c in "._-" for c in username):
        return False, "Username can only contain letters, numbers, '.', '_' or '-'."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    salt = secrets.token_bytes(SALT_BYTES)
    pw_hash = hash_password(password, salt)
    conn = db_connect()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, pw_hash, salt.hex()),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return False, "That username is already taken."
    except sqlite3.Error as error:
        return False, f"Database error: {error}"
    finally:
        conn.close()
    return True, None


def authenticate_user(username, password):
    username = (username or "").strip()
    password = password or ""
    if not username or not password:
        return False, "Please enter both a username and password."
    conn = db_connect()
    try:
        row = conn.execute(
            "SELECT username, password_hash, salt FROM users WHERE username = ? COLLATE NOCASE",
            (username,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return False, "Invalid username or password."
    real_username, stored_hash, salt_hex = row
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False, "Stored credentials are corrupted for this account."
    candidate_hash = hash_password(password, salt)
    if not secrets.compare_digest(candidate_hash, stored_hash):
        return False, "Invalid username or password."
    return True, real_username


# ---------- Notes DB ----------
def notes_get_all(username):
    conn = db_connect()
    try:
        rows = conn.execute(
            "SELECT id, title, content, color, created_at, updated_at FROM notes WHERE username=? ORDER BY updated_at DESC",
            (username,),
        ).fetchall()
        return [
            {"id": r[0], "title": r[1], "content": r[2],
             "color": r[3], "created_at": r[4], "updated_at": r[5]}
            for r in rows
        ]
    finally:
        conn.close()


def notes_create(username, title, content, color="#7C5CFC"):
    conn = db_connect()
    try:
        conn.execute(
            "INSERT INTO notes (username, title, content, color) VALUES (?, ?, ?, ?)",
            (username, title, content, color),
        )
        conn.commit()
    finally:
        conn.close()


def notes_update(note_id, title, content, color):
    conn = db_connect()
    try:
        conn.execute(
            "UPDATE notes SET title=?, content=?, color=?, updated_at=datetime('now') WHERE id=?",
            (title, content, color, note_id),
        )
        conn.commit()
    finally:
        conn.close()


def notes_delete(note_id):
    conn = db_connect()
    try:
        conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
        conn.commit()
    finally:
        conn.close()


# ---------- Todo DB ----------
def todos_get_all(username):
    conn = db_connect()
    try:
        rows = conn.execute(
            "SELECT id, title, priority, done, created_at FROM todos WHERE username=? ORDER BY done ASC, created_at DESC",
            (username,),
        ).fetchall()
        return [{"id": r[0], "title": r[1], "priority": r[2], "done": r[3], "created_at": r[4]} for r in rows]
    finally:
        conn.close()


def todos_create(username, title, priority="Normal"):
    conn = db_connect()
    try:
        conn.execute("INSERT INTO todos (username, title, priority) VALUES (?, ?, ?)", (username, title, priority))
        conn.commit()
    finally:
        conn.close()


def todos_toggle(todo_id, done):
    conn = db_connect()
    try:
        conn.execute("UPDATE todos SET done=? WHERE id=?", (done, todo_id))
        conn.commit()
    finally:
        conn.close()


def todos_delete(todo_id):
    conn = db_connect()
    try:
        conn.execute("DELETE FROM todos WHERE id=?", (todo_id,))
        conn.commit()
    finally:
        conn.close()


# ---------- RSS News fetch ----------
def fetch_rss(url):
    import xml.etree.ElementTree as ET
    import re
    data = _http_get_bytes(url)
    root_el = ET.fromstring(data)
    articles = []
    items = root_el.findall(".//item")
    if not items:
        items = root_el.findall(".//{http://www.w3.org/2005/Atom}entry")
    for item in items[:20]:
        def get_text(el, tag, default=""):
            child = el.find(tag)
            return (child.text or "").strip() if child is not None else default
        title = get_text(item, "title") or get_text(item, "{http://www.w3.org/2005/Atom}title")
        link  = get_text(item, "link")  or get_text(item, "{http://www.w3.org/2005/Atom}link")
        desc  = get_text(item, "description") or get_text(item, "{http://www.w3.org/2005/Atom}summary")
        date  = get_text(item, "pubDate") or get_text(item, "{http://www.w3.org/2005/Atom}published")
        desc  = re.sub(r"<[^>]+>", "", desc)[:200]
        if title:
            articles.append({"title": title, "link": link, "desc": desc, "date": date})
    return articles


# ---------- Currency fetch (Frankfurter - free, no key) ----------
def fetch_currency_rate(from_c, to_c):
    url = f"https://api.frankfurter.app/latest?from={from_c}&to={to_c}"
    data = _http_get(url)
    return data["rates"][to_c]


# ---------- Open file with system default app ----------
def open_with_system(path):
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


# ---------- Translation cache ----------
def cache_path():
    return os.path.join(app_data_folder(), "translations.json")


translations = {}
seen_texts = set()


def load_translation_cache():
    global translations
    if translations:
        return
    if os.path.isfile(cache_path()):
        try:
            with open(cache_path(), "r", encoding="utf-8") as f:
                translations = json.load(f)
        except Exception:
            translations = {}


def save_translation_cache():
    try:
        with open(cache_path(), "w", encoding="utf-8") as f:
            json.dump(translations, f, ensure_ascii=False)
    except Exception:
        pass


def translate(text):
    load_translation_cache()
    if not text:
        return text
    seen_texts.add(text)
    language = settings["language"]
    if language == "English":
        return text
    bucket = translations.setdefault(language, {})
    if text in bucket:
        return bucket[text]
    if not HAS_TRANSLATOR:
        return text
    try:
        translator = GoogleTranslator(source="en", target=LANGUAGES[language])
        bucket[text] = translator.translate(text) or text
        save_translation_cache()
        return bucket[text]
    except Exception:
        return text


def preload_language(language):
    if language == "English" or not HAS_TRANSLATOR:
        return
    bucket = translations.setdefault(language, {})
    missing = [t for t in seen_texts if t and t not in bucket]
    if not missing:
        return
    try:
        translator = GoogleTranslator(source="en", target=LANGUAGES[language])
        for text in missing:
            try:
                bucket[text] = translator.translate(text) or text
            except Exception:
                bucket[text] = text
        save_translation_cache()
    except Exception:
        pass


# ---------- Helpers ----------
def color(name):
    return THEMES[settings["theme"]][name]


def font(size=11, bold=False):
    real_size = max(8, int(size * settings["text_scale"]))
    weight = "bold" if bold else "normal"
    return ("Segoe UI", real_size, weight)


def format_time(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _safe_label_image(label, photo):
    """Set image on a label, ignoring errors if widget was destroyed."""
    try:
        label.config(image=photo, text="")
        label.image = photo
    except tk.TclError:
        pass


# ---------- Search sources ----------

UA = "MultiPurposeApp/1.0"

def _http_get(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def _http_get_bytes(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def wiki_search(query):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrlimit": "8", "prop": "extracts",
        "exintro": "1", "explaintext": "1", "exsentences": "3",
    }
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    data = _http_get(url)
    pages = (data.get("query") or {}).get("pages", {})
    results = []
    for page in pages.values():
        title = page.get("title", "")
        summary = (page.get("extract") or "").strip()
        link = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
        results.append({"source": "Wikipedia", "title": title, "summary": summary, "link": link})
    return results


def duckduckgo_search(query):
    """DuckDuckGo Instant Answer API — free, no key."""
    params = {"q": query, "format": "json", "no_redirect": "1", "no_html": "1"}
    url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(params)
    data = _http_get(url)
    results = []

    # Abstract (main result)
    abstract = (data.get("AbstractText") or "").strip()
    abstract_url = data.get("AbstractURL") or ""
    abstract_source = data.get("AbstractSource") or "DuckDuckGo"
    heading = data.get("Heading") or query
    if abstract:
        results.append({
            "source": f"DuckDuckGo ({abstract_source})",
            "title": heading,
            "summary": abstract,
            "link": abstract_url,
        })

    # Related topics
    for topic in (data.get("RelatedTopics") or [])[:6]:
        if not isinstance(topic, dict):
            continue
        text = (topic.get("Text") or "").strip()
        link = topic.get("FirstURL") or ""
        if text and link:
            title = text.split(" - ")[0][:80]
            summary = text[:200]
            results.append({
                "source": "DuckDuckGo",
                "title": title,
                "summary": summary,
                "link": link,
            })
    return results


def openlibrary_search(query):
    """Open Library book search — free, no key. Returns books with cover image URLs."""
    params = {"q": query, "limit": "8", "fields": "key,title,author_name,first_sentence,cover_i,subject"}
    url = "https://openlibrary.org/search.json?" + urllib.parse.urlencode(params)
    data = _http_get(url)
    results = []
    for doc in (data.get("docs") or []):
        title = doc.get("title") or ""
        authors = ", ".join(doc.get("author_name") or [])
        subjects = ", ".join((doc.get("subject") or [])[:3])
        first_sentence = ""
        fs = doc.get("first_sentence")
        if isinstance(fs, dict):
            first_sentence = fs.get("value") or ""
        elif isinstance(fs, str):
            first_sentence = fs
        summary = first_sentence or subjects
        cover_id = doc.get("cover_i")
        cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None
        link = "https://openlibrary.org" + (doc.get("key") or "")
        results.append({
            "source": "Open Library",
            "title": title,
            "summary": (f"by {authors}  •  {summary}" if authors else summary),
            "link": link,
            "image_url": cover_url,
        })
    return results


def reddit_search(query):
    """Reddit search — public JSON API, no key."""
    params = {"q": query, "limit": "8", "sort": "relevance", "type": "link"}
    url = "https://www.reddit.com/search.json?" + urllib.parse.urlencode(params)
    data = _http_get(url)
    results = []
    for child in (data.get("data", {}).get("children") or []):
        post = child.get("data") or {}
        title = (post.get("title") or "").strip()
        subreddit = post.get("subreddit_name_prefixed") or ""
        score = post.get("score") or 0
        num_comments = post.get("num_comments") or 0
        selftext = (post.get("selftext") or "")[:200].strip()
        permalink = "https://reddit.com" + (post.get("permalink") or "")
        summary = selftext or f"{subreddit}  •  ↑{score} points  •  {num_comments} comments"
        results.append({
            "source": "Reddit",
            "title": title,
            "summary": summary,
            "link": permalink,
            "meta": f"{subreddit}  •  ↑{score}  •  {num_comments} comments",
        })
    return results


def wikimedia_image_search(query):
    """Wikimedia Commons image search — free, no key. Returns image thumb URLs."""
    params = {
        "action": "query", "format": "json",
        "generator": "search", "gsrsearch": query,
        "gsrnamespace": "6",  # File namespace
        "gsrlimit": "20",
        "prop": "imageinfo",
        "iiprop": "url|thumburl|extmetadata",
        "iiurlwidth": "240",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    data = _http_get(url)
    pages = (data.get("query") or {}).get("pages") or {}
    images = []
    for page in pages.values():
        title = page.get("title", "").replace("File:", "")
        ii = (page.get("imageinfo") or [{}])[0]
        thumb_url = ii.get("thumburl") or ii.get("url") or ""
        full_url = ii.get("url") or ""
        if not thumb_url:
            continue
        # Get description from extmetadata
        meta = ii.get("extmetadata") or {}
        desc = ""
        for field in ("ImageDescription", "ObjectName", "Categories"):
            val = (meta.get(field) or {}).get("value") or ""
            if val:
                # Strip basic HTML tags
                import re
                desc = re.sub(r"<[^>]+>", "", val)[:120]
                break
        images.append({
            "title": title[:60],
            "thumb_url": thumb_url,
            "full_url": full_url,
            "desc": desc,
        })
    return images


def multi_search(query, sources):
    """Run all selected sources in parallel threads. Returns dict keyed by source."""
    results = {}
    errors = {}
    lock = threading.Lock()

    def run(name, fn):
        try:
            data = fn(query)
            with lock:
                results[name] = data
        except Exception as e:
            with lock:
                errors[name] = str(e)

    threads = []
    source_map = {
        "Wikipedia": wiki_search,
        "DuckDuckGo": duckduckgo_search,
        "Books": openlibrary_search,
        "Reddit": reddit_search,
        "Images": wikimedia_image_search,
    }
    for src in sources:
        if src in source_map:
            t = threading.Thread(target=run, args=(src, source_map[src]), daemon=True)
            t.start()
            threads.append(t)
    for t in threads:
        t.join(timeout=15)

    return results, errors


# ---------- Weather fetch (wttr.in - no API key needed) ----------
def fetch_weather(city):
    """Returns a dict with weather info or raises an exception."""
    encoded = urllib.parse.quote(city)
    url = f"https://wttr.in/{encoded}?format=j1"
    req = urllib.request.Request(url, headers={"User-Agent": "MultiPurposeApp/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    current = data["current_condition"][0]
    area = data["nearest_area"][0]
    area_name = area["areaName"][0]["value"]
    country = area["country"][0]["value"]
    temp_c = int(current["temp_C"])
    temp_f = int(current["temp_F"])
    feels_c = int(current["FeelsLikeC"])
    desc = current["weatherDesc"][0]["value"]
    humidity = current["humidity"]
    wind_kmph = current["windspeedKmph"]
    return {
        "city": f"{area_name}, {country}",
        "temp_c": temp_c,
        "temp_f": temp_f,
        "feels_c": feels_c,
        "desc": desc,
        "humidity": humidity,
        "wind": wind_kmph,
    }


# ---------- Text to speech ----------
tts_engine = None


def speak(text):
    if not (settings["tts"] and HAS_TTS and text):
        return

    def run():
        global tts_engine
        try:
            if tts_engine is None:
                tts_engine = pyttsx3.init()
            tts_engine.stop()
            tts_engine.say(text)
            tts_engine.runAndWait()
        except Exception:
            tts_engine = None

    threading.Thread(target=run, daemon=True).start()


# ---------- Toolbar actions ----------
def action_open_google():
    if HAS_WEBVIEW:
        try:
            webview.create_window("Google", "https://www.google.com")
            webview.start()
            return
        except Exception:
            pass
    webbrowser.open("https://www.google.com")


def action_feedback():
    working = messagebox.askyesno(translate("Feedback"), translate("Is the app working?"))
    if working:
        message = simpledialog.askstring(translate("Feedback"), translate("Rate us:"))
    else:
        message = simpledialog.askstring(translate("Feedback"), translate("Describe the issue:"))
    if message:
        messagebox.showinfo(translate("Thanks"), translate("Sent") + ": " + message)


# ---------- Reusable widgets ----------
def make_button(parent, text, command, primary=False, width=None, danger=False, small=False):
    if danger:
        bg, fg = color("danger"), "#FFFFFF"
    elif primary:
        bg, fg = color("accent"), color("on_accent")
    else:
        bg, fg = color("highlight"), color("text")

    pad_x = 12 if small else 18
    pad_y = 5 if small else 8
    sz = 10 if small else 11

    options = dict(
        text=translate(text), command=command, bg=bg, fg=fg,
        activebackground=bg, activeforeground=fg,
        relief="flat", bd=0, padx=pad_x, pady=pad_y,
        cursor="hand2", font=font(sz, bold=primary),
    )
    if width is not None:
        options["width"] = width
    return tk.Button(parent, **options)


def make_label(parent, text, size=11, bold=False, subtle=False, on_panel=False, color_name=None):
    if color_name:
        bg = color_name
    else:
        bg = color("panel") if on_panel else color("bg")
    fg = color("subtext") if subtle else color("text")
    return tk.Label(parent, text=translate(text), bg=bg, fg=fg, font=font(size, bold))


def make_card(parent, bg_key="panel", padx=16, pady=14, relief="flat", bd=1):
    """A styled card frame."""
    f = tk.Frame(parent, bg=color(bg_key), relief=relief, bd=bd,
                 highlightthickness=1, highlightbackground=color("border"))
    return f


def make_entry(parent, textvariable=None, show=None, width=None):
    opts = dict(
        bg=color("input"), fg=color("text"),
        insertbackground=color("text"),
        relief="flat",
        font=font(12),
        highlightthickness=1,
        highlightbackground=color("border"),
        highlightcolor=color("accent"),
    )
    if textvariable is not None:
        opts["textvariable"] = textvariable
    if show is not None:
        opts["show"] = show
    if width is not None:
        opts["width"] = width
    return tk.Entry(parent, **opts)


def make_separator(parent, orient="horizontal"):
    f = tk.Frame(parent, bg=color("border"), height=1 if orient == "horizontal" else 0,
                 width=0 if orient == "horizontal" else 1)
    return f


# ============================================================
# TOAST NOTIFICATIONS
# ============================================================
class Toast:
    """A small non-blocking notification that fades after a few seconds."""
    _toasts = []

    @staticmethod
    def show(root, message, kind="info", duration=3000):
        bg = {
            "info": color("accent"),
            "success": color("success"),
            "error": color("danger"),
            "warning": color("warning"),
        }.get(kind, color("accent"))

        win = tk.Toplevel(root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=bg)

        # Position bottom-right
        root.update_idletasks()
        rw, rh = root.winfo_width(), root.winfo_height()
        rx, ry = root.winfo_rootx(), root.winfo_rooty()

        # Stack multiple toasts
        offset = len(Toast._toasts) * 60
        win.geometry(f"+{rx + rw - 320}+{ry + rh - 80 - offset}")

        tk.Label(
            win, text=message, bg=bg, fg="#FFFFFF",
            font=font(11), padx=20, pady=12, wraplength=280,
        ).pack()

        Toast._toasts.append(win)

        def destroy():
            try:
                win.destroy()
                if win in Toast._toasts:
                    Toast._toasts.remove(win)
            except Exception:
                pass

        root.after(duration, destroy)



# LOGIN / SIGN-UP WINDOW

class AuthWindow:
    def __init__(self, on_success):
        self.on_success = on_success
        self.mode = "login"

        self.root = tk.Tk()
        self.root.title("Sign in — MultiPurpose App")
        self.root.geometry("420x540")
        self.root.minsize(380, 480)
        self.root.configure(bg=color("bg"))
        self.root.resizable(False, False)

        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w // 2) - 210
        y = (screen_h // 2) - 270
        self.root.geometry(f"420x540+{x}+{y}")

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.confirm_var = tk.StringVar()

        self.body = None
        self.title_label = None
        self.confirm_row = None
        self.submit_button = None
        self.toggle_button = None
        self.status_label = None

        self._build()
        self.root.bind("<Return>", lambda _e: self._submit())

    def _build(self):
        # Left accent bar
        accent_bar = tk.Frame(self.root, bg=color("accent"), width=4)
        accent_bar.pack(side="left", fill="y")

        outer = tk.Frame(self.root, bg=color("bg"))
        outer.pack(fill="both", expand=True, padx=36, pady=32)

        # App name badge
        badge = tk.Label(
            outer, text="MultiPurpose App", bg=color("highlight"),
            fg=color("accent"), font=font(9, bold=True), padx=10, pady=4,
        )
        badge.pack(anchor="w", pady=(0, 16))

        self.title_label = tk.Label(
            outer, text="Welcome back", bg=color("bg"), fg=color("text"),
            font=font(22, bold=True),
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = tk.Label(
            outer, text="Log in to continue.",
            bg=color("bg"), fg=color("subtext"), font=font(11),
        )
        self.subtitle_label.pack(anchor="w", pady=(2, 22))

        # Username
        tk.Label(outer, text="USERNAME", bg=color("bg"), fg=color("subtext"),
                 font=font(9, bold=True)).pack(anchor="w")
        username_entry = make_entry(outer, textvariable=self.username_var)
        username_entry.pack(fill="x", ipady=10, pady=(4, 14))
        username_entry.focus_set()

        # Password
        tk.Label(outer, text="PASSWORD", bg=color("bg"), fg=color("subtext"),
                 font=font(9, bold=True)).pack(anchor="w")
        make_entry(outer, textvariable=self.password_var, show="•").pack(
            fill="x", ipady=10, pady=(4, 14))

        # Confirm password
        self.confirm_row = tk.Frame(outer, bg=color("bg"))
        tk.Label(self.confirm_row, text="CONFIRM PASSWORD", bg=color("bg"),
                 fg=color("subtext"), font=font(9, bold=True)).pack(anchor="w")
        make_entry(self.confirm_row, textvariable=self.confirm_var, show="•").pack(
            fill="x", ipady=10, pady=(4, 14))

        # Status
        self.status_label = tk.Label(
            outer, text="", bg=color("bg"),
            fg=color("danger"), font=font(10), wraplength=340, justify="left",
        )
        self.status_label.pack(anchor="w", pady=(0, 6))

        # Submit
        self.submit_button = tk.Button(
            outer, text="Log in", command=self._submit,
            bg=color("accent"), fg=color("on_accent"),
            activebackground=color("accent"), activeforeground=color("on_accent"),
            relief="flat", bd=0, padx=18, pady=12,
            cursor="hand2", font=font(12, bold=True),
        )
        self.submit_button.pack(fill="x", pady=(4, 12))

        # Switch mode
        self.toggle_button = tk.Button(
            outer, text="Need an account? Sign up", command=self._toggle_mode,
            bg=color("bg"), fg=color("accent"),
            activebackground=color("bg"), activeforeground=color("accent"),
            relief="flat", bd=0, cursor="hand2", font=font(10, bold=True),
        )
        self.toggle_button.pack()

        self._apply_mode()

    def _apply_mode(self):
        if self.mode == "login":
            self.title_label.config(text="Welcome back")
            self.subtitle_label.config(text="Log in to continue.")
            self.submit_button.config(text="Log in")
            self.toggle_button.config(text="Need an account? Sign up")
            self.confirm_row.pack_forget()
        else:
            self.title_label.config(text="Create account")
            self.subtitle_label.config(text="It only takes a few seconds.")
            self.submit_button.config(text="Sign up")
            self.toggle_button.config(text="Already have an account? Log in")
            self.confirm_row.pack(fill="x", before=self.status_label)
        self.status_label.config(text="")

    def _toggle_mode(self):
        self.mode = "signup" if self.mode == "login" else "login"
        self.confirm_var.set("")
        self._apply_mode()

    def _show_error(self, message):
        self.status_label.config(text=message, fg=color("danger"))

    def _submit(self):
        username = self.username_var.get()
        password = self.password_var.get()
        if self.mode == "signup":
            if password != self.confirm_var.get():
                self._show_error("Passwords don't match.")
                return
            ok, error = create_user(username, password)
            if not ok:
                self._show_error(error)
                return
            ok, result = authenticate_user(username, password)
            if not ok:
                self._show_error(result)
                return
            self._finish(result)
        else:
            ok, result = authenticate_user(username, password)
            if not ok:
                self._show_error(result)
                return
            self._finish(result)

    def _finish(self, username):
        settings["current_user"] = username
        try:
            self.root.destroy()
        except Exception:
            pass
        self.on_success(username)

    def run(self):
        self.root.mainloop()



# MAIN APP

class MultiPurposeApp:
    def __init__(self, root):
        self.root = root
        self.pages = {}
        self.current_page = "home"

        # AI chat state
        self.chat_history = []
        self._typing_anim_running = False

        # Map state
        self.map_widget = None
        self.map_markers = []
        self.map_search_var = None
        self.map_status_var = None
        self.map_coord_var = None
        self._map_default_pos = (27.9944, -81.7603)
        self._map_default_zoom = 6
        self._map_tile_servers = {
            "Map":       "https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}",
            "Satellite": "https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}",
            "Hybrid":    "https://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}",
            "Terrain":   "https://mt0.google.com/vt/lyrs=p&hl=en&x={x}&y={y}&z={z}",
            "Dark":      "https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png",
            "OSM":       "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
        }
        self._map_zoom = self._map_default_zoom
        self._map_style_buttons = {}
        self._map_current_style = "Map"

        # Search / wiki
        self.search_entry = None
        self.results_text = None

        # Settings
        self.theme_choice = None
        self.language_choice = None
        self.scale_value = None
        self.tts_value = None

        # MP3 player state
        self.playlist = []
        self.current_index = -1
        self.song_length = 0
        self.seek_offset = 0
        self.is_paused = False
        self.is_playing = False
        self.shuffle = False
        self.repeat = False
        self.volume = 0.7
        self.user_seeking = False
        self.default_cover = None

        # MP3 widgets
        self.listbox = None
        self.cover_label = None
        self.song_label = None
        self.artist_label = None
        self.time_label = None
        self.seek_var = None
        self.seek_scale = None
        self.volume_var = None
        self.play_button = None
        self.shuffle_button = None
        self.repeat_button = None

        # Notes state
        self._notes_data = []
        self._selected_note_id = None
        self._notes_title_var = None
        self._notes_color_var = None
        self._notes_list_frame = None
        self._notes_editor_title = None
        self._notes_editor = None

        # Calculator state
        self._calc_expression = ""
        self._calc_display_var = None

        # Weather state
        self._weather_city_var = None
        self._weather_result_frame = None

        # Sidebar nav buttons
        self._nav_buttons = {}

        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        if HAS_PYGAME:
            try:
                pygame.mixer.music.set_volume(self.volume)
            except Exception:
                pass

        self.build_window()
        self.tick_player()

  
    # TOP-LEVEL REBUILD
    def build_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        user = settings.get("current_user") or "guest"
        self.root.title(translate("MultiPurpose App") + f"  —  {user}")
        self.root.configure(bg=color("bg"))

        self.style.configure(
            "App.TCombobox",
            fieldbackground=color("input"),
            background=color("input"),
            foreground=color("text"),
            arrowcolor=color("text"),
        )
        self.style.configure(
            "Sidebar.TScrollbar",
            background=color("panel"),
            troughcolor=color("panel"),
        )

        # Outer container: sidebar left + content right
        container = tk.Frame(self.root, bg=color("bg"))
        container.pack(fill="both", expand=True)

        self._build_sidebar(container)

        # Content area
        self.content_area = tk.Frame(container, bg=color("bg"))
        self.content_area.pack(side="left", fill="both", expand=True)

        self.build_pages()
        self.show_page(self.current_page)

    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=color("panel"), width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo / app name
        logo_frame = tk.Frame(sidebar, bg=color("panel"), pady=12)
        logo_frame.pack(fill="x")
        tk.Label(logo_frame, text="✦", bg=color("panel"), fg=color("accent"), font=font(18, bold=True)).pack()
        tk.Label(logo_frame, text="MultiPurpose", bg=color("panel"), fg=color("text"), font=font(10, bold=True)).pack()
        tk.Label(logo_frame, text="App", bg=color("panel"), fg=color("subtext"), font=font(9)).pack()

        make_separator(sidebar).pack(fill="x", padx=12)

        # Scrollable nav area (handles many items without overflow)
        nav_canvas = tk.Canvas(sidebar, bg=color("panel"), highlightthickness=0)
        nav_canvas.pack(fill="both", expand=True, pady=4)
        nav_inner = tk.Frame(nav_canvas, bg=color("panel"))
        nav_canvas.create_window((0, 0), window=nav_inner, anchor="nw")
        nav_inner.bind("<Configure>", lambda e: nav_canvas.configure(scrollregion=nav_canvas.bbox("all")))
        nav_canvas.bind("<MouseWheel>", lambda e: nav_canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        nav_canvas.bind("<Button-4>", lambda e: nav_canvas.yview_scroll(-1, "units"))
        nav_canvas.bind("<Button-5>", lambda e: nav_canvas.yview_scroll(1, "units"))

        all_nav = [
            ("Home",        "⌂",  "home"),
            ("AI Chat",     "◈",  "AI"),
            ("Search",      "⊙",  "database"),
            ("Browser",     "⊕",  "browser"),
            ("News Feed",   "◉",  "news"),
            ("Map",         "◎",  "map"),
            ("MP3 Player",  "♫",  "mp3"),
            ("Video",       "▣",  "video"),
            ("Weather",     "☁",  "weather"),
            ("Calculator",  "⊞",  "calculator"),
            ("Settings",    "⚙",  "settings"),
            ("Contact",     "✉",  "contact"),
        ]

        self._nav_buttons = {}
        for label, icon, page_id in all_nav:
            self._add_nav_button(nav_inner, label, icon, page_id)

        # Spacer (empty frame at the bottom of sidebar, below the canvas)
        tk.Frame(sidebar, bg=color("panel"), height=4).pack(fill="x")

        # User + logout at bottom
        user_frame = tk.Frame(sidebar, bg=color("highlight"), pady=10)
        user_frame.pack(fill="x")
        user = settings.get("current_user") or "guest"
        tk.Label(
            user_frame, text=user, bg=color("highlight"), fg=color("text"),
            font=font(10, bold=True),
        ).pack()
        tk.Label(
            user_frame, text="Signed in", bg=color("highlight"), fg=color("subtext"),
            font=font(9),
        ).pack(pady=(0, 6))
        tk.Button(
            user_frame, text="Log out", command=self._logout,
            bg=color("danger"), fg="#FFFFFF",
            activebackground=color("danger"), activeforeground="#FFFFFF",
            relief="flat", bd=0, padx=12, pady=4,
            cursor="hand2", font=font(9, bold=True),
        ).pack()

    def _add_nav_button(self, parent, label, icon, page_id):
        btn_frame = tk.Frame(parent, bg=color("panel"), cursor="hand2")
        btn_frame.pack(fill="x", padx=8, pady=1)

        def on_click(p=page_id, f=btn_frame):
            self.show_page(p)

        btn_frame.bind("<Button-1>", lambda e, p=page_id: on_click(p))

        icon_lbl = tk.Label(
            btn_frame, text=icon, bg=color("panel"), fg=color("subtext"),
            font=font(13), width=2, padx=8, pady=7,
        )
        icon_lbl.pack(side="left")
        icon_lbl.bind("<Button-1>", lambda e, p=page_id: on_click(p))

        text_lbl = tk.Label(
            btn_frame, text=translate(label), bg=color("panel"), fg=color("text"),
            font=font(10), anchor="w",
        )
        text_lbl.pack(side="left", fill="x", expand=True)
        text_lbl.bind("<Button-1>", lambda e, p=page_id: on_click(p))

        self._nav_buttons[page_id] = (btn_frame, icon_lbl, text_lbl)

    def _highlight_nav(self, active_page):
        for page_id, (btn_frame, icon_lbl, text_lbl) in self._nav_buttons.items():
            if page_id == active_page:
                btn_frame.config(bg=color("highlight"), highlightbackground=color("accent"),
                                 highlightthickness=0)
                icon_lbl.config(bg=color("highlight"), fg=color("accent"))
                text_lbl.config(bg=color("highlight"), fg=color("accent"), font=font(10, bold=True))
                # accent left border via a tiny frame
            else:
                btn_frame.config(bg=color("panel"))
                icon_lbl.config(bg=color("panel"), fg=color("subtext"))
                text_lbl.config(bg=color("panel"), fg=color("text"), font=font(10))

    def _logout(self):
        if not messagebox.askyesno(translate("Log out"),
                                   translate("Are you sure you want to log out?")):
            return
        settings["current_user"] = None
        self.root.destroy()
        AuthWindow(on_success=_start_main_app).run()

  
    def build_pages(self):
        self.pages = {}
        page_names = (
            "home", "database", "contact", "settings", "mp3",
            "map", "AI", "weather", "calculator",
            "browser", "news", "video",
        )
        for name in page_names:
            self.pages[name] = tk.Frame(self.content_area, bg=color("bg"))

        self.build_home(self.pages["home"])
        self.build_database(self.pages["database"])
        self.build_contact(self.pages["contact"])
        self.build_settings(self.pages["settings"])
        self.build_mp3_player(self.pages["mp3"])
        self.build_map(self.pages["map"])
        self.build_AI(self.pages["AI"])
        self.build_weather(self.pages["weather"])
        self.build_calculator(self.pages["calculator"])
        self.build_browser(self.pages["browser"])
        self.build_news(self.pages["news"])
        self.build_video(self.pages["video"])

    def show_page(self, name):
        if name not in self.pages:
            return
        self.current_page = name
        for frame in self.pages.values():
            frame.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        self._highlight_nav(name)


    # HOME PAGE

    def build_home(self, page):
        wrapper = tk.Frame(page, bg=color("bg"))
        wrapper.pack(fill="both", expand=True, padx=28, pady=24)

        # Top bar: greeting left + clock right
        top_row = tk.Frame(wrapper, bg=color("bg"))
        top_row.pack(fill="x", pady=(0, 20))

        user = settings.get("current_user") or "there"
        tk.Label(
            top_row, text=f"Hello, {user}  👋",
            bg=color("bg"), fg=color("text"), font=font(22, bold=True),
        ).pack(side="left")

        # Live clock
        self._home_clock_var = tk.StringVar()
        clock_lbl = tk.Label(
            top_row, textvariable=self._home_clock_var,
            bg=color("accent"), fg=color("on_accent"),
            font=font(13, bold=True), padx=14, pady=6,
        )
        clock_lbl.pack(side="right")

        def _tick_clock():
            self._home_clock_var.set(strftime('%I:%M:%S %p'))
            page.after(1000, _tick_clock)
        _tick_clock()

        subtitle = tk.Label(
            wrapper, text="What would you like to do today?",
            bg=color("bg"), fg=color("subtext"), font=font(12),
        )
        subtitle.pack(anchor="w", pady=(0, 24))

        # Quick action cards grid  (2 rows x 4 cols)
        grid = tk.Frame(wrapper, bg=color("bg"))
        grid.pack(fill="x", pady=(0, 20))

        cards = [
            ("AI Chat",     "◈", "card1", "AI",          "Chat with AI assistant"),
            ("Browser",     "⊕", "card2", "browser",     "Browse the web in-app"),
            ("YouTube",     "▷", "card3", "youtube",     "Watch YouTube in-app"),
            ("News Feed",   "◉", "card4", "news",        "Latest headlines"),
            ("Search",      "⊙", "card1", "database",    "Wiki, Reddit & more"),
            ("Map",         "◎", "card2", "map",          "Explore the map"),
            ("MP3 Player",  "♫", "card3", "mp3",          "Play your music"),
            ("Video",       "▣", "card4", "video",        "Play local videos"),
            ("Notes",       "✎", "card1", "notes",        "Write & save notes"),
            ("To-Do",       "☑", "card2", "todo",         "Track your tasks"),
            ("Weather",     "☁", "card3", "weather",      "Check the weather"),
            ("Pomodoro",    "◷", "card4", "pomodoro",     "Stay focused"),
            ("Calculator",  "⊞", "card1", "calculator",   "Do math"),
            ("Currency",    "◎", "card2", "currency",     "Convert currencies"),
            ("Settings",    "⚙", "card3", "settings",     "Configure the app"),
            ("Contact",     "✉", "card4", "contact",      "Get in touch"),
        ]

        for i, (title, icon, bg_key, page_id, desc) in enumerate(cards):
            row_i, col_i = divmod(i, 4)
            card = tk.Frame(
                grid, bg=color(bg_key),
                cursor="hand2",
                highlightthickness=1, highlightbackground=color("border"),
            )
            card.grid(row=row_i, column=col_i, padx=8, pady=8, sticky="nsew")
            grid.columnconfigure(col_i, weight=1)

            tk.Label(
                card, text=icon, bg=color(bg_key), fg=color("accent"),
                font=font(22), padx=14,
            ).pack(pady=(14, 4))
            tk.Label(
                card, text=title, bg=color(bg_key), fg=color("text"),
                font=font(11, bold=True),
            ).pack()
            tk.Label(
                card, text=desc, bg=color(bg_key), fg=color("subtext"),
                font=font(9),
            ).pack(pady=(0, 12))

            def bind_card(widget, pid=page_id):
                widget.bind("<Button-1>", lambda e: self.show_page(pid))
                for child in widget.winfo_children():
                    child.bind("<Button-1>", lambda e, p=pid: self.show_page(p))

            bind_card(card)

        # Info strip
        info_row = tk.Frame(wrapper, bg=color("panel"),
                            highlightthickness=1, highlightbackground=color("border"))
        info_row.pack(fill="x", pady=(8, 0))

        tk.Label(
            info_row, text="✦  MultiPurpose App v0.1.0  —  Made with ♥",
            bg=color("panel"), fg=color("subtext"), font=font(9),
            padx=16, pady=8,
        ).pack(side="left")

        feedback_btn = make_button(info_row, "Give Feedback", action_feedback, small=True)
        feedback_btn.pack(side="right", padx=10, pady=6)

        google_btn = make_button(info_row, "Open Google", action_open_google, small=True)
        google_btn.pack(side="right", padx=4, pady=6)

        # Scrolling ticker at the bottom
        canvas = tk.Canvas(wrapper, height=30, bg=color("bg"), highlightthickness=0)
        canvas.pack(fill="x", pady=(14, 0))
        text_str = "  ✦  Welcome to MultiPurpose App  —  AI Chat · Browser · YouTube · News · Map · Music · Video · Notes · To-Do · Weather · Calculator · Pomodoro · Currency  ✦  "
        ticker_text = canvas.create_text(
            1600, 15, text=text_str, fill=color("accent"),
            font=font(10), anchor="w",
        )

        def move_ticker():
            canvas.move(ticker_text, -2, 0)
            bbox = canvas.bbox(ticker_text)
            if bbox and bbox[2] < 0:
                canvas.coords(ticker_text, 1600, 15)
            page.after(14, move_ticker)

        move_ticker()


    # MAP PAGE

    def build_map(self, page):
        self.map_markers      = []
        self.map_search_var   = tk.StringVar()
        self.map_status_var   = tk.StringVar(value="Click to drop a pin  |  Right-click for more options")
        self.map_coord_var    = tk.StringVar(value="—")
        self.map_dist_var     = tk.StringVar(value="")
        self._map_style_buttons = {}
        self._map_current_style = "Map"
        self._map_zoom = self._map_default_zoom
        self._map_search_results = []   # list of (display, lat, lon)

        wrapper = tk.Frame(page, bg=color("bg"))
        wrapper.pack(fill="both", expand=True, padx=20, pady=14)

        # ── Header ──────────────────────────────────────────────────────
        header = tk.Frame(wrapper, bg=color("bg"))
        header.pack(fill="x", pady=(0, 8))
        tk.Label(header, text="◎  Map Explorer", bg=color("bg"), fg=color("text"),
                 font=font(20, bold=True)).pack(side="left")

        # Map style buttons
        style_row = tk.Frame(header, bg=color("bg"))
        style_row.pack(side="right")
        for style_name in ("Map", "Satellite", "Hybrid", "Terrain", "Dark", "OSM"):
            btn = make_button(style_row, style_name,
                              lambda s=style_name: self._map_set_style(s), small=True)
            btn.pack(side="left", padx=(3, 0))
            self._map_style_buttons[style_name] = btn

        # ── Search row ───────────────────────────────────────────────
        search_row = tk.Frame(wrapper, bg=color("bg"))
        search_row.pack(fill="x", pady=(0, 4))
        search_entry = make_entry(search_row, textvariable=self.map_search_var)
        search_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        search_entry.bind("<Return>", lambda _e: self._map_search())

        make_button(search_row, "Search", self._map_search, primary=True, small=True).pack(side="left", padx=(0, 4))
        make_button(search_row, "▲ Reset", self._map_reset_view, small=True).pack(side="left", padx=(0, 4))
        make_button(search_row, "✕ Pins", self._map_clear_markers, small=True).pack(side="left", padx=(0, 4))
        make_button(search_row, "📋 Export", self._map_export_pins, small=True).pack(side="left", padx=(0, 4))
        make_button(search_row, "📍 My Location", self._map_my_location, small=True).pack(side="left")

        # ── Search results dropdown ───────────────────────────────────
        self._map_results_frame = tk.Frame(wrapper, bg=color("panel"),
                                           highlightthickness=1, highlightbackground=color("border"))
        # Not packed yet — appears only when results are available

        # ── Zoom controls + Map canvas ─────────────────────────────────
        map_row = tk.Frame(wrapper, bg=color("bg"))
        map_row.pack(fill="both", expand=True)

        # Zoom sidebar
        zoom_col = tk.Frame(map_row, bg=color("panel"), width=42, padx=4, pady=4)
        zoom_col.pack(side="left", fill="y")
        zoom_col.pack_propagate(False)
        for label, cmd in (("➕", self._map_zoom_in), ("➖", self._map_zoom_out)):
            tk.Button(zoom_col, text=label, font=font(14, bold=True),
                      bg=color("highlight"), fg=color("text"),
                      activebackground=color("accent"), activeforeground=color("on_accent"),
                      relief="flat", bd=0, cursor="hand2",
                      command=cmd).pack(fill="x", pady=3)

        map_outer = tk.Frame(map_row, bg=color("border"),
                             highlightthickness=1, highlightbackground=color("border"))
        map_outer.pack(side="left", fill="both", expand=True)

        self.map_widget = TkinterMapView(map_outer, corner_radius=0)
        self.map_widget.pack(fill="both", expand=True, padx=1, pady=1)
        self.map_widget.set_tile_server(self._map_tile_servers[self._map_current_style])
        self.map_widget.set_position(*self._map_default_pos)
        self.map_widget.set_zoom(self._map_zoom)
        self.map_widget.add_left_click_map_command(self._map_on_left_click)

        # Right-click context menu entries
        self.map_widget.add_right_click_menu_command(
            "Copy coordinates",
            lambda coords: self._map_copy_coords(coords[0], coords[1]))
        self.map_widget.add_right_click_menu_command(
            "Open in Google Maps",
            lambda coords: webbrowser.open(
                f"https://maps.google.com/?q={coords[0]},{coords[1]}"))
        self.map_widget.add_right_click_menu_command(
            "Search nearby (restaurants)",
            lambda coords: self._map_search_nearby(coords[0], coords[1], "restaurant"))
        self.map_widget.add_right_click_menu_command(
            "Search nearby (hotels)",
            lambda coords: self._map_search_nearby(coords[0], coords[1], "hotel"))
        self.map_widget.add_right_click_menu_command(
            "Search nearby (gas stations)",
            lambda coords: self._map_search_nearby(coords[0], coords[1], "fuel"))

        self._map_set_style(self._map_current_style, refresh=False)

        # Keyboard zoom shortcuts
        self.map_widget.bind("<plus>",  lambda _e: self._map_zoom_in())
        self.map_widget.bind("<minus>", lambda _e: self._map_zoom_out())
        self.map_widget.bind("<equal>", lambda _e: self._map_zoom_in())
        wrapper.bind_all("<Control-equal>", lambda _e: self._map_zoom_in())
        wrapper.bind_all("<Control-minus>", lambda _e: self._map_zoom_out())

        # ── Footer ──────────────────────────────────────────────────────
        footer = tk.Frame(wrapper, bg=color("bg"))
        footer.pack(fill="x", pady=(6, 0))
        tk.Label(footer, textvariable=self.map_status_var,
                 bg=color("bg"), fg=color("subtext"), font=font(10)).pack(side="left")
        tk.Label(footer, textvariable=self.map_dist_var,
                 bg=color("bg"), fg=color("text"), font=font(10, bold=True)).pack(side="left", padx=(12, 0))
        tk.Label(footer, textvariable=self.map_coord_var,
                 bg=color("bg"), fg=color("accent"), font=font(10, bold=True)).pack(side="right")

    # -------- Map helpers --------

    def _map_set_style(self, style_name, refresh=True):
        if style_name not in self._map_tile_servers:
            return
        self._map_current_style = style_name
        if refresh and self.map_widget is not None:
            try:
                self.map_widget.set_tile_server(self._map_tile_servers[style_name])
            except Exception:
                pass
        for name, btn in self._map_style_buttons.items():
            if name == style_name:
                btn.config(bg=color("accent"), fg=color("on_accent"),
                           activebackground=color("accent"), activeforeground=color("on_accent"))
            else:
                btn.config(bg=color("highlight"), fg=color("text"),
                           activebackground=color("highlight"), activeforeground=color("text"))

    def _map_zoom_in(self):
        if self.map_widget is None:
            return
        self._map_zoom = min(19, self._map_zoom + 1)
        try:
            self.map_widget.set_zoom(self._map_zoom)
        except Exception:
            pass

    def _map_zoom_out(self):
        if self.map_widget is None:
            return
        self._map_zoom = max(1, self._map_zoom - 1)
        try:
            self.map_widget.set_zoom(self._map_zoom)
        except Exception:
            pass

    def _map_on_left_click(self, coords):
        try:
            lat, lon = float(coords[0]), float(coords[1])
        except (TypeError, ValueError, IndexError):
            return
        self._map_add_marker(lat, lon)
        self.map_coord_var.set(f"{lat:.5f}, {lon:.5f}")
        self._map_update_distance()

    def _map_update_distance(self):
        if len(self.map_markers) < 2:
            self.map_dist_var.set("")
            return
        try:
            import math
            lat1, lon1 = self.map_markers[-2].position
            lat2, lon2 = self.map_markers[-1].position
            R = 6371.0
            phi1, phi2 = math.radians(lat1), math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlam = math.radians(lon2 - lon1)
            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
            km = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            mi = km * 0.621371
            self.map_dist_var.set(f"↔ {km:.1f} km / {mi:.1f} mi")
        except Exception:
            self.map_dist_var.set("")

    def _map_add_marker(self, lat, lon, label=None):
        if self.map_widget is None:
            return
        text = label or f"{lat:.4f}, {lon:.4f}"
        try:
            marker = self.map_widget.set_marker(lat, lon, text=text,
                                                command=self._map_on_marker_click)
        except Exception:
            return
        self.map_markers.append(marker)
        count = len(self.map_markers)
        self.map_status_var.set(
            f"{count} pin{'s' if count != 1 else ''}  |  Right-click for options  |  Click pin to delete")

    def _map_on_marker_click(self, marker):
        try:
            lat, lon = marker.position
        except Exception:
            return
        # Ask user: delete or open street view
        top = tk.Toplevel(self.root)
        top.title("Pin options")
        top.geometry("300x160")
        top.configure(bg=color("bg"))
        top.resizable(False, False)
        tk.Label(top, text=f"{lat:.5f}, {lon:.5f}", bg=color("bg"),
                 fg=color("accent"), font=font(11, bold=True)).pack(pady=(16, 4))
        btn_frame = tk.Frame(top, bg=color("bg"))
        btn_frame.pack(pady=8)

        def open_sv():
            webbrowser.open(f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}")
            top.destroy()

        def delete_pin():
            try:
                marker.delete()
                self.map_markers.remove(marker)
            except Exception:
                pass
            self.map_status_var.set(f"{len(self.map_markers)} pin(s) remaining.")
            self._map_update_distance()
            top.destroy()

        def copy_pin():
            self.root.clipboard_clear()
            self.root.clipboard_append(f"{lat:.6f}, {lon:.6f}")
            self.map_status_var.set("Coordinates copied to clipboard.")
            top.destroy()

        make_button(btn_frame, "🗺 Street View", open_sv, primary=True, small=True).pack(side="left", padx=4)
        make_button(btn_frame, "📋 Copy", copy_pin, small=True).pack(side="left", padx=4)
        make_button(btn_frame, "🗑 Delete Pin", delete_pin, small=True).pack(side="left", padx=4)

    def _map_copy_coords(self, lat, lon):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(f"{float(lat):.6f}, {float(lon):.6f}")
            self.map_status_var.set(f"Copied: {float(lat):.6f}, {float(lon):.6f}")
            self.map_coord_var.set(f"{float(lat):.5f}, {float(lon):.5f}")
        except Exception:
            pass

    def _map_clear_markers(self):
        for marker in list(self.map_markers):
            try:
                marker.delete()
            except Exception:
                pass
        self.map_markers.clear()
        self.map_dist_var.set("")
        self.map_status_var.set("All pins cleared.")

    def _map_reset_view(self):
        if self.map_widget is None:
            return
        self.map_widget.set_position(*self._map_default_pos)
        self._map_zoom = self._map_default_zoom
        self.map_widget.set_zoom(self._map_zoom)

    def _map_export_pins(self):
        if not self.map_markers:
            self.map_status_var.set("No pins to export.")
            return
        lines = ["lat,lon,label"]
        for m in self.map_markers:
            try:
                lat, lon = m.position
                label = getattr(m, "text", "")
                lines.append(f"{lat:.6f},{lon:.6f},{label}")
            except Exception:
                pass
        csv_text = "\n".join(lines)
        self.root.clipboard_clear()
        self.root.clipboard_append(csv_text)
        self.map_status_var.set(f"Exported {len(self.map_markers)} pin(s) as CSV — copied to clipboard.")

    def _map_my_location(self):
        self.map_status_var.set("Getting your location…")

        def work():
            try:
                req = urllib.request.Request("http://ip-api.com/json/",
                                             headers={"User-Agent": "MultiPurposeApp/1.0"})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                lat = float(data["lat"])
                lon = float(data["lon"])
                city = data.get("city", "")
                country = data.get("country", "")

                def show():
                    if self.map_widget is None:
                        return
                    self.map_widget.set_position(lat, lon)
                    self._map_zoom = 13
                    self.map_widget.set_zoom(self._map_zoom)
                    label = city or "My Location"
                    self._map_add_marker(lat, lon, label=label)
                    self.map_coord_var.set(f"{lat:.5f}, {lon:.5f}")
                    self.map_status_var.set(f"Showing: {city}, {country} (IP-based)")
                    self._map_update_distance()

                self.root.after(0, show)
            except Exception as e:
                self.root.after(0, lambda: self.map_status_var.set(f"Could not get location: {e}"))

        threading.Thread(target=work, daemon=True).start()

    def _map_search_nearby(self, lat, lon, amenity):
        self.map_status_var.set(f"Searching nearby {amenity}s…")

        def work():
            try:
                query = f"[out:json][timeout:10];node[amenity={amenity}](around:1500,{lat},{lon});out 8;"
                req = urllib.request.Request(
                    "https://overpass-api.de/api/interpreter",
                    data=query.encode("utf-8"),
                    headers={"Content-Type": "application/x-www-form-urlencoded",
                             "User-Agent": "MultiPurposeApp/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                elements = data.get("elements", [])

                def show():
                    if not elements:
                        self.map_status_var.set(f"No {amenity}s found nearby.")
                        return
                    for el in elements[:8]:
                        elat = float(el.get("lat", 0))
                        elon = float(el.get("lon", 0))
                        name = el.get("tags", {}).get("name", amenity.title())
                        self._map_add_marker(elat, elon, label=name)
                    self.map_status_var.set(
                        f"Found {len(elements)} {amenity}(s) nearby. ({min(len(elements),8)} shown)")

                self.root.after(0, show)
            except Exception as e:
                self.root.after(0, lambda: self.map_status_var.set(f"Nearby search failed: {e}"))

        threading.Thread(target=work, daemon=True).start()

    def _map_show_search_results(self, results):
        """Show up to 5 clickable result rows below the search bar."""
        frame = self._map_results_frame
        for w in frame.winfo_children():
            w.destroy()
        if not results:
            frame.pack_forget()
            return
        tk.Label(frame, text="Pick a result:", bg=color("panel"), fg=color("subtext"),
                 font=font(9)).pack(anchor="w", padx=8, pady=(4, 2))
        for display, lat, lon in results[:5]:
            short = display.split(",")[0]

            def go(d=display, la=lat, lo=lon):
                if self.map_widget is None:
                    return
                self.map_widget.set_position(la, lo)
                self._map_zoom = 13
                self.map_widget.set_zoom(self._map_zoom)
                self._map_add_marker(la, lo, label=d.split(",")[0])
                self.map_coord_var.set(f"{la:.5f}, {lo:.5f}")
                self.map_status_var.set(f"Showing: {d}")
                self._map_show_search_results([])   # hide list

            tk.Button(frame, text=short, anchor="w", bg=color("panel"), fg=color("text"),
                      font=font(10), relief="flat", bd=0, cursor="hand2",
                      activebackground=color("highlight"), command=go).pack(
                          fill="x", padx=8, pady=1)
        tk.Button(frame, text="✕ Dismiss", bg=color("panel"), fg=color("subtext"),
                  font=font(9), relief="flat", bd=0, cursor="hand2",
                  command=lambda: self._map_show_search_results([])).pack(anchor="e", padx=8, pady=4)
        frame.pack(fill="x", pady=(0, 4))

    def _map_search(self):
        query = (self.map_search_var.get() or "").strip()
        if not query:
            self.map_status_var.set("Type a place name to search.")
            return
        self.map_status_var.set(f"Searching for '{query}'…")

        def work():
            try:
                params = {"q": query, "format": "json", "limit": "5"}
                url = ("https://nominatim.openstreetmap.org/search?"
                       + urllib.parse.urlencode(params))
                req = urllib.request.Request(url, headers={"User-Agent": "MultiPurposeApp/1.0"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode("utf-8"))
            except Exception as error:
                try:
                    self.root.after(0, lambda m=str(error): self.map_status_var.set(f"Search failed: {m}"))
                except RuntimeError:
                    pass
                return
            if not data:
                try:
                    self.root.after(0, lambda q=query: self.map_status_var.set(f"No results for '{q}'."))
                except RuntimeError:
                    pass
                return
            results = []
            for item in data[:5]:
                try:
                    results.append((item.get("display_name", query),
                                    float(item["lat"]), float(item["lon"])))
                except (KeyError, ValueError):
                    pass
            if not results:
                self.root.after(0, lambda: self.map_status_var.set("Couldn't parse search results."))
                return
            # If only one result jump straight to it; otherwise show picker
            if len(results) == 1:
                display, lat, lon = results[0]

                def show_one():
                    if self.map_widget is None:
                        return
                    self.map_widget.set_position(lat, lon)
                    self._map_zoom = 13
                    self.map_widget.set_zoom(self._map_zoom)
                    self._map_add_marker(lat, lon, label=display.split(",")[0])
                    self.map_coord_var.set(f"{lat:.5f}, {lon:.5f}")
                    self.map_status_var.set(f"Showing: {display}")
                    self._map_update_distance()

                self.root.after(0, show_one)
            else:
                self.root.after(0, lambda r=results: (
                    self.map_status_var.set(f"{len(r)} results — pick one below:"),
                    self._map_show_search_results(r)))

        threading.Thread(target=work, daemon=True).start()


    # AI CHATBOT

    def build_AI(self, page):
        self.chat_history = []
        self._typing_anim_running = False

        wrapper = tk.Frame(page, bg=color("bg"))
        wrapper.pack(fill="both", expand=True, padx=24, pady=20)

        # Header
        header = tk.Frame(wrapper, bg=color("bg"))
        header.pack(fill="x", pady=(0, 12))
        tk.Label(header, text="◈  AI Chatbot", bg=color("bg"), fg=color("text"),
                 font=font(20, bold=True)).pack(side="left")
        make_button(header, "New chat", lambda: clear_chat(), small=True).pack(side="right")

        # Chat area
        chat_outer = tk.Frame(wrapper, bg=color("input"),
                              highlightthickness=1, highlightbackground=color("border"))
        chat_outer.pack(fill="both", expand=True, pady=(0, 12))

        chat_canvas = tk.Canvas(chat_outer, bg=color("input"), highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(chat_outer, orient="vertical", command=chat_canvas.yview)
        chat_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        chat_canvas.pack(side="left", fill="both", expand=True)

        bubble_frame = tk.Frame(chat_canvas, bg=color("input"))
        bubble_window = chat_canvas.create_window((0, 0), window=bubble_frame, anchor="nw")

        def _resize_bubble_frame(event):
            chat_canvas.itemconfigure(bubble_window, width=event.width)

        chat_canvas.bind("<Configure>", _resize_bubble_frame)

        def _update_scroll(*_):
            chat_canvas.configure(scrollregion=chat_canvas.bbox("all"))
            chat_canvas.yview_moveto(1.0)

        bubble_frame.bind("<Configure>", _update_scroll)

        def _on_enter(_e):
            chat_canvas.bind_all(
                "<MouseWheel>",
                lambda e: chat_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
            )

        def _on_leave(_e):
            chat_canvas.unbind_all("<MouseWheel>")

        chat_canvas.bind("<Enter>", _on_enter)
        chat_canvas.bind("<Leave>", _on_leave)

        # Composer
        entry_frame = tk.Frame(wrapper, bg=color("bg"))
        entry_frame.pack(fill="x")

        entry = make_entry(entry_frame)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=10)

        # ---- bubble helpers ----
        def add_bubble(role, text_content):
            row = tk.Frame(bubble_frame, bg=color("input"))
            row.pack(fill="x", padx=14, pady=6)
            if role == "user":
                bubble = tk.Label(
                    row, text=text_content,
                    bg=color("accent"), fg=color("on_accent"),
                    font=font(11), wraplength=560, justify="left",
                    padx=14, pady=10,
                )
                bubble.pack(side="right", anchor="e")
            else:
                bubble = tk.Label(
                    row, text=text_content,
                    bg=color("panel"), fg=color("text"),
                    font=font(11), wraplength=560, justify="left",
                    padx=14, pady=10,
                )
                bubble.pack(side="left", anchor="w")
            return bubble

        def animate_dots(label, state=[0]):
            if not self._typing_anim_running:
                return
            frames = ["●  ○  ○", "○  ●  ○", "○  ○  ●", "○  ●  ○"]
            try:
                label.config(text=frames[state[0] % len(frames)])
            except tk.TclError:
                return
            state[0] += 1
            page.after(300, lambda: animate_dots(label, state))

        def send_message(_event=None):
            user_text = entry.get().strip()
            if not user_text or self._typing_anim_running:
                return
            entry.delete(0, tk.END)
            add_bubble("user", user_text)
            self.chat_history.append({"role": "user", "content": user_text})
            thinking_label = add_bubble("assistant", "●  ○  ○")
            self._typing_anim_running = True
            animate_dots(thinking_label)

            def worker():
                reply = get_ai_response(self.chat_history)

                def show():
                    self._typing_anim_running = False
                    try:
                        thinking_label.config(text=reply)
                    except tk.TclError:
                        return
                    self.chat_history.append({"role": "assistant", "content": reply})

                try:
                    self.root.after(0, show)
                except RuntimeError:
                    pass

            threading.Thread(target=worker, daemon=True).start()

        def clear_chat():
            self._typing_anim_running = False
            self.chat_history = []
            for child in bubble_frame.winfo_children():
                child.destroy()
            add_bubble("assistant", "New chat started. Ask me anything.")

        make_button(entry_frame, "Send", send_message, primary=True).pack(side="right")
        entry.bind("<Return>", send_message)
        add_bubble("assistant", "Hi! I'm your AI assistant. Ask me anything.")


    # MULTI-SOURCE SEARCH


    # Source colours (label badge)
    SOURCE_COLORS = {
        "Wikipedia":  "#3366CC",
        "DuckDuckGo": "#DE5833",
        "Books":      "#4CAF7D",
        "Reddit":     "#FF4500",
        "Images":     "#7C5CFC",
    }
    ALL_SOURCES = ["Wikipedia", "DuckDuckGo", "Books", "Reddit", "Images"]

    def build_database(self, page):
        self._search_source_var = tk.StringVar(value="All")
        self._search_image_refs = []   # keep PhotoImage refs alive

        wrapper = tk.Frame(page, bg=color("bg"))
        wrapper.pack(pady=20, padx=28, fill="both", expand=True)

        # ---- Header ----
        tk.Label(wrapper, text="⊙  Search", bg=color("bg"), fg=color("text"),
                 font=font(20, bold=True)).pack(anchor="w")
        tk.Label(wrapper, text="Search Wikipedia, DuckDuckGo, Books, Reddit & Images",
                 bg=color("bg"), fg=color("subtext"), font=font(11)).pack(anchor="w", pady=(2, 14))

        # ---- Search bar ----
        search_row = tk.Frame(wrapper, bg=color("bg"))
        search_row.pack(fill="x")
        self.search_entry = make_entry(search_row)
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 10))
        self.search_entry.bind("<Return>", lambda _e: self.do_search())
        make_button(search_row, "Search", self.do_search, primary=True).pack(side="left")

        # ---- Source tabs ----
        tabs_row = tk.Frame(wrapper, bg=color("bg"))
        tabs_row.pack(fill="x", pady=(12, 0))
        self._src_tab_buttons = {}
        for src in ["All"] + self.ALL_SOURCES:
            btn = tk.Label(
                tabs_row, text=src,
                bg=color("panel"), fg=color("subtext"),
                font=font(10), padx=12, pady=5, cursor="hand2",
            )
            btn.pack(side="left", padx=(0, 4))
            btn.bind("<Button-1>", lambda _e, s=src: self._switch_search_tab(s))
            self._src_tab_buttons[src] = btn
        self._switch_search_tab("All")   # highlight default

        # ---- Results notebook ----
        # Text results panel
        results_outer = tk.Frame(wrapper, bg=color("input"),
                                 highlightthickness=1, highlightbackground=color("border"))
        results_outer.pack(fill="both", expand=True, pady=(10, 0))

        self.results_text = tk.Text(
            results_outer, bg=color("input"), fg=color("text"), relief="flat",
            padx=14, pady=12, wrap="word", insertbackground=color("text"),
            font=("Consolas", 10), highlightthickness=0, state="disabled",
        )
        sb_text = ttk.Scrollbar(results_outer, orient="vertical",
                                command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=sb_text.set)
        sb_text.pack(side="right", fill="y")
        self.results_text.pack(fill="both", expand=True)

        self.results_text.tag_configure("source_wiki",   foreground="#3366CC", font=font(9, bold=True))
        self.results_text.tag_configure("source_ddg",    foreground="#DE5833", font=font(9, bold=True))
        self.results_text.tag_configure("source_books",  foreground="#4CAF7D", font=font(9, bold=True))
        self.results_text.tag_configure("source_reddit", foreground="#FF4500", font=font(9, bold=True))
        self.results_text.tag_configure("source_images", foreground="#7C5CFC", font=font(9, bold=True))
        self.results_text.tag_configure("title",   foreground=color("text"),   font=font(12, bold=True))
        self.results_text.tag_configure("summary", foreground=color("subtext"), font=font(10))
        self.results_text.tag_configure("link",    foreground=color("accent2"), font=font(9))
        self.results_text.tag_configure("meta",    foreground=color("subtext"), font=font(9))
        self.results_text.tag_configure("sep",     foreground=color("border"))
        self.results_text.tag_configure("h2",      foreground=color("text"),   font=font(13, bold=True))
        self.results_text.tag_configure("error",   foreground="#FC5C7D",       font=font(10))
        self.results_text.tag_configure("status",  foreground=color("subtext"), font=font(10))

        # Image grid panel (hidden by default, shown when Images tab active)
        self._img_outer = tk.Frame(wrapper, bg=color("input"),
                                   highlightthickness=1, highlightbackground=color("border"))
        self._img_canvas = tk.Canvas(self._img_outer, bg=color("input"),
                                     highlightthickness=0)
        img_sb = ttk.Scrollbar(self._img_outer, orient="vertical",
                               command=self._img_canvas.yview)
        self._img_canvas.configure(yscrollcommand=img_sb.set)
        img_sb.pack(side="right", fill="y")
        self._img_canvas.pack(fill="both", expand=True)
        self._img_inner = tk.Frame(self._img_canvas, bg=color("input"))
        self._img_canvas_window = self._img_canvas.create_window(
            (0, 0), window=self._img_inner, anchor="nw"
        )
        self._img_inner.bind(
            "<Configure>",
            lambda e: self._img_canvas.configure(
                scrollregion=self._img_canvas.bbox("all")
            )
        )
        self._img_canvas.bind(
            "<Configure>",
            lambda e: self._img_canvas.itemconfig(
                self._img_canvas_window, width=e.width
            )
        )

        self._search_showing_images = False

    def _switch_search_tab(self, src):
        self._search_source_var.set(src)
        for name, btn in self._src_tab_buttons.items():
            if name == src:
                btn.config(bg=color("accent"), fg=color("on_accent"))
            else:
                btn.config(bg=color("panel"), fg=color("subtext"))

    def _sources_for_tab(self):
        tab = self._search_source_var.get()
        if tab == "All":
            return self.ALL_SOURCES
        return [tab]

    def _text_write(self, *args):
        self.results_text.config(state="normal")
        self.results_text.insert(*args)
        self.results_text.config(state="disabled")

    def _text_clear(self):
        self.results_text.config(state="normal")
        self.results_text.delete("1.0", tk.END)
        self.results_text.config(state="disabled")

    def _show_text_panel(self):
        if self._search_showing_images:
            self._img_outer.pack_forget()
            self.results_text.master.pack(fill="both", expand=True, pady=(10, 0))
            self._search_showing_images = False

    def _show_image_panel(self):
        if not self._search_showing_images:
            self.results_text.master.pack_forget()
            self._img_outer.pack(fill="both", expand=True, pady=(10, 0))
            self._search_showing_images = True

    def do_search(self):
        query = self.search_entry.get().strip()
        sources = self._sources_for_tab()
        if not query:
            self._show_text_panel()
            self._text_clear()
            self._text_write(tk.END, "Please enter a search term.\n", "status")
            return

        if sources == ["Images"]:
            self._show_image_panel()
            for w in self._img_inner.winfo_children():
                w.destroy()
            self._search_image_refs.clear()
            tk.Label(self._img_inner, text=f"Searching images for '{query}'…",
                     bg=color("input"), fg=color("subtext"),
                     font=font(11), pady=20).pack()
        else:
            self._show_text_panel()
            self._text_clear()
            self._text_write(tk.END, f"Searching '{query}' across {', '.join(sources)}…\n", "status")

        def work():
            results, errors = multi_search(query, sources)
            try:
                self.root.after(0, lambda: self._render_results(query, results, errors, sources))
            except RuntimeError:
                pass

        threading.Thread(target=work, daemon=True).start()

    def _render_results(self, query, results, errors, sources):
        # Images-only tab → grid view
        if sources == ["Images"]:
            self._render_image_grid(results.get("Images", []), errors.get("Images"))
            return

        # Otherwise → text view (may include inline book covers later)
        self._show_text_panel()
        self._text_clear()

        source_tag_map = {
            "Wikipedia":  "source_wiki",
            "DuckDuckGo": "source_ddg",
            "Books":      "source_books",
            "Reddit":     "source_reddit",
            "Images":     "source_images",
        }
        spoken = []
        has_any = False

        for src in sources:
            if src == "Images":
                continue
            items = results.get(src, [])
            err   = errors.get(src)
            tag   = source_tag_map.get(src, "source_wiki")

            if err:
                self._text_write(tk.END, f"[{src}]\n", tag)
                self._text_write(tk.END, f"  Error: {err}\n\n", "error")
                continue
            if not items:
                self._text_write(tk.END, f"[{src}]  No results.\n\n", tag)
                continue

            self._text_write(tk.END, f"[{src}]\n", tag)
            self._text_write(tk.END, "─" * 68 + "\n", "sep")
            has_any = True

            for item in items:
                title   = item.get("title") or ""
                summary = item.get("summary") or ""
                link    = item.get("link") or ""
                meta    = item.get("meta") or ""

                self._text_write(tk.END, title + "\n", "title")
                spoken.append(title)
                if summary:
                    self._text_write(tk.END, summary + "\n", "summary")
                    spoken.append(summary[:80])
                if meta:
                    self._text_write(tk.END, meta + "\n", "meta")
                if link:
                    self._text_write(tk.END, link + "\n", "link")
                self._text_write(tk.END, "\n")

            self._text_write(tk.END, "\n")

        if not has_any and not errors:
            self._text_write(tk.END, "No results found.\n", "status")

        # If "All" was selected also show image thumbnails below text
        if "Images" in sources:
            img_data = results.get("Images", [])
            if img_data:
                self._text_write(tk.END, "[Images]  (loading thumbnails…)\n", "source_images")
                threading.Thread(
                    target=self._load_inline_images,
                    args=(img_data[:6],),
                    daemon=True,
                ).start()

        settings["last_result"] = ". ".join(spoken)
        speak(settings["last_result"])

    def _render_image_grid(self, images, error):
        for w in self._img_inner.winfo_children():
            w.destroy()
        self._search_image_refs.clear()

        if error:
            tk.Label(self._img_inner, text=f"Error: {error}",
                     bg=color("input"), fg="#FC5C7D", font=font(11), pady=20).pack()
            return
        if not images:
            tk.Label(self._img_inner, text="No images found.",
                     bg=color("input"), fg=color("subtext"), font=font(11), pady=20).pack()
            return

        cols = 4
        for i, img_info in enumerate(images):
            row_idx = i // cols
            col_idx = i % cols
            cell = tk.Frame(self._img_inner, bg=color("panel"),
                            highlightthickness=1, highlightbackground=color("border"))
            cell.grid(row=row_idx, column=col_idx, padx=6, pady=6, sticky="nsew")
            self._img_inner.columnconfigure(col_idx, weight=1)

            thumb_label = tk.Label(cell, bg=color("panel"), text="⏳",
                                   font=font(14), width=18, height=8)
            thumb_label.pack(padx=4, pady=(6, 2))

            title_text = img_info.get("title") or ""
            desc_text  = (img_info.get("desc") or "")[:60]
            tk.Label(cell, text=title_text[:30], bg=color("panel"),
                     fg=color("text"), font=font(9, bold=True),
                     wraplength=140).pack(padx=4)
            if desc_text:
                tk.Label(cell, text=desc_text, bg=color("panel"),
                         fg=color("subtext"), font=font(8),
                         wraplength=140).pack(padx=4, pady=(0, 6))

            full_url = img_info.get("full_url") or ""
            if full_url:
                link_btn = tk.Label(cell, text="Open ↗", bg=color("panel"),
                                    fg=color("accent2"), font=font(8), cursor="hand2")
                link_btn.pack(pady=(0, 6))
                link_btn.bind("<Button-1>", lambda _e, u=full_url: self._open_url(u))

            threading.Thread(
                target=self._load_thumb,
                args=(img_info.get("thumb_url", ""), thumb_label),
                daemon=True,
            ).start()

    def _load_thumb(self, url, label):
        if not url or not HAS_PIL:
            return
        try:
            data = _http_get_bytes(url)
            pil_img = PIL_Image.open(io.BytesIO(data))
            pil_img.thumbnail((160, 120), PIL_Image.LANCZOS)
            photo = PIL_ImageTk.PhotoImage(pil_img)
            self._search_image_refs.append(photo)
            try:
                self.root.after(0, lambda ph=photo, lb=label: _safe_label_image(lb, ph))
            except RuntimeError:
                pass
        except Exception:
            pass

    def _load_inline_images(self, images):
        for img_info in images:
            url = img_info.get("thumb_url") or ""
            if not url or not HAS_PIL:
                continue
            try:
                data = _http_get_bytes(url)
                pil_img = PIL_Image.open(io.BytesIO(data))
                pil_img.thumbnail((100, 80), PIL_Image.LANCZOS)
                photo = PIL_ImageTk.PhotoImage(pil_img)
                self._search_image_refs.append(photo)
                title = img_info.get("title") or ""

                def insert_img(ph=photo, t=title):
                    self.results_text.config(state="normal")
                    self.results_text.image_create(tk.END, image=ph, padx=4, pady=4)
                    self.results_text.insert(tk.END, f" {t}\n", "meta")
                    self.results_text.config(state="disabled")

                try:
                    self.root.after(0, insert_img)
                except RuntimeError:
                    pass
            except Exception:
                pass

    def _open_url(self, url):
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass

    def show_search_error(self, message):
        self._text_clear()
        self._text_write(tk.END, "Error: " + message + "\n", "error")

    def show_search_results(self, results):
        pass  # replaced by _render_results


    # NOTES

    # WEATHER

    def build_weather(self, page):
        wrapper = tk.Frame(page, bg=color("bg"))
        wrapper.pack(fill="both", expand=True, padx=28, pady=24)

        tk.Label(wrapper, text="☁  Weather", bg=color("bg"), fg=color("text"),
                 font=font(20, bold=True)).pack(anchor="w")
        tk.Label(wrapper, text="Enter any city name to get current weather",
                 bg=color("bg"), fg=color("subtext"), font=font(11)).pack(anchor="w", pady=(4, 20))

        search_row = tk.Frame(wrapper, bg=color("bg"))
        search_row.pack(fill="x", pady=(0, 20))

        self._weather_city_var = tk.StringVar()
        city_entry = make_entry(search_row, textvariable=self._weather_city_var)
        city_entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 10))
        city_entry.bind("<Return>", lambda _e: self._weather_fetch())

        make_button(search_row, "Get Weather", self._weather_fetch, primary=True).pack(side="left")

        self._weather_result_frame = tk.Frame(wrapper, bg=color("bg"))
        self._weather_result_frame.pack(fill="both", expand=True)

        # Placeholder
        tk.Label(
            self._weather_result_frame,
            text="☁\n\nEnter a city above to see the weather.",
            bg=color("bg"), fg=color("subtext"), font=font(14), justify="center",
        ).pack(expand=True)

    def _weather_fetch(self):
        city = (self._weather_city_var.get() or "").strip()
        if not city:
            Toast.show(self.root, "Please enter a city name.", "warning")
            return

        for w in self._weather_result_frame.winfo_children():
            w.destroy()

        loading = tk.Label(
            self._weather_result_frame,
            text="Fetching weather...", bg=color("bg"),
            fg=color("subtext"), font=font(13),
        )
        loading.pack(expand=True)

        def work():
            try:
                data = fetch_weather(city)
                try:
                    self.root.after(0, lambda d=data: self._weather_show(d))
                except RuntimeError:
                    pass
            except Exception as e:
                msg = str(e)
                try:
                    self.root.after(0, lambda m=msg: self._weather_error(m))
                except RuntimeError:
                    pass

        threading.Thread(target=work, daemon=True).start()

    def _weather_error(self, message):
        for w in self._weather_result_frame.winfo_children():
            w.destroy()
        tk.Label(
            self._weather_result_frame,
            text=f"Could not get weather:\n{message}",
            bg=color("bg"), fg=color("danger"), font=font(11), justify="center",
        ).pack(expand=True)

    def _weather_show(self, data):
        for w in self._weather_result_frame.winfo_children():
            w.destroy()

        # Main card
        card = make_card(self._weather_result_frame, bg_key="panel")
        card.pack(padx=0, pady=0, fill="x")

        inner = tk.Frame(card, bg=color("panel"))
        inner.pack(padx=30, pady=30)

        tk.Label(inner, text=data["city"], bg=color("panel"), fg=color("text"),
                 font=font(18, bold=True)).pack()
        tk.Label(inner, text=data["desc"], bg=color("panel"), fg=color("subtext"),
                 font=font(12)).pack(pady=(2, 18))

        temp_row = tk.Frame(inner, bg=color("panel"))
        temp_row.pack(pady=(0, 18))
        tk.Label(temp_row, text=f"{data['temp_c']}°C", bg=color("panel"),
                 fg=color("accent"), font=font(48, bold=True)).pack(side="left", padx=(0, 20))
        tk.Label(temp_row, text=f"{data['temp_f']}°F", bg=color("panel"),
                 fg=color("subtext"), font=font(24)).pack(side="left")

        # Stats row
        stats = tk.Frame(inner, bg=color("panel"))
        stats.pack()

        stats_items = [
            ("Feels like", f"{data['feels_c']}°C"),
            ("Humidity", f"{data['humidity']}%"),
            ("Wind", f"{data['wind']} km/h"),
        ]
        for label, val in stats_items:
            stat_box = make_card(stats, bg_key="highlight")
            stat_box.pack(side="left", padx=8, pady=4, ipadx=14, ipady=10)
            tk.Label(stat_box, text=val, bg=color("highlight"), fg=color("text"),
                     font=font(14, bold=True)).pack()
            tk.Label(stat_box, text=label, bg=color("highlight"), fg=color("subtext"),
                     font=font(9)).pack()


    # CALCULATOR

    def build_calculator(self, page):
        wrapper = tk.Frame(page, bg=color("bg"))
        wrapper.pack(fill="both", expand=True, padx=28, pady=24)

        tk.Label(wrapper, text="⊞  Calculator", bg=color("bg"), fg=color("text"),
                 font=font(20, bold=True)).pack(anchor="w", pady=(0, 20))

        # Center the calculator
        center = tk.Frame(wrapper, bg=color("bg"))
        center.pack(expand=True)

        calc_card = make_card(center, bg_key="panel")
        calc_card.pack(padx=8, pady=8)

        inner = tk.Frame(calc_card, bg=color("panel"), padx=20, pady=20)
        inner.pack()

        self._calc_expression = ""
        self._calc_display_var = tk.StringVar(value="0")

        # Display
        display_frame = tk.Frame(inner, bg=color("input"),
                                 highlightthickness=1, highlightbackground=color("border"))
        display_frame.pack(fill="x", pady=(0, 16))

        self._calc_expr_var = tk.StringVar(value="")
        tk.Label(display_frame, textvariable=self._calc_expr_var,
                 bg=color("input"), fg=color("subtext"), font=font(10),
                 anchor="e", padx=14, pady=4).pack(fill="x")

        display_lbl = tk.Label(
            display_frame, textvariable=self._calc_display_var,
            bg=color("input"), fg=color("text"),
            font=font(28, bold=True), anchor="e", padx=14, pady=10, width=14,
        )
        display_lbl.pack(fill="x")

        # Buttons layout
        buttons = [
            ["C", "±", "%", "÷"],
            ["7", "8", "9", "×"],
            ["4", "5", "6", "−"],
            ["1", "2", "3", "+"],
            ["0", ".", "⌫", "="],
        ]

        btn_frame = tk.Frame(inner, bg=color("panel"))
        btn_frame.pack()

        for r, row in enumerate(buttons):
            for c, label in enumerate(row):
                is_op = label in ("÷", "×", "−", "+", "=")
                is_special = label in ("C", "±", "%", "⌫")
                if is_op:
                    bg_col, fg_col = color("accent"), color("on_accent")
                elif is_special:
                    bg_col, fg_col = color("highlight"), color("accent")
                else:
                    bg_col, fg_col = color("panel2"), color("text")

                span = 2 if (label == "0" and c == 0) else 1
                btn = tk.Button(
                    btn_frame, text=label,
                    command=lambda lbl=label: self._calc_press(lbl),
                    bg=bg_col, fg=fg_col,
                    activebackground=bg_col, activeforeground=fg_col,
                    relief="flat", bd=0, cursor="hand2",
                    font=font(14, bold=True),
                    width=3 if span == 1 else 7, height=2,
                    highlightthickness=1, highlightbackground=color("border"),
                )
                btn.grid(row=r, column=c, columnspan=span, padx=4, pady=4, sticky="nsew")

        # Keyboard bindings
        self.root.bind("<Key>", self._calc_key_press)

    def _calc_key_press(self, event):
        if self.current_page != "calculator":
            return
        k = event.char
        if k in "0123456789.":
            self._calc_press(k)
        elif k in "+-":
            self._calc_press(k if k == "+" else "−")
        elif k == "*":
            self._calc_press("×")
        elif k == "/":
            self._calc_press("÷")
        elif k in ("\r", "\n"):
            self._calc_press("=")
        elif event.keysym == "BackSpace":
            self._calc_press("⌫")
        elif k == "c" or k == "C":
            self._calc_press("C")
        elif k == "%":
            self._calc_press("%")

    def _calc_press(self, label):
        try:
            if label == "C":
                self._calc_expression = ""
                self._calc_display_var.set("0")
                self._calc_expr_var.set("")
            elif label == "⌫":
                if self._calc_expression:
                    self._calc_expression = self._calc_expression[:-1]
                    self._calc_display_var.set(self._calc_expression or "0")
                    self._calc_expr_var.set("")
            elif label == "=":
                expr = self._calc_expression
                expr = expr.replace("÷", "/").replace("×", "*").replace("−", "-")
                result = eval(expr)
                self._calc_expr_var.set(self._calc_expression + " =")
                # Format cleanly
                if isinstance(result, float) and result == int(result):
                    result = int(result)
                self._calc_display_var.set(str(result))
                self._calc_expression = str(result)
            elif label == "±":
                if self._calc_expression and self._calc_expression != "0":
                    if self._calc_expression.startswith("-"):
                        self._calc_expression = self._calc_expression[1:]
                    else:
                        self._calc_expression = "-" + self._calc_expression
                    self._calc_display_var.set(self._calc_expression)
            elif label == "%":
                if self._calc_expression:
                    val = eval(self._calc_expression.replace("÷", "/").replace("×", "*").replace("−", "-"))
                    val = val / 100
                    self._calc_expression = str(val)
                    self._calc_display_var.set(str(val))
                    self._calc_expr_var.set("")
            else:
                # digit or operator
                if self._calc_display_var.get() == "0" and label.isdigit():
                    self._calc_expression = label
                else:
                    self._calc_expression += label
                self._calc_display_var.set(self._calc_expression[-16:])
                self._calc_expr_var.set("")
        except Exception:
            self._calc_display_var.set("Error")
            self._calc_expr_var.set(self._calc_expression + " =")
            self._calc_expression = ""


    # CONTACT

    def build_contact(self, page):
        wrapper = tk.Frame(page, bg=color("bg"))
        wrapper.pack(fill="both", expand=True, padx=28, pady=24)

        tk.Label(wrapper, text="✉  Contact", bg=color("bg"), fg=color("text"),
                 font=font(20, bold=True)).pack(anchor="w", pady=(0, 20))

        card = make_card(wrapper, bg_key="panel")
        card.pack(anchor="w", fill="x", padx=0, pady=0)

        inner = tk.Frame(card, bg=color("panel"), padx=30, pady=24)
        inner.pack(fill="x")

        contact_items = [
            ("📞", "Phone",          "7722590947"),
            ("📧", "Personal Email", "madhusudhant207@gmail.com"),
            ("📸", "Instagram",      "@airbusissocool102"),
            ("💼", "Work Email",     "boimdmdmdmd@gmail.com"),
            ("🎵", "TikTok",         "Don't got it"),
        ]

        for emoji, label, value in contact_items:
            row = tk.Frame(inner, bg=color("panel"))
            row.pack(fill="x", pady=6)
            tk.Label(row, text=emoji, bg=color("panel"), fg=color("text"),
                     font=font(14), width=3).pack(side="left")
            tk.Label(row, text=label, bg=color("panel"), fg=color("subtext"),
                     font=font(10, bold=True), width=16, anchor="w").pack(side="left")
            tk.Label(row, text=value, bg=color("panel"), fg=color("text"),
                     font=font(11), anchor="w").pack(side="left")


    # SETTINGS

    def build_settings(self, page):
        wrapper = tk.Frame(page, bg=color("bg"))
        wrapper.pack(pady=24, padx=28, fill="both", expand=True)

        tk.Label(wrapper, text="⚙  Settings", bg=color("bg"), fg=color("text"),
                 font=font(20, bold=True)).pack(anchor="w", pady=(0, 20))

        card = make_card(wrapper, bg_key="panel")
        card.pack(anchor="w", fill="x")

        inner = tk.Frame(card, bg=color("panel"), padx=30, pady=24)
        inner.pack(fill="x")

        def section_header(text):
            tk.Label(inner, text=text.upper(), bg=color("panel"), fg=color("subtext"),
                     font=font(9, bold=True)).pack(anchor="w", pady=(16, 4))
            make_separator(inner).pack(fill="x", pady=(0, 10))

        # Theme
        section_header("Appearance")
        row = tk.Frame(inner, bg=color("panel"))
        row.pack(anchor="w", fill="x")
        tk.Label(row, text="Theme", bg=color("panel"), fg=color("text"),
                 font=font(11), width=20, anchor="w").pack(side="left")
        self.theme_choice = ttk.Combobox(
            row, values=["Dark", "Light"], state="readonly",
            style="App.TCombobox", width=14,
        )
        self.theme_choice.set("Dark" if settings["theme"] == "dark" else "Light")
        self.theme_choice.pack(side="left")

        # Text scale
        section_header("Text Size")
        self.scale_value = tk.DoubleVar(value=settings["text_scale"])
        scale_row = tk.Frame(inner, bg=color("panel"))
        scale_row.pack(anchor="w", fill="x")
        tk.Label(scale_row, text="Scale", bg=color("panel"), fg=color("text"),
                 font=font(11), width=20, anchor="w").pack(side="left")
        tk.Scale(
            scale_row, from_=0.8, to=2.0, resolution=0.1, orient="horizontal",
            variable=self.scale_value, bg=color("panel"), fg=color("text"),
            troughcolor=color("input"), highlightthickness=0, length=200,
            activebackground=color("accent"),
        ).pack(side="left")

        # Language
        section_header("Language")
        lang_row = tk.Frame(inner, bg=color("panel"))
        lang_row.pack(anchor="w", fill="x")
        tk.Label(lang_row, text="Language", bg=color("panel"), fg=color("text"),
                 font=font(11), width=20, anchor="w").pack(side="left")
        self.language_choice = ttk.Combobox(
            lang_row, values=sorted(LANGUAGES), state="readonly",
            style="App.TCombobox", width=28,
        )
        self.language_choice.set(settings["language"])
        self.language_choice.pack(side="left")

        # TTS
        section_header("Accessibility")
        tts_row = tk.Frame(inner, bg=color("panel"))
        tts_row.pack(anchor="w")
        self.tts_value = tk.BooleanVar(value=settings["tts"])
        tk.Checkbutton(
            tts_row, text=translate("Enable text-to-speech"), variable=self.tts_value,
            bg=color("panel"), fg=color("text"), selectcolor=color("input"),
            activebackground=color("panel"), activeforeground=color("text"),
            font=font(11),
        ).pack(side="left")

        make_button(inner, "Save Settings", self.save_settings, primary=True).pack(
            anchor="w", pady=(24, 0))

    def save_settings(self):
        settings["theme"] = "dark" if self.theme_choice.get() == "Dark" else "light"
        settings["text_scale"] = float(self.scale_value.get())
        settings["tts"] = bool(self.tts_value.get())
        new_language = self.language_choice.get()

        def finish():
            settings["language"] = new_language
            self.build_window()
            Toast.show(self.root, "Settings saved!", "success")

        if new_language == settings["language"] or not HAS_TRANSLATOR:
            finish()
            return

        def background():
            preload_language(new_language)
            try:
                self.root.after(0, finish)
            except RuntimeError:
                pass

        threading.Thread(target=background, daemon=True).start()


    # MP3 PLAYER

    def build_mp3_player(self, page):
        wrapper = tk.Frame(page, bg=color("bg"))
        wrapper.pack(fill="both", expand=True, padx=20, pady=16)

        # Header
        header = tk.Frame(wrapper, bg=color("bg"))
        header.pack(fill="x", pady=(0, 14))
        tk.Label(header, text="♫  MP3 Player", bg=color("bg"), fg=color("text"),
                 font=font(20, bold=True)).pack(side="left")
        make_button(header, "Load Folder", self.mp3_load_folder, primary=True, small=True).pack(side="right")
        make_button(header, "Add Files", self.mp3_add_files, small=True).pack(side="right", padx=(0, 6))
        make_button(header, "Clear", self.mp3_clear_playlist, small=True).pack(side="right", padx=(0, 6))

        body = tk.Frame(wrapper, bg=color("bg"))
        body.pack(fill="both", expand=True)

        # ----- LEFT: playlist -----
        left = tk.Frame(body, bg=color("panel"), width=300,
                        highlightthickness=1, highlightbackground=color("border"))
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)

        tk.Label(left, text="PLAYLIST", bg=color("panel"), fg=color("subtext"),
                 font=font(9, bold=True), padx=14, pady=12).pack(anchor="w")

        list_frame = tk.Frame(left, bg=color("panel"))
        list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            list_frame,
            bg=color("input"), fg=color("text"),
            selectbackground=color("accent"), selectforeground=color("on_accent"),
            highlightthickness=0, borderwidth=0,
            font=font(10), activestyle="none",
            yscrollcommand=scrollbar.set,
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", lambda _e: self.mp3_play_selected())
        self.listbox.bind("<Return>", lambda _e: self.mp3_play_selected())
        scrollbar.config(command=self.listbox.yview)

        # ----- RIGHT: player -----
        right = tk.Frame(body, bg=color("panel"),
                         highlightthickness=1, highlightbackground=color("border"))
        right.pack(side="left", fill="both", expand=True)

        center_frame = tk.Frame(right, bg=color("panel"))
        center_frame.pack(expand=True, fill="both", padx=30, pady=24)

        # Cover art
        self.default_cover = self.make_default_cover(280)
        self.cover_label = tk.Label(
            center_frame, bg=color("input"), image=self.default_cover,
            width=280, height=280,
        )
        self.cover_label.image = self.default_cover
        self.cover_label.pack(pady=(0, 18))

        self.song_label = tk.Label(center_frame, text=translate("No song playing"),
                                   bg=color("panel"), fg=color("text"), font=font(15, bold=True))
        self.song_label.pack()

        self.artist_label = tk.Label(center_frame, text="—", bg=color("panel"),
                                     fg=color("subtext"), font=font(11))
        self.artist_label.pack(pady=(2, 16))

        # Seek bar
        seek_frame = tk.Frame(center_frame, bg=color("panel"))
        seek_frame.pack(fill="x")
        self.seek_var = tk.DoubleVar(value=0)
        self.seek_scale = tk.Scale(
            seek_frame, from_=0, to=100, orient="horizontal",
            variable=self.seek_var,
            bg=color("panel"), fg=color("panel"),
            troughcolor=color("input"), activebackground=color("accent"),
            highlightthickness=0, sliderrelief="flat", showvalue=False, length=400,
        )
        self.seek_scale.pack(fill="x")
        self.seek_scale.bind("<ButtonPress-1>", lambda _e: self.mp3_seek_start())
        self.seek_scale.bind("<ButtonRelease-1>", lambda _e: self.mp3_seek_end())

        self.time_label = tk.Label(center_frame, text="00:00 / 00:00",
                                   bg=color("panel"), fg=color("subtext"), font=font(10))
        self.time_label.pack(pady=(2, 16))

        # Controls
        controls = tk.Frame(center_frame, bg=color("panel"))
        controls.pack(pady=(0, 12))

        self.shuffle_button = tk.Button(
            controls, text="⇄", command=self.mp3_toggle_shuffle,
            bg=color("panel"), fg=color("subtext"),
            activebackground=color("panel"), activeforeground=color("accent"),
            relief="flat", bd=0, cursor="hand2",
            font=font(14), width=3,
        )
        self.shuffle_button.pack(side="left", padx=8)

        tk.Button(controls, text="⏮", command=self.mp3_prev,
                  bg=color("panel"), fg=color("text"),
                  activebackground=color("panel"), activeforeground=color("accent"),
                  relief="flat", bd=0, cursor="hand2", font=font(16), width=3).pack(side="left", padx=8)

        self.play_button = tk.Button(
            controls, text="▶", command=self.mp3_toggle_play,
            bg=color("accent"), fg=color("on_accent"),
            activebackground=color("accent"), activeforeground=color("on_accent"),
            relief="flat", bd=0, cursor="hand2",
            font=font(18, bold=True), width=4, height=1,
        )
        self.play_button.pack(side="left", padx=10)

        tk.Button(controls, text="⏭", command=self.mp3_next,
                  bg=color("panel"), fg=color("text"),
                  activebackground=color("panel"), activeforeground=color("accent"),
                  relief="flat", bd=0, cursor="hand2", font=font(16), width=3).pack(side="left", padx=8)

        self.repeat_button = tk.Button(
            controls, text="↻", command=self.mp3_toggle_repeat,
            bg=color("panel"), fg=color("subtext"),
            activebackground=color("panel"), activeforeground=color("accent"),
            relief="flat", bd=0, cursor="hand2", font=font(14), width=3,
        )
        self.repeat_button.pack(side="left", padx=8)

        # Volume
        volume_row = tk.Frame(center_frame, bg=color("panel"))
        volume_row.pack(pady=(6, 0))
        tk.Label(volume_row, text="🔊", bg=color("panel"), fg=color("subtext"),
                 font=font(12)).pack(side="left", padx=(0, 8))
        self.volume_var = tk.DoubleVar(value=self.volume * 100)
        tk.Scale(
            volume_row, from_=0, to=100, orient="horizontal",
            variable=self.volume_var, command=self.mp3_set_volume,
            bg=color("panel"), fg=color("panel"),
            troughcolor=color("input"), activebackground=color("accent"),
            highlightthickness=0, sliderrelief="flat", showvalue=False, length=200,
        ).pack(side="left")

    # ---------- MP3 helpers ----------
    def make_default_cover(self, size):
        if not HAS_PIL:
            return None
        img = PIL_Image.new("RGB", (size, size), color("input"))
        draw = ImageDraw.Draw(img)
        # Draw a simple music note shape
        draw.ellipse([size//3, size//2, 2*size//3, 3*size//4],
                     fill=color("highlight"))
        draw.rectangle([2*size//3 - 4, size//3, 2*size//3, 3*size//4],
                       fill=color("highlight"))
        return PIL_ImageTk.PhotoImage(img)

    def mp3_load_folder(self):
        folder = filedialog.askdirectory(title=translate("Choose music folder"))
        if not folder:
            return
        added = 0
        for root_dir, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(".mp3"):
                    self.mp3_add_to_playlist(os.path.join(root_dir, file))
                    added += 1
        if added == 0:
            messagebox.showinfo(translate("MP3 Player"), translate("No MP3 files found."))
        else:
            Toast.show(self.root, f"Added {added} track{'s' if added != 1 else ''}.", "success")

    def mp3_add_files(self):
        files = filedialog.askopenfilenames(
            title=translate("Choose MP3 files"),
            filetypes=[("MP3 audio", "*.mp3"), ("All files", "*.*")],
        )
        for f in files:
            if f.lower().endswith(".mp3"):
                self.mp3_add_to_playlist(f)

    def mp3_add_to_playlist(self, path):
        self.playlist.append(path)
        self.listbox.insert(tk.END, "  " + os.path.basename(path))

    def mp3_clear_playlist(self):
        self.mp3_stop()
        self.playlist.clear()
        self.listbox.delete(0, tk.END)
        self.current_index = -1

    def mp3_play_selected(self):
        sel = self.listbox.curselection()
        if sel:
            self.mp3_play(sel[0])

    def mp3_play(self, index):
        if not self.playlist or index < 0 or index >= len(self.playlist):
            return
        if not HAS_PYGAME:
            messagebox.showerror(translate("MP3 Player"), translate("pygame is not available."))
            return
        self.current_index = index
        path = self.playlist[index]
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
        except Exception as error:
            messagebox.showerror(translate("MP3 Player"),
                                 translate("Could not play this file.") + f"\n{error}")
            return
        self.is_playing = True
        self.is_paused = False
        self.seek_offset = 0
        try:
            if HAS_MUTAGEN:
                audio = MP3(path)
                self.song_length = max(1, int(audio.info.length))
            else:
                self.song_length = 0
        except Exception:
            self.song_length = 0
        title, artist = self.mp3_get_metadata(path)
        self.song_label.config(text=title)
        self.artist_label.config(text=artist or translate("Unknown artist"))
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(index)
        self.listbox.see(index)
        if self.seek_scale is not None:
            self.seek_scale.config(to=max(1, self.song_length))
            self.seek_var.set(0)
        self.mp3_load_cover(path)
        self.play_button.config(text="⏸")

    def mp3_get_metadata(self, path):
        try:
            if not HAS_MUTAGEN:
                return os.path.splitext(os.path.basename(path))[0], ""
            tags = ID3(path)
            title_tag = tags.get("TIT2")
            artist_tag = tags.get("TPE1")
            title = title_tag.text[0] if title_tag else os.path.splitext(os.path.basename(path))[0]
            artist = artist_tag.text[0] if artist_tag else ""
            return title, artist
        except Exception:
            return os.path.splitext(os.path.basename(path))[0], ""

    def mp3_load_cover(self, path):
        photo = None
        try:
            if not HAS_MUTAGEN or not HAS_PIL:
                self.cover_label.config(image="", bg=color("panel"))
                return
            tags = ID3(path)
            for tag in tags.values():
                if getattr(tag, "FrameID", "") == "APIC":
                    img = PIL_Image.open(io.BytesIO(tag.data)).convert("RGB")
                    img = img.resize((280, 280), PIL_Image.LANCZOS)
                    photo = PIL_ImageTk.PhotoImage(img)
                    break
        except Exception:
            photo = None
        if photo is None:
            photo = self.default_cover
        self.cover_label.config(image=photo, text="")
        self.cover_label.image = photo

    def mp3_toggle_play(self):
        if not self.playlist or not HAS_PYGAME:
            return
        if self.current_index < 0:
            self.mp3_play(0)
            return
        if self.is_paused:
            try:
                pygame.mixer.music.unpause()
            except Exception:
                pass
            self.is_paused = False
            self.play_button.config(text="⏸")
        elif self.is_playing:
            try:
                pygame.mixer.music.pause()
            except Exception:
                pass
            self.is_paused = True
            self.play_button.config(text="▶")
        else:
            self.mp3_play(self.current_index)

    def mp3_stop(self):
        try:
            if HAS_PYGAME:
                pygame.mixer.music.stop()
        except Exception:
            pass
        self.is_playing = False
        self.is_paused = False
        self.seek_offset = 0
        if self.play_button is not None:
            self.play_button.config(text="▶")

    def mp3_next(self):
        if not self.playlist:
            return
        if self.shuffle:
            if len(self.playlist) > 1:
                idx = self.current_index
                while idx == self.current_index:
                    idx = random.randint(0, len(self.playlist) - 1)
            else:
                idx = 0
            self.mp3_play(idx)
        elif self.current_index + 1 < len(self.playlist):
            self.mp3_play(self.current_index + 1)
        elif self.repeat:
            self.mp3_play(0)
        else:
            self.mp3_stop()

    def mp3_prev(self):
        if not self.playlist:
            return
        position = self.mp3_current_position()
        if position > 3 or self.current_index <= 0:
            self.mp3_play(self.current_index if self.current_index >= 0 else 0)
        else:
            self.mp3_play(self.current_index - 1)

    def mp3_toggle_shuffle(self):
        self.shuffle = not self.shuffle
        self.shuffle_button.config(fg=color("accent") if self.shuffle else color("subtext"))

    def mp3_toggle_repeat(self):
        self.repeat = not self.repeat
        self.repeat_button.config(fg=color("accent") if self.repeat else color("subtext"))

    def mp3_set_volume(self, value):
        try:
            self.volume = float(value) / 100.0
        except ValueError:
            return
        if HAS_PYGAME:
            try:
                pygame.mixer.music.set_volume(self.volume)
            except Exception:
                pass

    def mp3_seek_start(self):
        self.user_seeking = True

    def mp3_seek_end(self):
        if not self.playlist or self.current_index < 0 or not HAS_PYGAME:
            self.user_seeking = False
            return
        target = float(self.seek_var.get())
        target = max(0, min(target, max(0, self.song_length - 1)))
        try:
            pygame.mixer.music.play(start=target)
            self.seek_offset = target
            self.is_playing = True
            self.is_paused = False
            self.play_button.config(text="⏸")
        except Exception:
            pass
        self.user_seeking = False

    def mp3_current_position(self):
        if not self.is_playing or not HAS_PYGAME:
            return 0
        try:
            ms = pygame.mixer.music.get_pos()
            if ms < 0:
                return self.seek_offset
            return self.seek_offset + (ms / 1000.0)
        except Exception:
            return 0

    # BROWSER (embedded web browser using tkinterweb)

    def build_browser(self, page):
        wrapper = tk.Frame(page, bg=color("bg"))
        wrapper.pack(fill="both", expand=True)

        # URL bar
        bar = tk.Frame(wrapper, bg=color("panel"), pady=6)
        bar.pack(fill="x")
        tk.Label(bar, text="⊕", bg=color("panel"), fg=color("accent"), font=font(14), padx=8).pack(side="left")
        self._browser_url_var = tk.StringVar(value="https://www.google.com")
        url_entry = make_entry(bar, textvariable=self._browser_url_var)
        url_entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))

        content = tk.Frame(wrapper, bg=color("bg"))
        content.pack(fill="both", expand=True)

        if HAS_TKWEB:
            self._browser_frame = HtmlFrame(content, messages_enabled=False)
            self._browser_frame.pack(fill="both", expand=True)

            def go(_e=None):
                u = self._browser_url_var.get().strip()
                if not u.startswith("http"):
                    u = "https://" + u
                self._browser_url_var.set(u)
                try:
                    self._browser_frame.load_url(u)
                except Exception as e:
                    messagebox.showerror("Browser Error", f"Could not load URL:\n{e}")

            make_button(bar, "Go", go, primary=True, small=True).pack(side="left", padx=(0, 4))
            if hasattr(self._browser_frame, "go_back"):
                make_button(bar, "◀", self._browser_frame.go_back, small=True).pack(side="left", padx=(0, 4))
            make_button(bar, "⟳", lambda: self._browser_frame.load_url(self._browser_url_var.get()), small=True).pack(side="left", padx=(0, 4))
            make_button(bar, "Google", lambda: (self._browser_url_var.set("https://www.google.com"), go()), small=True).pack(side="left")
            make_button(bar, "YouTube", lambda: (self._browser_url_var.set("https://www.youtube.com"), go()), small=True).pack(side="left", padx=(0, 4))
            url_entry.bind("<Return>", go)
            go()
        else:
            make_button(bar, "Open in Browser", lambda: webbrowser.open(self._browser_url_var.get()), primary=True, small=True).pack(side="left")
            url_entry.bind("<Return>", lambda _e: webbrowser.open(self._browser_url_var.get()))
            tk.Label(content,
                     text="⊕\n\nIn-App Browser\n\nInstall tkinterweb for a full browser inside the app:\npip install tkinterweb\n\nFor now, clicking 'Open in Browser' opens your system browser.",
                     bg=color("bg"), fg=color("subtext"), font=font(12), justify="center").pack(expand=True)


    # NEWS FEED (RSS reader)

    def build_news(self, page):
        wrapper = tk.Frame(page, bg=color("bg"))
        wrapper.pack(fill="both", expand=True, padx=24, pady=20)

        header = tk.Frame(wrapper, bg=color("bg"))
        header.pack(fill="x", pady=(0, 10))
        tk.Label(header, text="◉  News Feed", bg=color("bg"), fg=color("text"), font=font(20, bold=True)).pack(side="left")
        make_button(header, "Refresh", self._news_refresh, primary=True, small=True).pack(side="right")

        self._news_sources = {
            "BBC World":    "https://feeds.bbci.co.uk/news/world/rss.xml",
            "BBC Tech":     "https://feeds.bbci.co.uk/news/technology/rss.xml",
            "BBC Science":  "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
            "Hacker News":  "https://news.ycombinator.com/rss",
            "NASA":         "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        }
        self._news_source_var = tk.StringVar(value="BBC World")

        src_row = tk.Frame(wrapper, bg=color("bg"))
        src_row.pack(fill="x", pady=(0, 10))
        tk.Label(src_row, text="Source:", bg=color("bg"), fg=color("subtext"), font=font(10)).pack(side="left", padx=(0, 8))
        src_box = ttk.Combobox(src_row, values=list(self._news_sources), textvariable=self._news_source_var, state="readonly", style="App.TCombobox", width=20)
        src_box.pack(side="left")
        src_box.bind("<<ComboboxSelected>>", lambda _e: self._news_refresh())

        list_outer = tk.Frame(wrapper, bg=color("input"), highlightthickness=1, highlightbackground=color("border"))
        list_outer.pack(fill="both", expand=True)
        self._news_canvas = tk.Canvas(list_outer, bg=color("input"), highlightthickness=0)
        news_sb = ttk.Scrollbar(list_outer, orient="vertical", command=self._news_canvas.yview)
        self._news_canvas.configure(yscrollcommand=news_sb.set)
        news_sb.pack(side="right", fill="y")
        self._news_canvas.pack(fill="both", expand=True)
        self._news_inner = tk.Frame(self._news_canvas, bg=color("input"))
        cwin = self._news_canvas.create_window((0, 0), window=self._news_inner, anchor="nw")
        self._news_inner.bind("<Configure>", lambda e: self._news_canvas.configure(scrollregion=self._news_canvas.bbox("all")))
        self._news_canvas.bind("<Configure>", lambda e: self._news_canvas.itemconfig(cwin, width=e.width))

        self._news_refresh()

    def _news_refresh(self):
        for w in self._news_inner.winfo_children():
            w.destroy()
        tk.Label(self._news_inner, text="Loading news...", bg=color("input"), fg=color("subtext"), font=font(11), pady=20).pack()
        url = self._news_sources[self._news_source_var.get()]

        def work():
            try:
                articles = fetch_rss(url)
                try:
                    self.root.after(0, lambda a=articles: self._news_show(a))
                except RuntimeError:
                    pass
            except Exception as e:
                msg = str(e)
                try:
                    self.root.after(0, lambda m=msg: self._news_error(m))
                except RuntimeError:
                    pass

        threading.Thread(target=work, daemon=True).start()

    def _news_show(self, articles):
        for w in self._news_inner.winfo_children():
            w.destroy()
        if not articles:
            tk.Label(self._news_inner, text="No articles found.", bg=color("input"), fg=color("subtext"), font=font(11), pady=20).pack()
            return
        for article in articles:
            card = tk.Frame(self._news_inner, bg=color("panel"), highlightthickness=1, highlightbackground=color("border"))
            card.pack(fill="x", padx=12, pady=5)
            inner = tk.Frame(card, bg=color("panel"))
            inner.pack(fill="x", padx=14, pady=10)
            tk.Label(inner, text=article["title"], bg=color("panel"), fg=color("text"),
                     font=font(11, bold=True), wraplength=700, justify="left", anchor="w").pack(fill="x")
            if article["desc"]:
                tk.Label(inner, text=article["desc"], bg=color("panel"), fg=color("subtext"),
                         font=font(9), wraplength=700, justify="left", anchor="w").pack(fill="x", pady=(2, 0))
            row = tk.Frame(inner, bg=color("panel"))
            row.pack(anchor="w", pady=(6, 0))
            tk.Label(row, text=article["date"][:20], bg=color("panel"), fg=color("subtext"), font=font(8)).pack(side="left", padx=(0, 12))
            link = article["link"]
            make_button(row, "Read →", lambda l=link: webbrowser.open(l), small=True).pack(side="left")

    def _news_error(self, message):
        for w in self._news_inner.winfo_children():
            w.destroy()
        tk.Label(self._news_inner, text=f"Could not load news:\n{message}",
                 bg=color("input"), fg=color("danger"), font=font(11), justify="center", pady=20).pack()


    # VIDEO PLAYER  (embedded python-vlc player window)

    def build_video(self, page):
        self._video_recent = []

        wrapper = tk.Frame(page, bg=color("bg"))
        wrapper.pack(fill="both", expand=True, padx=24, pady=20)

        hdr = tk.Frame(wrapper, bg=color("bg"))
        hdr.pack(fill="x", pady=(0, 16))
        tk.Label(hdr, text="▣  Video Player", bg=color("bg"), fg=color("text"),
                 font=font(20, bold=True)).pack(side="left")
        make_button(hdr, "📂  Open File", self._video_open, primary=True).pack(side="right")

        # Big click-to-open area
        drop_area = tk.Frame(wrapper, bg=color("panel"), pady=40, cursor="hand2")
        drop_area.pack(fill="x", pady=(0, 20))
        tk.Label(drop_area, text="▶", bg=color("panel"), fg=color("accent"),
                 font=font(48)).pack()
        tk.Label(drop_area, text="Click 'Open File' or click here to choose a video",
                 bg=color("panel"), fg=color("subtext"), font=font(11)).pack(pady=(8, 0))
        engine_txt = "python-vlc  (audio + video)" if HAS_VLC else "python-vlc not installed — pip install python-vlc"
        tk.Label(drop_area, text=f"Engine: {engine_txt}", bg=color("panel"),
                 fg=color("accent") if HAS_VLC else color("danger"), font=font(9)).pack(pady=(4, 0))
        for w in [drop_area] + drop_area.winfo_children():
            w.bind("<Button-1>", lambda _e: self._video_open())

        # Recently played
        tk.Label(wrapper, text="Recently Played", bg=color("bg"), fg=color("subtext"),
                 font=font(10, bold=True)).pack(anchor="w", pady=(8, 6))
        self._video_recent_frame = tk.Frame(wrapper, bg=color("bg"))
        self._video_recent_frame.pack(fill="x")
        self._video_empty_lbl = tk.Label(wrapper, text="No recent files yet.",
                                         bg=color("bg"), fg=color("subtext"), font=font(10))
        self._video_empty_lbl.pack(anchor="w")

    def _video_open(self):
        file = filedialog.askopenfilename(
            title="Open Video File",
            filetypes=[("Video files", "*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v"),
                       ("All files", "*.*")],
        )
        if not file:
            return
        if file in self._video_recent:
            self._video_recent.remove(file)
        self._video_recent.insert(0, file)
        self._video_recent = self._video_recent[:10]
        self._video_refresh_recent()
        self._open_vlc_window(os.path.basename(file), file)

    def _video_refresh_recent(self):
        for w in self._video_recent_frame.winfo_children():
            w.destroy()
        if self._video_recent:
            self._video_empty_lbl.pack_forget()
        for path in self._video_recent:
            row = tk.Frame(self._video_recent_frame, bg=color("panel"), pady=8, padx=12, cursor="hand2")
            row.pack(fill="x", pady=(0, 5))
            tk.Label(row, text="▶", bg=color("panel"), fg=color("accent"), font=font(12)).pack(side="left", padx=(0, 10))
            info = tk.Frame(row, bg=color("panel"))
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=os.path.basename(path), bg=color("panel"), fg=color("text"),
                     font=font(10, bold=True), anchor="w").pack(fill="x")
            tk.Label(info, text=path, bg=color("panel"), fg=color("subtext"),
                     font=font(8), anchor="w").pack(fill="x")
            make_button(row, "Play", lambda p=path: self._open_vlc_window(os.path.basename(p), p),
                        primary=True, small=True).pack(side="right")
            for w in [row, info]:
                w.bind("<Button-1>", lambda _e, p=path: self._open_vlc_window(os.path.basename(p), p))


    def tick_player(self):
        try:
            if (self.seek_scale is not None and self.is_playing
                    and not self.is_paused and not self.user_seeking):
                position = self.mp3_current_position()
                if self.song_length and position >= self.song_length - 0.3:
                    self.mp3_next()
                else:
                    if self.song_length:
                        self.seek_var.set(min(position, self.song_length))
                    self.time_label.config(
                        text=f"{format_time(position)} / {format_time(self.song_length)}")
            elif self.time_label is not None and self.current_index < 0:
                self.time_label.config(text="00:00 / 00:00")
        except tk.TclError:
            return
        self.root.after(500, self.tick_player)


# ---------- Run the app ----------
def _start_main_app(_username):
    root = tk.Tk()
    try:
        root.state("zoomed")
    except Exception:
        root.geometry("1200x750")
    root.minsize(960, 620)
    MultiPurposeApp(root)
    root.mainloop()


def _show_patch_notes():
    splash = tk.Tk()
    splash.withdraw()
    try:
        messagebox.showinfo(
            "PATCH NOTES",
            "Version 0.1.0:\n"
            "• New sidebar navigation\n"
            "• Notes page — create, edit, delete notes with colors\n"
            "• Weather page — check weather for any city\n"
            "• Calculator — full keyboard support\n"
            "• Toast notifications\n"
            "• Improved dark/light themes\n"
            "• Quick-action cards on home page\n"
            "• AI chatbot with animated typing indicator",
            parent=splash,
        )
    finally:
        try:
            splash.destroy()
        except Exception:
            pass


def main():
    try:
        import multiprocessing
        multiprocessing.freeze_support()
    except Exception:
        pass
    app_data_folder()
    load_translation_cache()
    db_init()
    _show_patch_notes()
    AuthWindow(on_success=_start_main_app).run()


if __name__ == "__main__":
    main()
