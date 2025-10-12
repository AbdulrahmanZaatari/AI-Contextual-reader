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

import streamlit as st
from PIL import Image
import fitz  # PyMuPDF
from google import genai
from google.genai import types
import io
import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
import threading
import time

st.set_page_config(
    page_title="AI Contextual Reader",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    }
    
    .ai-explanation {
        background: #dbeafe;
        border-left: 4px solid #3b82f6;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
        line-height: 1.8;
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
    }
    
    .history-response {
        background: #f0fdf4;
        border-left: 4px solid #22c55e;
        padding: 1rem;
        border-radius: 8px;
        line-height: 1.8;
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
    
    .reading-progress {
        background: #f0f9ff;
        border-left: 4px solid #0ea5e9;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

BOOK_DIR = Path("books_library")
BOOK_DIR.mkdir(exist_ok=True)
DB_PATH = Path("user_data.db")

def init_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, 
                  password_hash TEXT NOT NULL,
                  created_at TEXT NOT NULL)''')
    
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS book_metadata
                 (username TEXT NOT NULL,
                  original_filename TEXT NOT NULL,
                  display_name TEXT NOT NULL,
                  PRIMARY KEY (username, original_filename))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS bookmarks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  book_name TEXT NOT NULL,
                  page_number INTEGER NOT NULL,
                  note TEXT,
                  created_at TEXT NOT NULL,
                  UNIQUE(username, book_name, page_number))''')
    
    # New table for tracking user's current page in each book
    c.execute('''CREATE TABLE IF NOT EXISTS user_reading_position
                 (username TEXT NOT NULL,
                  book_name TEXT NOT NULL,
                  current_page INTEGER NOT NULL,
                  last_read TEXT NOT NULL,
                  PRIMARY KEY (username, book_name))''')
    
    conn.commit()
    conn.close()

init_database()

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

def get_user_books_dir(username):
    user_dir = BOOK_DIR / username
    user_dir.mkdir(exist_ok=True)
    return user_dir

# New functions for reading position tracking
def save_reading_position(username, book_name, page_number):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    last_read = datetime.now().isoformat()
    c.execute("""INSERT OR REPLACE INTO user_reading_position 
                 (username, book_name, current_page, last_read)
                 VALUES (?, ?, ?, ?)""",
              (username, book_name, page_number, last_read))
    conn.commit()
    conn.close()

def get_reading_position(username, book_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT current_page FROM user_reading_position 
                 WHERE username=? AND book_name=?""",
              (username, book_name))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def get_reading_stats(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT book_name, current_page, last_read FROM user_reading_position 
                 WHERE username=? ORDER BY last_read DESC""",
              (username,))
    stats = c.fetchall()
    conn.close()
    return stats

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

def get_all_book_names(username):
    user_dir = get_user_books_dir(username)
    books = []
    for f in sorted(user_dir.glob("*.pdf")):
        display_name = get_display_name(username, f.name)
        books.append((f.name, display_name))
    return books

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

try:
    API_KEY = st.secrets["google_api_key"]
    client = genai.Client(api_key=API_KEY)
except KeyError:
    st.error("API key not found")
    st.stop()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

def pdf_page_to_image(pdf_path, page_number):
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_number]
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
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
            model='gemini-2.0-flash-exp',
            contents=[prompt, image_part]
        )
        
        return response.text.strip()
    except Exception as e:
        return ""

def extract_page_content(pdf_path, page_number, username="", book_name=""):
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
    def extract():
        extract_page_content(pdf_path, page_number, username, book_name)
    
    thread = threading.Thread(target=extract, daemon=True)
    thread.start()

