import os
from pathlib import Path

# Use Streamlit's persistent storage
if "STREAMLIT_SCRIPT_RUN_CONTEXT" in os.environ:
    # Running on Streamlit Cloud
    DATA_DIR = Path.home() / ".streamlit_data"
else:
    # Running locally
    DATA_DIR = Path(".")

DATA_DIR.mkdir(exist_ok=True)

# Update these paths
BOOK_DIR = DATA_DIR / "books_library"
BOOK_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "user_data.db"

# --- 1. IMPORTS AND CONFIGURATION ---
import streamlit as st
from PIL import Image
import fitz  # PyMuPDF
from google import genai
from google.genai import types
import io
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time

# --- INITIAL PAGE CONFIG ---
st.set_page_config(
    page_title="AI Contextual Reader",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS FOR BETTER UI ---
st.markdown("""
<style>
    .main {
        padding: 1rem;
    }
    
    .book-title {
        font-size: 1.8rem;
        font-weight: 600;
        color: #1e3a8a;
        margin-bottom: 1rem;
    }
    
    .page-info {
        font-size: 1.1rem;
        color: #475569;
        text-align: center;
        padding: 0.5rem;
        background: #f1f5f9;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .stButton button {
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    .selected-text-box {
    background: #fef3c7;
    border-left: 4px solid #f59e0b;
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
    font-family: 'Traditional Arabic', 'Simplified Arabic', 'Segoe UI', sans-serif;
    font-size: 1.3rem;
    direction: rtl;
    line-height: 2.2;
    white-space: pre-wrap;
    text-align: right;
    color: #4a5568;
}
 
.ai-explanation {
    background: #dbeafe;
    border-left: 4px solid #3b82f6;
    padding: 1.5rem;
    border-radius: 8px;
    margin: 1rem 0;
    line-height: 1.8;
    color: #1e293b;
}
    
    .history-chat-item {
        background: white;
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .history-prompt {
        background: #f0f9ff;
        border-left: 4px solid #0ea5e9;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        font-weight: 600;
        color: #0c4a6e;
    }
    
    .history-text {
    background: #fef3c7;
    border-left: 4px solid #f59e0b;
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    font-family: 'Traditional Arabic', 'Simplified Arabic', 'Segoe UI', sans-serif;
    direction: rtl;
    text-align: right;
    max-height: 200px;
    overflow-y: auto;
    color: #4a5568; 
}
    
  .history-response {
    background: #f0fdf4;
    border-left: 4px solid #22c55e;
    padding: 1rem;
    border-radius: 8px;
    line-height: 1.8;
    color: #1e293b; 
}
    
    .page-badge {
        display: inline-block;
        background: #8b5cf6;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .timestamp-badge {
        display: inline-block;
        background: #64748b;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.75rem;
        margin-left: 0.5rem;
    }
    
   .info-box {
    background: #f0fdf4;
    border-left: 4px solid #22c55e;
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
    color: #166534; 
}
    
    .feature-card {
        background: white;
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .feature-card h4 {
        color: #1e3a8a;
        margin-bottom: 0.5rem;
    }
    
    .extracted-text-area {
        background: white;
        border: 2px solid #e2e8f0;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        font-family: 'Traditional Arabic', 'Simplified Arabic', 'Segoe UI', sans-serif;
        font-size: 1.2rem;
        line-height: 2.2;
        direction: rtl;
        text-align: right;
        max-height: 500px;
        overflow-y: auto;
        user-select: text;
        cursor: text;
        white-space: pre-wrap;
        word-wrap: break-word;
        -webkit-user-select: text;
        -moz-user-select: text;
        -ms-user-select: text;
        color: #334155;
    }
    
    .context-badge {
        background: #818cf8;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        display: inline-block;
        margin: 0.5rem 0;
    }
    
    .tip-box {
    background: #fef3c7;
    border: 2px solid #fbbf24;
    border-radius: 8px;
    padding: 1rem;
    margin: 1rem 0;
    color: #78350f;
}
    
    .page-number-label {
        text-align: center;
        font-size: 0.9rem;
        color: #64748b;
        font-weight: 600;
        margin: 0.5rem 0;
        background: #f1f5f9;
        padding: 0.25rem;
        border-radius: 4px;
    }
    
    .multi-page-scroll {
        display: flex;
        overflow-x: auto;
        gap: 15px;
        padding: 15px;
        background: #f8fafc;
        border-radius: 12px;
        margin: 1rem 0;
    }
    
    .page-card {
        flex: 0 0 auto;
        width: 300px;
        border: 2px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .page-card img {
        width: 100%;
        border-radius: 4px;
    }
    
    .bookmark-badge {
        background: #fbbf24;
        color: #78350f;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        display: inline-block;
        margin: 0.25rem;
        cursor: pointer;
    }
    
    .extraction-status {
        background: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-size: 0.85rem;
        color: #78350f;
        display: inline-block;
        margin: 0.5rem 0;
    }
    
    /* Responsive Design */
    @media (max-width: 1024px) {
        .main {
            padding: 0.5rem;
        }
        
        .book-title {
            font-size: 1.4rem;
        }
        
        .extracted-text-area {
            font-size: 1.1rem;
            line-height: 2;
        }
    }
    
    @media (max-width: 768px) {
        .book-title {
            font-size: 1.2rem;
        }
        
        .page-info {
            font-size: 0.95rem;
        }
        
        .extracted-text-area {
            font-size: 1rem;
            line-height: 1.8;
            padding: 1rem;
        }
        
        .selected-text-box {
            font-size: 1.1rem;
            line-height: 1.9;
        }
        
        .ai-explanation {
            font-size: 0.95rem;
            padding: 1rem;
        }
        
        .feature-card {
            padding: 1rem;
        }
    }
    
    @media (max-width: 480px) {
        .book-title {
            font-size: 1rem;
        }
        
        .extracted-text-area {
            font-size: 0.95rem;
            line-height: 1.7;
            padding: 0.75rem;
        }
        
        .selected-text-box {
            font-size: 1rem;
            line-height: 1.8;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- PATHS AND DIRECTORIES ---
BOOK_DIR = Path("books_library")
BOOK_DIR.mkdir(exist_ok=True)
DB_PATH = Path("user_data.db")

# --- DATABASE SETUP ---
def init_database():
    try:
        conn = sqlite3.connect(DB_PATH)
    except NameError:
        print("Error: DB_PATH is not defined. Using 'temp.db' for demonstration.")
        conn = sqlite3.connect('temp.db')
        
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, 
                  password_hash TEXT NOT NULL,
                  created_at TEXT NOT NULL)''')
    
    c.execute("PRAGMA table_info(sessions)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'sessions' not in [table[0] for table in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        c.execute('''CREATE TABLE sessions
                     (username TEXT PRIMARY KEY,
                      token TEXT UNIQUE,
                      created_at TEXT NOT NULL,
                      expires_at TEXT NOT NULL)''')
    
    c.execute("PRAGMA table_info(page_history)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'page_history' not in [table[0] for table in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        c.execute('''CREATE TABLE page_history
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT NOT NULL,
                      book_name TEXT NOT NULL,
                      page_number INTEGER NOT NULL,
                      prompt_type TEXT NOT NULL,
                      question TEXT NOT NULL,
                      answer TEXT NOT NULL,
                      text_snippet TEXT,
                      timestamp TEXT NOT NULL,
                      FOREIGN KEY (username) REFERENCES users(username))''')
    elif 'prompt_type' not in columns:
        c.execute('''CREATE TABLE page_history_new
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT NOT NULL,
                      book_name TEXT NOT NULL,
                      page_number INTEGER NOT NULL,
                      prompt_type TEXT NOT NULL DEFAULT 'Custom Question',
                      question TEXT NOT NULL,
                      answer TEXT NOT NULL,
                      text_snippet TEXT,
                      timestamp TEXT NOT NULL,
                      FOREIGN KEY (username) REFERENCES users(username))''')
        
        c.execute('''INSERT INTO page_history_new (id, username, book_name, page_number, prompt_type, question, answer, text_snippet, timestamp)
                      SELECT id, username, book_name, page_number, 'Custom Question', question, answer, text_snippet, timestamp 
                      FROM page_history''')
        
        c.execute('DROP TABLE page_history')
        c.execute('ALTER TABLE page_history_new RENAME TO page_history')
    
    c.execute('''CREATE TABLE IF NOT EXISTS page_cache
                 (username TEXT NOT NULL,
                  book_name TEXT NOT NULL,
                  page_number INTEGER NOT NULL,
                  extracted_text TEXT,
                  extraction_method TEXT,
                  cached_at TEXT NOT NULL,
                  PRIMARY KEY (username, book_name, page_number))''')
    
    try:
        c.execute("PRAGMA table_info(book_metadata)")
        book_metadata_columns = [column[1] for column in c.fetchall()]
        
        if book_metadata_columns and 'last_page' not in book_metadata_columns:
            c.execute("ALTER TABLE book_metadata ADD COLUMN last_page INTEGER DEFAULT 0")
            print("MIGRATION SUCCESS: Added 'last_page' column to 'book_metadata' table.")
            
    except sqlite3.OperationalError:
        pass 

    c.execute('''CREATE TABLE IF NOT EXISTS book_metadata
                 (username TEXT NOT NULL,
                  original_filename TEXT NOT NULL,
                  display_name TEXT NOT NULL,
                  last_page INTEGER DEFAULT 0,
                  PRIMARY KEY (username, original_filename))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS bookmarks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  book_name TEXT NOT NULL,
                  page_number INTEGER NOT NULL,
                  note TEXT,
                  created_at TEXT NOT NULL,
                  UNIQUE(username, book_name, page_number))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS custom_prompts
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            prompt_name TEXT NOT NULL,
            prompt_template TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(username, prompt_name))''')
    
    conn.commit()
    conn.close()

init_database()

def get_db_connection():
    """Returns an active SQLite connection object."""
    # This function is crucial to define and use consistently.
    return sqlite3.connect(DB_PATH)

# --- SESSION MANAGEMENT ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        password_hash = hash_password(password)
        created_at = datetime.now().isoformat()
        c.execute("INSERT INTO users VALUES (?, ?, ?)", (username, password_hash, created_at))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def verify_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    password_hash = hash_password(password)
    c.execute("SELECT * FROM users WHERE username=? AND password_hash=?", (username, password_hash))
    user = c.fetchone()
    conn.close()
    return user is not None

def create_session(username):
    import secrets
    token = secrets.token_hex(32)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    created_at = datetime.now()
    expires_at = created_at + timedelta(hours=24)
    c.execute("INSERT OR REPLACE INTO sessions (username, token, created_at, expires_at) VALUES (?, ?, ?, ?)",
              (username, token, created_at.isoformat(), expires_at.isoformat()))
    conn.commit()
    conn.close()
    return token

def verify_session(token):
    if not token:
        return None
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, expires_at FROM sessions WHERE token=?", (token,))
    result = c.fetchone()
    conn.close()
    
    if result:
        username, expires_at = result
        if datetime.fromisoformat(expires_at) > datetime.now():
            return username
        else:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM sessions WHERE token=?", (token,))
            conn.commit()
            conn.close()
    
    return None

def get_user_books_dir(username):
    user_dir = BOOK_DIR / username
    user_dir.mkdir(exist_ok=True)
    return user_dir

# --- BOOKMARK FUNCTIONS ---
def add_bookmark(username, book_name, page_number, note=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO bookmarks (username, book_name, page_number, note, created_at) VALUES (?, ?, ?, ?, ?)",
                  (username, book_name, page_number, note, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def remove_bookmark(username, book_name, page_number):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM bookmarks WHERE username=? AND book_name=? AND page_number=?",
              (username, book_name, page_number))
    conn.commit()
    conn.close()

def get_bookmarks(username, book_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT page_number, note, created_at FROM bookmarks WHERE username=? AND book_name=? ORDER BY page_number",
              (username, book_name))
    bookmarks = c.fetchall()
    conn.close()
    return bookmarks

def is_bookmarked(username, book_name, page_number):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM bookmarks WHERE username=? AND book_name=? AND page_number=?",
              (username, book_name, page_number))
    result = c.fetchone()
    conn.close()
    return result is not None

def save_custom_prompt(username, name, template):
    """Saves a new custom prompt to the database."""
    conn = get_db_connection()
    c = conn.cursor()
    created_at = datetime.now().isoformat()
    
    try:
        c.execute('''INSERT INTO custom_prompts 
                     (username, prompt_name, prompt_template, created_at) 
                     VALUES (?, ?, ?, ?)''', 
                  (username, name.strip(), template.strip(), created_at))
        conn.commit()
        return (True, f"Prompt '{name}' saved successfully!")
    except sqlite3.IntegrityError:
        return (False, f"Error: A prompt named '{name}' already exists.")
    except Exception as e:
        return (False, f"Database Error: {e}")
    finally:
        conn.close()

def get_custom_prompts(username):
    """Retrieves all custom prompts for a user."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT id, prompt_name, prompt_template 
                 FROM custom_prompts 
                 WHERE username = ? 
                 ORDER BY created_at DESC''', (username,))
    prompts = c.fetchall()
    conn.close()
    # Returns list of tuples: [(id, name, template), ...]
    return prompts

def delete_custom_prompt(prompt_id):
    """Deletes a custom prompt by its ID."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM custom_prompts WHERE id = ?', (prompt_id,))
    conn.commit()
    conn.close()

# --- MODIFIED UTILITY FUNCTION to combine fixed and custom prompts ---

def get_all_prompts(username):
    """Combines hardcoded actions and user's custom prompts."""
    # 1. Base set of quick actions (type is the prompt_key)
    base_actions = {
        "Translate": "translate",
        "Explain": "explain",
        "ELI5": "eli5",
        "Historical": "historical",
        "Summary": "summary",
        "Compare": "compare",
        "Themes": "themes",
        "Cite": "cite"
    }
    
    # 2. Get custom prompts and add them
    custom_prompts = get_custom_prompts(username) 
    
    # Custom prompts use their name as the key, and their ID as the value/type
    # The generation logic will use this ID to look up the template later.
    for prompt_id, name, _ in custom_prompts:
        base_actions[name] = f"custom_{prompt_id}"
        
    return base_actions

# --- BOOK METADATA ---
def get_display_name(username, filename):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT display_name FROM book_metadata WHERE username=? AND original_filename=?", 
              (username, filename))
    result = c.fetchone()
    conn.close()
    return result[0] if result else filename

def set_display_name(username, filename, display_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO book_metadata (username, original_filename, display_name) VALUES (?, ?, ?)",
              (username, filename, display_name))
    conn.commit()
    conn.close()

def save_last_page(username, filename, page_number):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE book_metadata SET last_page=? WHERE username=? AND original_filename=?",
              (page_number, username, filename))
    conn.commit()
    conn.close()

def get_last_page(username, filename):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT last_page FROM book_metadata WHERE username=? AND original_filename=?",
              (username, filename))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def get_all_book_names(username):
    user_dir = get_user_books_dir(username)
    books = []
    for f in sorted(user_dir.glob("*.pdf")):
        display_name = get_display_name(username, f.name)
        books.append((f.name, display_name))
    return books

# --- HISTORY MANAGEMENT ---
def save_to_history(username, book_name, page_number, prompt_type, question, answer, text_snippet=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute("""INSERT INTO page_history 
                 (username, book_name, page_number, prompt_type, question, answer, text_snippet, timestamp)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
              (username, book_name, page_number, prompt_type, question, answer, text_snippet, timestamp))
    conn.commit()
    conn.close()

def get_book_history(username, book_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT id, page_number, prompt_type, question, answer, text_snippet, timestamp 
                 FROM page_history 
                 WHERE username=? AND book_name=?
                 ORDER BY timestamp DESC""",
              (username, book_name))
    history = c.fetchall()
    conn.close()
    return history

def delete_history_item(item_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM page_history WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

def clear_book_history(username, book_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM page_history WHERE username=? AND book_name=?",
              (username, book_name))
    conn.commit()
    conn.close()

def export_book_history_to_markdown(username, book_name):
    history = get_book_history(username, book_name)
    md_content = f"# Q&A History: {get_display_name(username, book_name)}\n\n"
    md_content += f"*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n---\n\n"
    
    for item_id, page_num, prompt_type, question, answer, text_snippet, timestamp in history:
        md_content += f"## Page {page_num + 1} | {prompt_type}\n\n"
        md_content += f"**Timestamp:** {timestamp}\n\n"
        if text_snippet:
            md_content += f"**Analyzed Text:**\n> {text_snippet}\n\n"
        md_content += f"**Prompt:** {question}\n\n"
        md_content += f"**Response:**\n{answer}\n\n---\n\n"
    
    return md_content

# --- PAGE CACHING ---
def get_cached_page(username, book_name, page_number):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT extracted_text, extraction_method 
                 FROM page_cache 
                 WHERE username=? AND book_name=? AND page_number=?""",
              (username, book_name, page_number))
    result = c.fetchone()
    conn.close()
    return result if result else (None, None)

def cache_page(username, book_name, page_number, extracted_text, extraction_method):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cached_at = datetime.now().isoformat()
    c.execute("""INSERT OR REPLACE INTO page_cache 
                 (username, book_name, page_number, extracted_text, extraction_method, cached_at)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (username, book_name, page_number, extracted_text, extraction_method, cached_at))
    conn.commit()
    conn.close()

# --- GEMINI API ---
try:
    API_KEY = st.secrets["gemini_api_key"]
    client = genai.Client(api_key=API_KEY)
except KeyError:
    st.error("API key not found")
    st.stop()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# --- HELPER FUNCTIONS ---
def pdf_page_to_image(pdf_path, page_number):
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_number]
        pix = page.get_pixmap(alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        return img
    except Exception as e:
        return None

def extract_text_with_gemini_vision(image, client):
    try:
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=95)
        img_bytes = img_byte_arr.getvalue()
        
        image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
        
        prompt = """Extract ALL text EXACTLY as it appears.
- Preserve formatting
- Keep original language
- Maintain RTL for Arabic
- Return raw text only

Text:"""
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, image_part]
        )
        
        return response.text.strip()
    except Exception as e:
        return ""

def extract_page_content_async(pdf_path, page_number, username="", book_name=""):
    """Background text extraction - non-blocking"""
    if username and book_name:
        cached_text, cached_method = get_cached_page(username, book_name, page_number)
        if cached_text:
            return cached_text, cached_method, True
    
    image = pdf_page_to_image(pdf_path, page_number)
    
    if not image:
        return "", "Error", False
    
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_number]
        direct_text = page.get_text("text").strip()
        doc.close()
        
        if direct_text and len(direct_text) > 100:
            if username and book_name:
                cache_page(username, book_name, page_number, direct_text, "Direct PDF")
            return direct_text, "Direct PDF", False
    except:
        pass
    
    text = extract_text_with_gemini_vision(image, client)
    
    if username and book_name and text:
        cache_page(username, book_name, page_number, text, "Gemini Vision")
    
    return text, "Gemini Vision", False

def start_background_extraction(pdf_path, page_number, username, book_name):
    """Start extraction in background thread"""
    def extract():
        extract_page_content_async(pdf_path, page_number, username, book_name)
    
    thread = threading.Thread(target=extract, daemon=True)
    thread.start()

def preload_adjacent_pages(pdf_path, current_page, total_pages, username, book_name):
    """Preload next and previous pages"""
    if current_page + 1 < total_pages:
        start_background_extraction(pdf_path, current_page + 1, username, book_name)
    if current_page - 1 >= 0:
        start_background_extraction(pdf_path, current_page - 1, username, book_name)

def get_extraction_status(username, book_name, page_number):
    """Check if text is being extracted or cached"""
    cached_text, cached_method = get_cached_page(username, book_name, page_number)
    if cached_text:
        return "cached", cached_method
    return "extracting", None

# NEW FUNCTION (get_gemini_explanation_stream)
def get_gemini_explanation_stream(client, text_snippet, prompt_value="explain"):
    """
    Generates a streaming response from the Gemini API, supporting both 
    static keys and custom prompt IDs.
    """
    
    # 1. Static Prompt Templates
    prompt_templates = {
        "translate": f"Translate to English and explain.\n\nText: {text_snippet}",
        "explain": f"Analyze and explain clearly.\n\nText: {text_snippet}",
        "eli5": f"Explain simply (ELI5).\n\nText: {text_snippet}",
        "historical": f"Historical and cultural context.\n\nText: {text_snippet}",
        "summary": f"Brief summary.\n\nText: {text_snippet}",
        "compare": f"Compare and contrast themes.\n\nText: {text_snippet}",
        "themes": f"Extract main themes.\n\nText: {text_snippet}",
        "cite": f"Citation-worthy insights.\n\nText: {text_snippet}"
    }
    
    prompt = None
    
    # A. Handle Custom Prompts (Key is "custom_ID")
    if isinstance(prompt_value, str) and prompt_value.startswith("custom_"):
        try:
            prompt_id = int(prompt_value.split("_")[1])
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            # Retrieve the template from the database
            c.execute("SELECT prompt_template FROM custom_prompts WHERE id=?", (prompt_id,))
            result = c.fetchone()
            conn.close()
            
            if result:
                # Inject the text snippet into the custom template using the placeholder
                prompt_template = result[0]
                prompt = prompt_template.replace("{{text_snippet}}", text_snippet).strip()
                
        except Exception as e:
            # Fallback for corrupted custom ID
            print(f"Error retrieving custom prompt: {e}")
            prompt = prompt_templates["explain"]
            
    # B. Handle Static Prompts (Key is "explain", "eli5", etc.)
    elif prompt_value in prompt_templates:
        prompt = prompt_templates[prompt_value]
        
    # C. Handle Custom Question (The actual question text)
    else:
        # If prompt_value is the actual question text typed by the user
        prompt = f"{prompt_value}\n\nText to analyze:\n{text_snippet}"
        
    # Final check: Fallback if everything fails
    if not prompt:
        prompt = prompt_templates["explain"]
    
    try:
        response = client.models.generate_content_stream(
            model='gemini-2.5-flash',
            contents=prompt
        )
        # For history saving, we return the final constructed prompt and the response stream
        return prompt, response
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return prompt, None
    
def handle_page_jump():
    """Callback to handle page changes from the number_input widget."""
    new_page = st.session_state.page_jump_input - 1
    if new_page != st.session_state.current_page:
        st.session_state.current_page = new_page
        save_last_page(st.session_state.username, st.session_state.current_book, new_page)
        st.session_state.page_image = None


# --- SESSION STATE ---
if 'session_token' not in st.session_state:
    st.session_state.session_token = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'current_book' not in st.session_state:
    st.session_state.current_book = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'total_pages' not in st.session_state:
    st.session_state.total_pages = 0
if 'page_image' not in st.session_state:
    st.session_state.page_image = None
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "reader"
if 'multi_page_mode' not in st.session_state:
    st.session_state.multi_page_mode = False
if 'selected_pages' not in st.session_state:
    st.session_state.selected_pages = []
if 'context_text' not in st.session_state:
    st.session_state.context_text = ""
if 'multi_page_images' not in st.session_state:
    st.session_state.multi_page_images = []
if 'pdf_doc' not in st.session_state:
    st.session_state.pdf_doc = None

# --- CHECK SESSION ON APP START ---
if not st.session_state.authenticated:
    token = st.query_params.get('session_token')
    if token:
        username = verify_session(token)
        if username:
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.session_token = token

# --- LOGIN UI ---
if not st.session_state.authenticated:
    st.title("AI Contextual Reader")
    st.markdown("### Welcome!")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if verify_user(username, password):
                    token = create_session(username)
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.session_token = token
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    
    with tab2:
        with st.form("signup_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            signup = st.form_submit_button("Create Account", use_container_width=True)
            
            if signup:
                if len(new_username) < 3:
                    st.error("Username must be at least 3 characters")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                elif new_password != confirm_password:
                    st.error("Passwords don't match")
                else:
                    if create_user(new_username, new_password):
                        st.success("Account created! Please login.")
                    else:
                        st.error("Username already exists")
    
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.9rem;'>Built with Gemini 2.0</div>", unsafe_allow_html=True)
    st.stop()

# --- MAIN APP ---
user_dir = get_user_books_dir(st.session_state.username)

st.components.v1.html("""
<script>
    let touchStartX = 0;
    let touchEndX = 0;
    const threshold = 80; // Swipe distance threshold in pixels
    
    function handleSwipe() {
        const diff = touchStartX - touchEndX;
        if (Math.abs(diff) > threshold) {
            // Must target the buttons in the parent (Streamlit main app) document
            const buttons = window.parent.document.querySelectorAll('button');
            
            if (diff > 0) { // Swiped left: Go to Next Page
                for (let btn of buttons) {
                    // Check button text and if it's not disabled
                    if (btn.textContent === 'Next ▶' && !btn.disabled) {
                        btn.click();
                        break;
                    }
                }
            } else { // Swiped right: Go to Previous Page
                for (let btn of buttons) {
                    // Check button text and if it's not disabled
                    if (btn.textContent === '◀ Previous' && !btn.disabled) {
                        btn.click();
                        break;
                    }
                }
            }
        }
    }

    // --- Key Change: Attach listeners to the parent window's document ---
    // The current script runs inside an iframe, so we listen on the parent.
    window.parent.document.addEventListener('touchstart', e => {
        // Only track single touches for swipe
        if (e.touches.length === 1) {
            touchStartX = e.touches[0].screenX;
        }
    }, {passive: true});

    window.parent.document.addEventListener('touchend', e => {
        if (e.changedTouches.length === 1) {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
        }
    }, {passive: true});

    // Existing Keyboard Logic (already working correctly by using window.parent.document)
    window.parent.document.addEventListener('keydown', function(e) {
        // ... (your existing ArrowKey logic) ...
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }

        const buttons = window.parent.document.querySelectorAll('button');
        if (e.key === "ArrowRight") {
            for (let btn of buttons) {
                if (btn.textContent === 'Next ▶' && !btn.disabled) {
                    btn.click();
                    break;
                }
            }
        } else if (e.key === "ArrowLeft") {
            for (let btn of buttons) {
                if (btn.textContent === '◀ Previous' && !btn.disabled) {
                    btn.click();
                    break;
                }
            }
        }
    });
</script>
""", height=0)

# --- TOP BAR ---
col1, col2, col3 = st.columns([2, 3, 1])

with col1:
    st.markdown(f"### {st.session_state.username}")

with col2:
    if st.session_state.current_book:
        view_mode = st.radio(
            "View:",
            ["Reader", "History", "Bookmarks"],
            horizontal=True,
            key="view_mode_selector"
        )
        if "Reader" in view_mode:
            st.session_state.view_mode = "reader"
        elif "History" in view_mode:
            st.session_state.view_mode = "history"
        else:
            st.session_state.view_mode = "bookmarks"

with col3:
    if st.button("Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.session_token = None
        st.rerun()

st.markdown("---")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Books")

    uploaded_file = st.file_uploader("Upload", type="pdf")
    if uploaded_file:
        file_path = user_dir / uploaded_file.name
        if not file_path.exists():
            with st.spinner("Saving..."):
                file_path.write_bytes(uploaded_file.getvalue())
                set_display_name(st.session_state.username, uploaded_file.name, uploaded_file.name)
            st.success("Added!")
            st.rerun()
        else:
            st.info("Already exists")

    st.markdown("---")

    books = get_all_book_names(st.session_state.username)
    if not books:
        st.info("Upload PDF")
    else:
        book_options = [display_name for _, display_name in books]
        selected_display = st.selectbox("Select:", book_options)
        
        selected_book = next(filename for filename, display in books if display == selected_display)
        
        if selected_book != st.session_state.current_book:
            st.session_state.current_book = selected_book
            last_page = get_last_page(st.session_state.username, selected_book)
            st.session_state.current_page = last_page
            st.session_state.page_image = None
            st.session_state.multi_page_mode = False
            st.session_state.selected_pages = []
            st.session_state.context_text = ""
            st.session_state.multi_page_images = []
            st.session_state.pdf_doc = None
            st.rerun()
        
        with st.expander("Rename"):
            current_name = get_display_name(st.session_state.username, selected_book)
            new_name = st.text_input("Name:", value=current_name, key="rename_input")
            if st.button("Save", use_container_width=True):
                if new_name and new_name != current_name:
                    set_display_name(st.session_state.username, selected_book, new_name)
                    st.success("Updated!")
                    st.rerun()

    st.markdown("---")
    st.header("Settings")
    
    if st.session_state.current_book:
        st.markdown("---")
        
        st.subheader("Multi-Page")
        multi_page_enabled = st.checkbox(
            "Enable",
            value=st.session_state.multi_page_mode,
            help="Max 5 pages"
        )
        
        if multi_page_enabled != st.session_state.multi_page_mode:
            st.session_state.multi_page_mode = multi_page_enabled
            if not multi_page_enabled:
                st.session_state.selected_pages = []
                st.session_state.context_text = ""
                st.session_state.multi_page_images = []
        
        if st.session_state.multi_page_mode:
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                start_page = st.number_input(
                    "Start:", 
                    min_value=1, 
                    max_value=st.session_state.total_pages,
                    value=max(1, st.session_state.current_page + 1),
                    key="start_page_select"
                )
            with col_r2:
                end_page = st.number_input(
                    "End:", 
                    min_value=start_page, 
                    max_value=min(start_page + 4, st.session_state.total_pages),
                    value=min(start_page + 1, st.session_state.total_pages),
                    key="end_page_select"
                )
            
            if st.button("Load", use_container_width=True):
                selected = list(range(start_page - 1, end_page))
                if len(selected) > 5:
                    st.warning("Max 5")
                    selected = selected[:5]
                
                st.session_state.selected_pages = selected
                with st.spinner("Loading..."):
                    book_path = user_dir / st.session_state.current_book
                    contexts = []
                    images = []
                    for page_num in selected:
                        text, _, _ = extract_page_content_async(book_path, page_num, st.session_state.username, st.session_state.current_book)
                        image = pdf_page_to_image(book_path, page_num)
                        if text:
                            contexts.append(f"--- Page {page_num + 1} ---\n{text}")
                        if image:
                            images.append((page_num + 1, image))
                    st.session_state.context_text = "\n\n".join(contexts)
                    st.session_state.multi_page_images = images
                st.success(f"{len(selected)} pages!")
                st.rerun()
            
            if st.session_state.selected_pages:
                pages_list = ', '.join(str(p+1) for p in st.session_state.selected_pages)
                st.success(f"Pages: {pages_list}")
    
    st.markdown("---")
    
    if st.button("Refresh", use_container_width=True):
        st.session_state.page_image = None
        if st.session_state.multi_page_mode:
            st.session_state.context_text = ""
            st.session_state.multi_page_images = []
            st.session_state.selected_pages = []
        st.rerun()

# --- MAIN CONTENT ---
if not st.session_state.current_book:
    st.markdown("""
    <div class='info-box'>
        <h2>Welcome!</h2>
        <p><strong>AI Contextual Reader</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class='feature-card'>
            <h4>Reading</h4>
            <ul>
                <li>Instant page navigation</li>
                <li>Multi-page context</li>
                <li>Fast caching</li>
                <li>Resume reading</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class='feature-card'>
            <h4>AI Analysis</h4>
            <ul>
                <li>Streaming responses</li>
                <li>Multiple analysis types</li>
                <li>Context-aware</li>
                <li>Copy to clipboard</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class='feature-card'>
            <h4>Organization</h4>
            <ul>
                <li>Bookmarks</li>
                <li>Full history</li>
                <li>Export data</li>
                <li>Personal library</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

else:
    book_path = user_dir / st.session_state.current_book
    display_name = get_display_name(st.session_state.username, st.session_state.current_book)
    
    # Load PDF document once
    if st.session_state.pdf_doc is None:
        try:
            st.session_state.pdf_doc = fitz.open(book_path)
            st.session_state.total_pages = len(st.session_state.pdf_doc)
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

    # --- READER MODE ---
    if st.session_state.view_mode == "reader":
        if 'page_jump_input' not in st.session_state:
            st.session_state.page_jump_input = st.session_state.current_page + 1
        elif st.session_state.page_jump_input != st.session_state.current_page + 1:
            st.session_state.page_jump_input = st.session_state.current_page + 1
        st.markdown(f"<div class='book-title'>{display_name}</div>", unsafe_allow_html=True)

        # Top navigation
        col1, col2, col3 = st.columns([1, 2, 1])
    
        with col1:
            if st.button("◀ Previous", disabled=(st.session_state.current_page == 0), use_container_width=True, key="prev_btn_top"):
                st.session_state.current_page -= 1
                save_last_page(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
                st.session_state.page_image = None
                st.rerun()
    
        with col2:
            st.markdown(f"<div class='page-info'>Page {st.session_state.current_page + 1} of {st.session_state.total_pages}</div>", unsafe_allow_html=True)
            page_jump = st.number_input(
                "Jump:", 
                min_value=1, 
                max_value=st.session_state.total_pages, 
                label_visibility="collapsed",
                key="page_jump_input",
                on_change=handle_page_jump
            )

        with col3:
            if st.button("Next ▶", disabled=(st.session_state.current_page >= st.session_state.total_pages - 1), use_container_width=True, key="next_btn_top"):
                st.session_state.current_page += 1
                save_last_page(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
                st.session_state.page_image = None
                st.rerun()

        # Bookmark button
        is_bm = is_bookmarked(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
        if st.button(f"{'🔖 Remove Bookmark' if is_bm else '🔖 Add Bookmark'}", use_container_width=True):
            if is_bm:
                remove_bookmark(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
                st.success("Removed!")
            else:
                add_bookmark(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
                st.success("Bookmarked!")
            time.sleep(0.5)
            st.rerun()

        st.markdown("---")

        # Load image immediately (non-blocking)
        if not st.session_state.page_image:
            st.session_state.page_image = pdf_page_to_image(book_path, st.session_state.current_page)
        
        # Start background text extraction (doesn't block UI)
        start_background_extraction(book_path, st.session_state.current_page, st.session_state.username, st.session_state.current_book)
        
        # Preload adjacent pages in background
        preload_adjacent_pages(book_path, st.session_state.current_page, st.session_state.total_pages, st.session_state.username, st.session_state.current_book)

        if st.session_state.page_image or (st.session_state.multi_page_mode and st.session_state.multi_page_images):
            if st.session_state.multi_page_mode and st.session_state.multi_page_images:
                st.subheader("Pages")
                st.markdown(f"<div class='context-badge'>{len(st.session_state.multi_page_images)} pages</div>", unsafe_allow_html=True)
                
                cols = st.columns(len(st.session_state.multi_page_images))
                for idx, (page_num, img) in enumerate(st.session_state.multi_page_images):
                    with cols[idx]:
                        st.markdown(f"<div class='page-number-label'>Page {page_num}</div>", unsafe_allow_html=True)
                        st.image(img, use_container_width=True)
                
                if st.session_state.context_text:
                    st.markdown("---")
                    st.subheader("Extracted Text")
                    
                    col_t1, col_t2 = st.columns([5, 1])
                    with col_t2:
                        if st.button("📋 Copy All", use_container_width=True, key="copy_multi"):
                            st.code(st.session_state.context_text, language=None)
                            st.success("Ready to copy!")
                    
                    with st.expander("📖 View Text", expanded=False):
                        st.markdown(f"<div class='extracted-text-area'>{st.session_state.context_text}</div>", unsafe_allow_html=True)
                
                st.markdown("---")
                st.subheader("AI Analysis")
                st.info(f"Analyzing {len(st.session_state.selected_pages)} pages")
                
            else:
                col_pdf, col_analysis = st.columns([1, 1])
                
                with col_pdf:
                    st.subheader("Page")
                    st.image(st.session_state.page_image, use_container_width=True)
                    
                    # Check extraction status
                    status, method = get_extraction_status(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
                    
                    if status == "cached":
                        cached_text, _ = get_cached_page(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
                        
                        col_t1, col_t2 = st.columns([5, 1])
                        with col_t2:
                            with st.popover("📋 Copy Text", use_container_width=True, help="Click to view and copy the extracted text."):
                                st.info("The text below is ready to copy! Use the native copy button on the code block.")
                                st.code(cached_text, language=None)
                        
                        with st.expander("📖 View Text", expanded=False):
                            st.markdown(f"<div class='extracted-text-area'>{cached_text}</div>", unsafe_allow_html=True)
                    else:
                        # Show subtle extraction indicator inside expander
                        with st.expander("📖 View Text (Extracting...)", expanded=False):
                            if st.button("🔄 Check Status", use_container_width=True):
                                st.rerun()
                            st.markdown("<div class='extraction-status'>⏳ Text extraction in progress...</div>", unsafe_allow_html=True)
                
                with col_analysis:
                    st.subheader("Analysis")
            
            with col_analysis:
                st.subheader("Analysis")
    
                # --- CUSTOM PROMPT MANAGER TRIGGER & UI (from previous step) ---
                if st.button("🔧 Manage Custom Prompts", use_container_width=True, key="manage_prompts_btn"):
                    # Toggle visibility
                    st.session_state.show_prompt_manager = not st.session_state.get('show_prompt_manager', False)
                    
                # --- NEW: CUSTOM PROMPT MANAGER UI (Placeholders for actual implementation) ---
                if st.session_state.get('show_prompt_manager', False):
                    st.markdown("---")
                    st.subheader("Custom Prompts Editor")

                    # 1. CREATE NEW PROMPT FORM
                    with st.form("new_prompt_form", clear_on_submit=True):
                        st.markdown("#### ➕ Create New Prompt")
                        new_prompt_name = st.text_input("Prompt Name (e.g., 'Summary for Notion')", max_chars=50)
                        new_prompt_template = st.text_area(
                            "Prompt Template",
                            placeholder="Act as a professional technical writer. Summarize the following text into three detailed points. Text: {{text_snippet}}",
                            height=150
                        )
                        submitted = st.form_submit_button("💾 Save Prompt")
                        
                        # --- DATABASE CALLS FOR SAVE ---
                        if submitted and new_prompt_name and new_prompt_template:
                            # Assuming save_custom_prompt is defined in your utilities
                            success, message = save_custom_prompt(
                                st.session_state.username, 
                                new_prompt_name.strip(), 
                                new_prompt_template.strip()
                            )
                            if success:
                                st.success(message)
                            else:
                                st.warning(message)
                            st.rerun() 

                    st.info("Tip: Use `{{text_snippet}}` in your template to mark where the selected text will be inserted.")
                    
                    # 2. VIEW/DELETE PROMPTS LIST
                    st.markdown("#### 🗑️ Your Saved Prompts")
                    # Assuming get_custom_prompts is defined in your utilities
                    custom_prompts_list = get_custom_prompts(st.session_state.username) 
                    
                    if custom_prompts_list:
                        for prompt_id, name, template in custom_prompts_list:
                            col_c1, col_c2 = st.columns([4, 1])
                            with col_c1:
                                with st.expander(f"**{name}**", expanded=False):
                                    st.code(template, language="plaintext")
                            with col_c2:
                                if st.button("Delete", key=f"delete_btn_{prompt_id}", type="secondary", use_container_width=True):
                                    # Assuming delete_custom_prompt is defined in your utilities
                                    delete_custom_prompt(prompt_id) 
                                    st.rerun() 
                    else:
                        st.caption("No custom prompts saved.")
                    st.markdown("---") 
                # --- END CUSTOM PROMPT MANAGER UI ---

                selected_text = st.text_area(
                    "Paste text:",
                    height=120,
                    placeholder="Paste text here to analyze...",
                    key="user_text_input"
                )
                
                use_full_context = False
                if st.session_state.multi_page_mode and st.session_state.context_text:
                    use_full_context = st.checkbox("Use all pages as context", value=True)
                
                if selected_text and selected_text.strip():
                    st.markdown(f"<div class='selected-text-box'>{selected_text.strip()[:100]}...</div>", unsafe_allow_html=True)
                    
                    st.markdown("**Quick Actions & Custom Prompts:**")
                    
                    # Get all actions (built-in and custom from DB)
                    # Assuming get_all_prompts is defined in your utilities
                    actions = get_all_prompts(st.session_state.username) 

                    # Re-fetch custom prompts list to look up template quickly if needed
                    # Assuming get_custom_prompts is defined in your utilities
                    custom_prompts_db = get_custom_prompts(st.session_state.username)
                    custom_prompts_map = {f"custom_{id}": template for id, _, template in custom_prompts_db}

                    cols = st.columns(4)
                    for idx, (name, ptype) in enumerate(actions.items()):
                        with cols[idx % 4]:
                            if st.button(name, use_container_width=True, key=f"btn_{ptype}"):
                                
                                analysis_text = selected_text.strip()
                                
                                # --- CUSTOM PROMPT LOGIC (using database template) ---
                                if ptype.startswith("custom_"):
                                    
                                    prompt_template = custom_prompts_map.get(ptype, "")
                                    
                                    if not prompt_template:
                                        st.error("Error: Custom prompt template not found.")
                                        continue
                                    
                                    # 1. Fill the template with the selected text
                                    template_filled = prompt_template.replace('{{text_snippet}}', analysis_text)
                                    
                                    # 2. Apply multi-page context if enabled
                                    if use_full_context and st.session_state.context_text:
                                        prompt = f"CONTEXT:\n{st.session_state.context_text}\n\nUSER PROMPT:\n{template_filled}"
                                    else:
                                        prompt = template_filled
                                    
                                    # Call Gemini API directly (since this is custom logic)
                                    response_stream = client.models.generate_content_stream(
                                        model='gemini-2.5-flash',
                                        contents=prompt
                                    )
                                    
                                # --- BUILT-IN ACTION LOGIC ---
                                else:
                                    # Use the existing function for built-in actions 
                                    # Assuming get_gemini_explanation_stream is defined elsewhere
                                    response_stream = get_gemini_explanation_stream(client, analysis_text, ptype)

                                # --- STREAMING RESPONSE & HISTORY SAVE ---
                                if response_stream:
                                    placeholder = st.empty()
                                    full_response = ""
                                    
                                    for chunk in response_stream:
                                        if hasattr(chunk, 'text'):
                                            full_response += chunk.text
                                            placeholder.markdown(f"<div class='ai-explanation'><strong>{name}:</strong><br><br>{full_response}</div>", unsafe_allow_html=True)
                                    
                                    # Save to history
                                    # Use the button name for both prompt_type and question for Quick Actions/Custom Prompts
                                    # Assuming save_to_history is defined elsewhere
                                    save_to_history(
                                        st.session_state.username,
                                        st.session_state.current_book,
                                        st.session_state.current_page,
                                        name, name, full_response, 
                                        selected_text.strip()
                                    )
                                    st.success("Saved to history!")
                    
                    st.markdown("---")
                    st.markdown("**Custom Question (Manual):**")
                    
                    custom_q = st.text_input("Ask anything about this text:", key="custom_q")
                    
                    if st.button("Get Answer", disabled=not custom_q, use_container_width=True):
                        try:
                            analysis_text = selected_text.strip()
                            if use_full_context and st.session_state.context_text:
                                prompt = f"CONTEXT:\n{st.session_state.context_text}\n\nFOCUS:\n{analysis_text}\n\nQUESTION: {custom_q}\n\nAnswer:"
                            else:
                                prompt = f"Text: '{analysis_text}'\n\nQuestion: {custom_q}\n\nAnswer:"
                            
                            response_stream = client.models.generate_content_stream(
                                model='gemini-2.5-flash',
                                contents=prompt
                            )
                            
                            placeholder = st.empty()
                            full_response = ""
                            
                            for chunk in response_stream:
                                if hasattr(chunk, 'text'):
                                    full_response += chunk.text
                                    placeholder.markdown(f"<div class='ai-explanation'><strong>Answer:</strong><br><br>{full_response}</div>", unsafe_allow_html=True)
                            
                            # Save to history for the manual question
                            save_to_history(
                                st.session_state.username,
                                st.session_state.current_book,
                                st.session_state.current_page,
                                "Custom Question",
                                custom_q, full_response,
                                selected_text.strip()
                            )
                            st.success("Saved to history!")
                        except Exception as e:
                            st.error(f"Error: {e}")

    # --- BOOKMARKS MODE ---
    elif st.session_state.view_mode == "bookmarks":
        st.markdown(f"<div class='book-title'>🔖 Bookmarks: {display_name}</div>", unsafe_allow_html=True)
        
        bookmarks = get_bookmarks(st.session_state.username, st.session_state.current_book)
        
        if bookmarks:
            st.info(f"{len(bookmarks)} bookmarks")
            st.markdown("---")
            
            for page_num, note, created_at in bookmarks:
                col_b1, col_b2 = st.columns([4, 1])
                
                with col_b1:
                    st.markdown(f"""
                    <div class='bookmark-badge'>
                        📄 Page {page_num + 1} - {created_at[:16]}
                    </div>
                    """, unsafe_allow_html=True)
                    if note:
                        st.caption(f"Note: {note}")
                
                with col_b2:
                    if st.button(f"Go to Page", key=f"goto_bm_{page_num}", use_container_width=True):
                        st.session_state.view_mode = "reader"
                        st.session_state.current_page = page_num
                        save_last_page(st.session_state.username, st.session_state.current_book, page_num)
                        st.session_state.page_image = None
                        st.rerun()
                
                st.markdown("---")
        else:
            st.info("No bookmarks yet")

    # --- HISTORY MODE ---
    elif st.session_state.view_mode == "history":
        st.markdown(f"<div class='book-title'>📚 History: {display_name}</div>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            md_export = export_book_history_to_markdown(st.session_state.username, st.session_state.current_book)
            st.download_button("📄 Export Markdown", md_export, file_name=f"{display_name}.md", mime="text/markdown", use_container_width=True)
        
        with col2:
            history_data = get_book_history(st.session_state.username, st.session_state.current_book)
            json_data = {
                "book": display_name,
                "total": len(history_data),
                "exported": datetime.now().isoformat(),
                "history": [{"page": p + 1, "type": pt, "question": q, "answer": a, "text": t, "time": ts}
                    for _, p, pt, q, a, t, ts in history_data]
            }
            st.download_button("📊 Export JSON", json.dumps(json_data, ensure_ascii=False, indent=2), 
                             file_name=f"{display_name}.json", mime="application/json", use_container_width=True)
        
        with col3:
            if st.button("🗑️ Clear All", use_container_width=True):
                if st.session_state.get('confirm_clear'):
                    clear_book_history(st.session_state.username, st.session_state.current_book)
                    st.session_state.confirm_clear = False
                    st.success("Cleared!")
                    st.rerun()
                else:
                    st.session_state.confirm_clear = True
                    st.warning("Click again to confirm")
        
        st.markdown("---")
        
        history = get_book_history(st.session_state.username, st.session_state.current_book)
        
        if history:
            st.info(f"{len(history)} conversations")
            st.markdown("---")
            
            for item_id, page_num, prompt_type, question, answer, text_snippet, timestamp in history:
                st.markdown(f"""
                <div class='history-chat-item'>
                    <div style='margin-bottom: 1rem;'>
                        <span class='page-badge'>Page {page_num + 1}</span>
                        <span class='timestamp-badge'>{timestamp[:16]}</span>
                    </div>
                    <div class='history-prompt'><strong>{prompt_type}</strong><br>{question}</div>
                """, unsafe_allow_html=True)
                
                if text_snippet:
                    snippet = text_snippet[:300] + "..." if len(text_snippet) > 300 else text_snippet
                    st.markdown(f"<div class='history-text'><strong>Text:</strong><br>{snippet}</div>", unsafe_allow_html=True)
                
                st.markdown(f"<div class='history-response'><strong>Response:</strong><br>{answer}</div>", unsafe_allow_html=True)
                
                col_a1, col_a2 = st.columns([3, 1])
                with col_a1:
                    if st.button(f"📄 Go to Page {page_num + 1}", key=f"goto_{item_id}", use_container_width=True):
                        st.session_state.view_mode = "reader"
                        st.session_state.current_page = page_num
                        save_last_page(st.session_state.username, st.session_state.current_book, page_num)
                        st.session_state.page_image = None
                        st.rerun()
                
                with col_a2:
                    if st.button(f"Delete", key=f"del_{item_id}", use_container_width=True):
                        delete_history_item(item_id)
                        st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.info("No history yet. Start analyzing text to build your history!")

st.markdown("---")
st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.9rem;'>Built with Gemini 2.5 Flash | Swipe to navigate on mobile</div>", unsafe_allow_html=True)