def get_gemini_explanation_stream(client, text_snippet, prompt_type="explain"):
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
    
    prompt = prompt_templates.get(prompt_type, prompt_templates["explain"])
    
    try:
        response = client.models.generate_content_stream(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
        return response
    except:
        return None

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
if 'page_text' not in st.session_state:
    st.session_state.page_text = ""
if 'page_image' not in st.session_state:
    st.session_state.page_image = None
if 'extraction_method' not in st.session_state:
    st.session_state.extraction_method = ""
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
                    st.session_state.authenticated = True
                    st.session_state.username = username
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

user_dir = get_user_books_dir(st.session_state.username)

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
        st.rerun()

st.markdown("---")

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
            # Load saved reading position
            st.session_state.current_page = get_reading_position(st.session_state.username, selected_book)
            st.session_state.page_text = ""
            st.session_state.page_image = None
            st.session_state.extraction_method = ""
            st.rerun()
        
        with st.expander("Rename"):
            current_name = get_display_name(st.session_state.username, selected_book)
            new_name = st.text_input("Name:", value=current_name, key="rename_input")
            if st.button("Save", use_container_width=True):
                if new_name and new_name != current_name:
                    set_display_name(st.session_state.username, selected_book, new_name)
                    st.success("Updated!")
                    st.rerun()

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
                <li>Fast caching</li>
                <li>Background extraction</li>
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
                <li>Reading progress</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Show reading stats
    st.markdown("---")
    st.markdown("### 📚 Your Reading Activity")
    stats = get_reading_stats(st.session_state.username)
    
    if stats:
        for book_name, page_num, last_read in stats[:5]:
            display = get_display_name(st.session_state.username, book_name)
            last_read_time = last_read[:10] if last_read else "Unknown"
            st.markdown(f"**{display}** • Page {page_num + 1} • Last read: {last_read_time}")
    else:
        st.info("Start reading to see your activity here")

else:
    book_path = user_dir / st.session_state.current_book
    display_name = get_display_name(st.session_state.username, st.session_state.current_book)
    
    try:
        doc = fitz.open(book_path)
        st.session_state.total_pages = len(doc)
        doc.close()
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

    if st.session_state.view_mode == "reader":
        st.markdown(f"<div class='book-title'>📖 {display_name}</div>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("⬅ Previous", disabled=(st.session_state.current_page == 0), use_container_width=True, key="prev_btn"):
                st.session_state.current_page = max(0, st.session_state.current_page - 1)
                save_reading_position(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
                st.session_state.page_image = None
                st.session_state.page_text = ""
                st.rerun()
        
        with col2:
            st.markdown(f"<div class='page-info'>Page {st.session_state.current_page + 1} of {st.session_state.total_pages}</div>", unsafe_allow_html=True)
            
            page_jump = st.number_input(
                "Jump to:", 
                min_value=1, 
                max_value=st.session_state.total_pages, 
                value=st.session_state.current_page + 1, 
                label_visibility="collapsed",
                key="page_jump_input"
            )
            if page_jump - 1 != st.session_state.current_page:
                st.session_state.current_page = page_jump - 1
                save_reading_position(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
                st.session_state.page_image = None
                st.session_state.page_text = ""
                st.rerun()
        
        with col3:
            if st.button("Next ➡", disabled=(st.session_state.current_page >= st.session_state.total_pages - 1), use_container_width=True, key="next_btn"):
                st.session_state.current_page = min(st.session_state.total_pages - 1, st.session_state.current_page + 1)
                save_reading_position(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
                st.session_state.page_image = None
                st.session_state.page_text = ""
                st.rerun()

        is_bm = is_bookmarked(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
        if st.button(f"{'🔖 Remove' if is_bm else '🔖 Add'}", use_container_width=True):
            if is_bm:
                remove_bookmark(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
            else:
                add_bookmark(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
            st.rerun()

        st.markdown("---")

        if not st.session_state.page_image:
            st.session_state.page_image = pdf_page_to_image(book_path, st.session_state.current_page)
        
        if not st.session_state.page_text:
            cached_text, cached_method = get_cached_page(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
            if cached_text:
                st.session_state.page_text = cached_text
                st.session_state.extraction_method = cached_method
            else:
                start_background_extraction(book_path, st.session_state.current_page, st.session_state.username, st.session_state.current_book)

        if st.session_state.page_image:
            col_pdf, col_analysis = st.columns([1, 1])
            
            with col_pdf:
                st.subheader("Page")
                st.image(st.session_state.page_image, use_container_width=True)
                
                if st.session_state.page_text:
                    with st.expander("View Text", expanded=False):
                        st.markdown(f"<div class='extracted-text-area'>{st.session_state.page_text}</div>", unsafe_allow_html=True)
                else:
                    st.info("Extracting text in background...")
                    if st.button("Check for Text", use_container_width=True):
                        cached_text, cached_method = get_cached_page(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
                        if cached_text:
                            st.session_state.page_text = cached_text
                            st.session_state.extraction_method = cached_method
                            st.rerun()
                        else:
                            st.info("Still extracting...")
            
            with col_analysis:
                st.subheader("Analysis")
                
                selected_text = st.text_area(
                    "Paste text:",
                    height=120,
                    placeholder="Paste here...",
                    key="user_text_input"
                )
                
                if selected_text and selected_text.strip():
                    st.markdown(f"<div class='selected-text-box'>{selected_text.strip()[:100]}...</div>", unsafe_allow_html=True)
                    
                    st.markdown("**Actions:**")
                    
                    actions = {
                        "Translate": "translate",
                        "Explain": "explain",
                        "ELI5": "eli5",
                        "Historical": "historical",
                        "Summary": "summary",
                        "Compare": "compare",
                        "Themes": "themes",
                        "Cite": "cite"
                    }
                    
                    cols = st.columns(4)
                    for idx, (name, ptype) in enumerate(actions.items()):
                        with cols[idx % 4]:
                            if st.button(name, use_container_width=True, key=f"btn_{ptype}"):
                                response_stream = get_gemini_explanation_stream(client, selected_text.strip(), ptype)
                                
                                if response_stream:
                                    placeholder = st.empty()
                                    full_response = ""
                                    
                                    for chunk in response_stream:
                                        if hasattr(chunk, 'text'):
                                            full_response += chunk.text
                                            placeholder.markdown(f"<div class='ai-explanation'><strong>{name}:</strong><br><br>{full_response}</div>", unsafe_allow_html=True)
                                    
                                    save_to_history(
                                        st.session_state.username,
                                        st.session_state.current_book,
                                        st.session_state.current_page,
                                        name, name, full_response,
                                        selected_text.strip()
                                    )
                                    st.success("Saved!")
                    
                    st.markdown("---")
                    st.markdown("**Custom Question:**")
                    
                    custom_q = st.text_input("Ask:", key="custom_q")
                    
                    if st.button("Answer", disabled=not custom_q, use_container_width=True):
                        try:
                            prompt = f"Text: '{selected_text.strip()}'\n\nQuestion: {custom_q}\n\nAnswer:"
                            
                            response_stream = client.models.generate_content_stream(
                                model='gemini-2.0-flash-exp',
                                contents=prompt
                            )
                            
                            placeholder = st.empty()
                            full_response = ""
                            
                            for chunk in response_stream:
                                if hasattr(chunk, 'text'):
                                    full_response += chunk.text
                                    placeholder.markdown(f"<div class='ai-explanation'><strong>Answer:</strong><br><br>{full_response}</div>", unsafe_allow_html=True)
                            
                            save_to_history(
                                st.session_state.username,
                                st.session_state.current_book,
                                st.session_state.current_page,
                                "Custom Question",
                                custom_q, full_response,
                                selected_text.strip()
                            )
                            st.success("Saved!")
                        except Exception as e:
                            st.error(f"Error: {e}")

    elif st.session_state.view_mode == "bookmarks":
        st.markdown(f"<div class='book-title'>Bookmarks: {display_name}</div>", unsafe_allow_html=True)
        
        bookmarks = get_bookmarks(st.session_state.username, st.session_state.current_book)
        
        if bookmarks:
            st.info(f"{len(bookmarks)} bookmarks")
            st.markdown("---")
            
            for page_num, note, created_at in bookmarks:
                col_b1, col_b2, col_b3 = st.columns([3, 1, 1])
                
                with col_b1:
                    st.markdown(f"<span class='page-badge'>Page {page_num + 1}</span> <span class='timestamp-badge'>{created_at[:16]}</span>", unsafe_allow_html=True)
                
                with col_b2:
                    if st.button("View", key=f"view_bm_{page_num}_{created_at}", use_container_width=True):
                        st.session_state.current_page = page_num
                        save_reading_position(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
                        st.session_state.view_mode = "reader"
                        st.session_state.page_image = None
                        st.session_state.page_text = ""
                        st.rerun()
                
                with col_b3:
                    if st.button("Remove", key=f"remove_bm_{page_num}_{created_at}", use_container_width=True):
                        remove_bookmark(st.session_state.username, st.session_state.current_book, page_num)
                        st.rerun()
                
                st.markdown("---")
        else:
            st.info("No bookmarks yet")

    elif st.session_state.view_mode == "history":
        st.markdown(f"<div class='book-title'>History: {display_name}</div>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            md_export = export_book_history_to_markdown(st.session_state.username, st.session_state.current_book)
            st.download_button("Export MD", md_export, file_name=f"{display_name}.md", mime="text/markdown", use_container_width=True)
        
        with col2:
            history_data = get_book_history(st.session_state.username, st.session_state.current_book)
            json_data = {
                "book": display_name,
                "total": len(history_data),
                "exported": datetime.now().isoformat(),
                "history": [{"page": p + 1, "type": pt, "question": q, "answer": a, "text": t, "time": ts}
                    for _, p, pt, q, a, t, ts in history_data]
            }
            st.download_button("Export JSON", json.dumps(json_data, ensure_ascii=False, indent=2), 
                             file_name=f"{display_name}.json", mime="application/json", use_container_width=True)
        
        with col3:
            if st.button("Clear", use_container_width=True):
                if st.session_state.get('confirm_clear'):
                    clear_book_history(st.session_state.username, st.session_state.current_book)
                    st.session_state.confirm_clear = False
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
                    if st.button(f"Go to Page {page_num + 1}", key=f"goto_{item_id}", use_container_width=True):
                        st.session_state.current_page = page_num
                        save_reading_position(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
                        st.session_state.view_mode = "reader"
                        st.session_state.page_image = None
                        st.session_state.page_text = ""
                        st.rerun()
                
                with col_a2:
                    if st.button(f"Delete", key=f"del_{item_id}", use_container_width=True):
                        delete_history_item(item_id)
                        st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.info("No history")

st.markdown("---")
st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.9rem;'>Built with Gemini 2.0</div>", unsafe_allow_html=True)