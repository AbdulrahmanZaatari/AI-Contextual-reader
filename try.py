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
from datetime import datetime
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
</style>
""", unsafe_allow_html=True)

# --- PATHS AND DIRECTORIES ---
BOOK_DIR = Path("books_library")
BOOK_DIR.mkdir(exist_ok=True)
DB_PATH = Path("user_data.db")

# --- DATABASE SETUP ---
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
    
    # Bookmarks table
    c.execute('''CREATE TABLE IF NOT EXISTS bookmarks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  book_name TEXT NOT NULL,
                  page_number INTEGER NOT NULL,
                  note TEXT,
                  created_at TEXT NOT NULL,
                  UNIQUE(username, book_name, page_number))''')
    
    conn.commit()
    conn.close()

init_database()

# --- USER AUTHENTICATION ---
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
        md_content += f"## 📄 Page {page_num + 1} | {prompt_type}\n\n"
        md_content += f"**Timestamp:** {timestamp}\n\n"
        if text_snippet:
            md_content += f"**Analyzed Text:**\n> {text_snippet}\n\n"
        md_content += f"**Prompt:** {question}\n\n"
        md_content += f"**Response:**\n{answer}\n\n---\n\n"
    
    return md_content

# --- PAGE CACHING (no zoom dependency) ---
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
    API_KEY = st.secrets["google_api_key"]
    client = genai.Client(api_key=API_KEY)
except KeyError:
    st.error("🔑 API key not found")
    st.stop()
except Exception as e:
    st.error(f"❌ Error: {e}")
    st.stop()

# --- HELPER FUNCTIONS ---
def pdf_page_to_image(pdf_path, page_number, zoom=2.0):
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_number]
        mat = fitz.Matrix(zoom, zoom)
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

def extract_page_content_async(pdf_path, page_number, username="", book_name=""):
    """Extract text in background - separate from display"""
    # Check cache first
    if username and book_name:
        cached_text, cached_method = get_cached_page(username, book_name, page_number)
        if cached_text:
            return cached_text, cached_method, True
    
    # Generate image for OCR at standard quality
    image = pdf_page_to_image(pdf_path, page_number, zoom=2.0)
    
    if not image:
        return "", "Error", False
    
    # Try direct extraction
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
    
    # Use Gemini Vision
    text = extract_text_with_gemini_vision(image, client)
    
    if username and book_name and text:
        cache_page(username, book_name, page_number, text, "Gemini Vision")
    
    return text, "Gemini Vision", False

def extract_multi_page_content(pdf_path, page_numbers, zoom, username="", book_name=""):
    all_texts = []
    all_images = []
    
    for page_num in page_numbers:
        # Get text (cached or extract)
        text, _, _ = extract_page_content_async(pdf_path, page_num, username, book_name)
        # Get image at user's zoom level
        image = pdf_page_to_image(pdf_path, page_num, zoom)
        
        if text:
            all_texts.append(f"--- Page {page_num + 1} ---\n{text}")
        if image:
            all_images.append((page_num + 1, image))
    
    return "\n\n".join(all_texts), all_images

def start_background_extraction(pdf_path, page_number, username, book_name):
    """Start text extraction in background thread"""
    def extract():
        extract_page_content_async(pdf_path, page_number, username, book_name)
    
    thread = threading.Thread(target=extract, daemon=True)
    thread.start()

def preload_adjacent_pages(pdf_path, current_page, total_pages, username, book_name):
    if current_page + 1 < total_pages:
        start_background_extraction(pdf_path, current_page + 1, username, book_name)
    if current_page - 1 >= 0:
        start_background_extraction(pdf_path, current_page - 1, username, book_name)

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

# --- SESSION STATE ---
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
if 'zoom_level' not in st.session_state:
    st.session_state.zoom_level = 2.0
if 'page_text' not in st.session_state:
    st.session_state.page_text = ""
if 'page_image' not in st.session_state:
    st.session_state.page_image = None
if 'extraction_method' not in st.session_state:
    st.session_state.extraction_method = ""
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "reader"
if 'text_loading' not in st.session_state:
    st.session_state.text_loading = False
if 'multi_page_mode' not in st.session_state:
    st.session_state.multi_page_mode = False
if 'selected_pages' not in st.session_state:
    st.session_state.selected_pages = []
if 'context_text' not in st.session_state:
    st.session_state.context_text = ""
if 'multi_page_images' not in st.session_state:
    st.session_state.multi_page_images = []

# --- LOGIN UI ---
if not st.session_state.authenticated:
    st.title("📚 AI Contextual Reader")
    st.markdown("### Welcome!")
    
    tab1, tab2 = st.tabs(["🔐 Login", "✨ Sign Up"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if verify_user(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")
    
    with tab2:
        with st.form("signup_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            signup = st.form_submit_button("Create Account", use_container_width=True)
            
            if signup:
                if len(new_username) < 3:
                    st.error("❌ Username must be at least 3 characters")
                elif len(new_password) < 6:
                    st.error("❌ Password must be at least 6 characters")
                elif new_password != confirm_password:
                    st.error("❌ Passwords don't match")
                else:
                    if create_user(new_username, new_password):
                        st.success("✅ Account created! Please login.")
                    else:
                        st.error("❌ Username already exists")
    
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.9rem;'>Built with ❤️ using Gemini 2.0</div>", unsafe_allow_html=True)
    st.stop()

# --- MAIN APP (Only runs if authenticated) ---
user_dir = get_user_books_dir(st.session_state.username)

# --- Component for keyboard navigation ---
st.components.v1.html("""
<script>
    const handleKeyPress = (e) => {
        const activeEl = document.activeElement;
        const isTyping = activeEl.tagName === 'INPUT' || 
                        activeEl.tagName === 'TEXTAREA' || 
                        activeEl.isContentEditable;
        
        if (!isTyping) {
            if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                e.preventDefault();
                const buttons = window.parent.document.querySelectorAll('button');
                const searchText = e.key === 'ArrowLeft' ? 'Previous' : 'Next';
                
                for (let btn of buttons) {
                    if (btn.textContent.includes(searchText) && !btn.disabled) {
                        btn.click();
                        break;
                    }
                }
            }
        }
    };
    
    window.parent.document.addEventListener('keydown', handleKeyPress);
</script>
""", height=0)

# --- TOP BAR ---
col1, col2, col3 = st.columns([2, 3, 1])

with col1:
    st.markdown(f"### 👤 {st.session_state.username}")

with col2:
    if st.session_state.current_book:
        view_mode = st.radio(
            "View:",
            ["📖 Reader", "💬 History", "🔖 Bookmarks"],
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
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.rerun()

st.markdown("---")

# --- SIDEBAR ---
with st.sidebar:
    st.header("📖 Books")

    uploaded_file = st.file_uploader("Upload", type="pdf")
    if uploaded_file:
        file_path = user_dir / uploaded_file.name
        if not file_path.exists():
            with st.spinner("Saving..."):
                file_path.write_bytes(uploaded_file.getvalue())
                set_display_name(st.session_state.username, uploaded_file.name, uploaded_file.name)
            st.success("✅ Added!")
            st.rerun()
        else:
            st.info("📘 Already exists")

    st.markdown("---")

    books = get_all_book_names(st.session_state.username)
    if not books:
        st.info("📚 Upload PDF")
    else:
        book_options = [display_name for _, display_name in books]
        selected_display = st.selectbox("Select:", book_options)
        
        selected_book = next(filename for filename, display in books if display == selected_display)
        
        if selected_book != st.session_state.current_book:
            st.session_state.current_book = selected_book
            st.session_state.current_page = 0
            st.session_state.page_text = ""
            st.session_state.page_image = None
            st.session_state.text_loading = False
            st.session_state.multi_page_mode = False
            st.session_state.selected_pages = []
            st.session_state.context_text = ""
            st.session_state.multi_page_images = []
            st.rerun()
        
        with st.expander("✏️ Rename"):
            current_name = get_display_name(st.session_state.username, selected_book)
            new_name = st.text_input("Name:", value=current_name, key="rename_input")
            if st.button("💾 Save", use_container_width=True):
                if new_name and new_name != current_name:
                    set_display_name(st.session_state.username, selected_book, new_name)
                    st.success("✅ Updated!")
                    st.rerun()

    st.markdown("---")
    st.header("⚙️ Settings")
    
    if st.session_state.current_book:
        zoom_level = st.slider(
            "🔍 PDF Zoom",
            min_value=1.0,
            max_value=4.0,
            value=st.session_state.zoom_level,
            step=0.5,
            help="Zoom PDF display only"
        )
        if zoom_level != st.session_state.zoom_level:
            st.session_state.zoom_level = zoom_level
            st.session_state.page_image = None
            if st.session_state.multi_page_mode:
                st.session_state.multi_page_images = []
            st.rerun()
        
        if st.session_state.extraction_method:
            if st.session_state.get('from_cache'):
                st.success(f"⚡ Cached")
            else:
                st.info(f"✓ {st.session_state.extraction_method}")
        
        st.markdown("---")
        
        st.subheader("📄 Multi-Page")
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
            
            if st.button("📚 Load", use_container_width=True):
                selected = list(range(start_page - 1, end_page))
                if len(selected) > 5:
                    st.warning("⚠️ Max 5")
                    selected = selected[:5]
                
                st.session_state.selected_pages = selected
                with st.spinner("Loading..."):
                    book_path = user_dir / st.session_state.current_book
                    context, images = extract_multi_page_content(
                        book_path, 
                        selected, 
                        st.session_state.zoom_level,
                        st.session_state.username,
                        st.session_state.current_book
                    )
                    st.session_state.context_text = context
                    st.session_state.multi_page_images = images
                st.success(f"✅ {len(selected)} pages!")
                st.rerun()
            
            if st.session_state.selected_pages:
                pages_list = ', '.join(str(p+1) for p in st.session_state.selected_pages)
                st.success(f"📄 {pages_list}")
    
    st.markdown("---")
    
    if st.button("🔄 Refresh", use_container_width=True):
        st.session_state.page_text = ""
        st.session_state.page_image = None
        st.session_state.text_loading = False
        if st.session_state.multi_page_mode:
            st.session_state.context_text = ""
            st.session_state.multi_page_images = []
            st.session_state.selected_pages = []
        st.rerun()

# --- MAIN CONTENT ---
if not st.session_state.current_book:
    st.markdown("""
    <div class='info-box'>
        <h2>👋 Welcome!</h2>
        <p><strong>✨ AI Contextual Reader</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class='feature-card'>
            <h4>📖 Reading</h4>
            <ul>
                <li>Instant page navigation</li>
                <li>Multi-page context</li>
                <li>Adjustable zoom</li>
                <li>Fast caching</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class='feature-card'>
            <h4>🤖 AI Analysis</h4>
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
            <h4>💾 Organization</h4>
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
    
    try:
        doc = fitz.open(book_path)
        st.session_state.total_pages = len(doc)
        doc.close()
    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.stop()

    # --- READER MODE ---
    if st.session_state.view_mode == "reader":
        st.markdown(f"<div class='book-title'>📖 {display_name}</div>", unsafe_allow_html=True)

        # Navigation
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("⬅️ Previous", disabled=(st.session_state.current_page == 0), use_container_width=True, key="prev_btn"):
                st.session_state.current_page -= 1
                st.session_state.page_image = None
                st.session_state.page_text = ""
                st.session_state.text_loading = False
                st.rerun()
        
        with col2:
            st.markdown(f"<div class='page-info'>Page {st.session_state.current_page + 1} of {st.session_state.total_pages}</div>", unsafe_allow_html=True)
            
            page_jump = st.number_input(
                "Jump:", 
                min_value=1, 
                max_value=st.session_state.total_pages, 
                value=st.session_state.current_page + 1, 
                label_visibility="collapsed",
                key="page_jump_input"
            )
            if page_jump - 1 != st.session_state.current_page:
                st.session_state.current_page = page_jump - 1
                st.session_state.page_image = None
                st.session_state.page_text = ""
                st.session_state.text_loading = False
                st.rerun()
        
        with col3:
            if st.button("Next ➡️", disabled=(st.session_state.current_page >= st.session_state.total_pages - 1), use_container_width=True, key="next_btn"):
                st.session_state.current_page += 1
                st.session_state.page_image = None
                st.session_state.page_text = ""
                st.session_state.text_loading = False
                st.rerun()

        # Bookmark button
        is_bm = is_bookmarked(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
        if st.button(f"{'🔖 Remove Bookmark' if is_bm else '🔖 Add Bookmark'}", use_container_width=True):
            if is_bm:
                remove_bookmark(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
                st.success("✅ Removed!")
            else:
                add_bookmark(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
                st.success("✅ Bookmarked!")
            time.sleep(0.5)
            st.rerun()

        st.markdown("---")

        # Load image immediately (no waiting for text)
        if not st.session_state.page_image:
            st.session_state.page_image = pdf_page_to_image(book_path, st.session_state.current_page, st.session_state.zoom_level)
        
        # Start text extraction in background if not loaded
        if not st.session_state.page_text and not st.session_state.text_loading:
            st.session_state.text_loading = True
            # Try to get from cache immediately
            cached_text, cached_method = get_cached_page(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
            if cached_text:
                st.session_state.page_text = cached_text
                st.session_state.extraction_method = cached_method
                st.session_state.from_cache = True
            else:
                # Start background extraction
                start_background_extraction(book_path, st.session_state.current_page, st.session_state.username, st.session_state.current_book)
                # Show loading message
                st.info("📝 Extracting text in background... Refresh in a moment to see text.")
        
        # Preload adjacent pages
        preload_adjacent_pages(book_path, st.session_state.current_page, st.session_state.total_pages, st.session_state.username, st.session_state.current_book)

        if st.session_state.page_image or (st.session_state.multi_page_mode and st.session_state.multi_page_images):
            if st.session_state.multi_page_mode and st.session_state.multi_page_images:
                # Horizontal scrollable pages
                st.subheader("📄 Pages")
                st.markdown(f"<div class='context-badge'>📚 {len(st.session_state.multi_page_images)} pages</div>", unsafe_allow_html=True)
                
                # Horizontal scroll container
                st.markdown("<div class='multi-page-scroll'>", unsafe_allow_html=True)
                cols = st.columns(len(st.session_state.multi_page_images))
                for idx, (page_num, img) in enumerate(st.session_state.multi_page_images):
                    with cols[idx]:
                        st.markdown(f"<div class='page-number-label'>Page {page_num}</div>", unsafe_allow_html=True)
                        st.image(img, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Text with copy button
                if st.session_state.context_text:
                    st.markdown("---")
                    st.subheader("📝 Extracted Text")
                    
                    col_t1, col_t2 = st.columns([5, 1])
                    with col_t2:
                        if st.button("📋 Copy All", use_container_width=True, key="copy_multi"):
                            st.code(st.session_state.context_text, language=None)
                            st.success("✅ Text ready to copy above!")
                    
                    with st.expander("View Text", expanded=False):
                        st.markdown(f"<div class='extracted-text-area'>{st.session_state.context_text}</div>", unsafe_allow_html=True)
                
                st.markdown("---")
                st.subheader("🎯 AI Analysis")
                st.info(f"📚 Analyzing {len(st.session_state.selected_pages)} pages")
                
            else:
                # Two columns for single page
                col_pdf, col_analysis = st.columns([1, 1])
                
                with col_pdf:
                    st.subheader("📄 Page")
                    st.image(st.session_state.page_image, use_container_width=True)
                    
                    if st.session_state.page_text:
                        col_t1, col_t2 = st.columns([5, 1])
                        with col_t2:
                            if st.button("📋 Copy", use_container_width=True, key="copy_single"):
                                st.code(st.session_state.page_text, language=None)
                                st.success("✅ Ready to copy!")
                        
                        with st.expander("📝 Text", expanded=False):
                            st.markdown(f"<div class='extracted-text-area'>{st.session_state.page_text}</div>", unsafe_allow_html=True)
                    else:
                        if st.session_state.text_loading:
                            if st.button("🔄 Check for Text", use_container_width=True):
                                cached_text, cached_method = get_cached_page(st.session_state.username, st.session_state.current_book, st.session_state.current_page)
                                if cached_text:
                                    st.session_state.page_text = cached_text
                                    st.session_state.extraction_method = cached_method
                                    st.session_state.from_cache = True
                                    st.rerun()
                                else:
                                    st.info("Still extracting...")
                
                with col_analysis:
                    st.subheader("🎯 Analysis")
            
            # Analysis (shared)
            selected_text = st.text_area(
                "📋 Paste text:",
                height=120,
                placeholder="Paste here...",
                key="user_text_input"
            )
            
            use_full_context = False
            if st.session_state.multi_page_mode and st.session_state.context_text:
                use_full_context = st.checkbox("📚 Use all pages", value=True)
            
            if selected_text and selected_text.strip():
                st.markdown(f"<div class='selected-text-box'>📄 {selected_text.strip()[:100]}...</div>", unsafe_allow_html=True)
                
                st.markdown("**🚀 Actions:**")
                
                actions = {
                    "🌍 Translate": "translate",
                    "💡 Explain": "explain",
                    "👶 ELI5": "eli5",
                    "📚 Historical": "historical",
                    "📝 Summary": "summary",
                    "🔄 Compare": "compare",
                    "🎨 Themes": "themes",
                    "📖 Cite": "cite"
                }
                
                cols = st.columns(4)
                for idx, (name, ptype) in enumerate(actions.items()):
                    with cols[idx % 4]:
                        if st.button(name, use_container_width=True, key=f"btn_{ptype}"):
                            analysis_text = selected_text.strip()
                            if use_full_context and st.session_state.context_text:
                                analysis_text = f"CONTEXT:\n{st.session_state.context_text}\n\nFOCUS:\n{analysis_text}"
                            
                            response_stream = get_gemini_explanation_stream(client, analysis_text, ptype)
                            
                            if response_stream:
                                placeholder = st.empty()
                                full_response = ""
                                
                                for chunk in response_stream:
                                    if hasattr(chunk, 'text'):
                                        full_response += chunk.text
                                        placeholder.markdown(f"<div class='ai-explanation'><strong>🤖 {name}:</strong><br><br>{full_response}</div>", unsafe_allow_html=True)
                                
                                save_to_history(
                                    st.session_state.username,
                                    st.session_state.current_book,
                                    st.session_state.current_page,
                                    name, name, full_response,
                                    selected_text.strip()
                                )
                                st.success("✅ Saved!")
                
                st.markdown("---")
                st.markdown("**💬 Custom:**")
                
                custom_q = st.text_input("Ask:", key="custom_q")
                
                if st.button("🔮 Answer", disabled=not custom_q, use_container_width=True):
                    try:
                        analysis_text = selected_text.strip()
                        if use_full_context and st.session_state.context_text:
                            prompt = f"CONTEXT:\n{st.session_state.context_text}\n\nFOCUS:\n{analysis_text}\n\nQUESTION: {custom_q}\n\nAnswer:"
                        else:
                            prompt = f"Text: '{analysis_text}'\n\nQuestion: {custom_q}\n\nAnswer:"
                        
                        response_stream = client.models.generate_content_stream(
                            model='gemini-2.0-flash-exp',
                            contents=prompt
                        )
                        
                        placeholder = st.empty()
                        full_response = ""
                        
                        for chunk in response_stream:
                            if hasattr(chunk, 'text'):
                                full_response += chunk.text
                                placeholder.markdown(f"<div class='ai-explanation'><strong>🤖:</strong><br><br>{full_response}</div>", unsafe_allow_html=True)
                        
                        save_to_history(
                            st.session_state.username,
                            st.session_state.current_book,
                            st.session_state.current_page,
                            "Custom Question",
                            custom_q, full_response,
                            selected_text.strip()
                        )
                        st.success("✅ Saved!")
                    except Exception as e:
                        st.error(f"❌ {e}")

    # --- BOOKMARKS MODE ---
    elif st.session_state.view_mode == "bookmarks":
        st.markdown(f"<div class='book-title'>🔖 Bookmarks: {display_name}</div>", unsafe_allow_html=True)
        
        bookmarks = get_bookmarks(st.session_state.username, st.session_state.current_book)
        
        if bookmarks:
            st.info(f"📚 {len(bookmarks)} bookmarks")
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
                    if st.button(f"Go", key=f"goto_bm_{page_num}", use_container_width=True):
                        st.session_state.view_mode = "reader"
                        st.session_state.current_page = page_num
                        st.session_state.page_image = None
                        st.session_state.page_text = ""
                        st.rerun()
                
                st.markdown("---")
        else:
            st.info("📭 No bookmarks yet")

    # --- HISTORY MODE ---
    elif st.session_state.view_mode == "history":
        st.markdown(f"<div class='book-title'>💬 History: {display_name}</div>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            md_export = export_book_history_to_markdown(st.session_state.username, st.session_state.current_book)
            st.download_button("📄 MD", md_export, file_name=f"{display_name}.md", mime="text/markdown", use_container_width=True)
        
        with col2:
            history_data = get_book_history(st.session_state.username, st.session_state.current_book)
            json_data = {
                "book": display_name,
                "total": len(history_data),
                "exported": datetime.now().isoformat(),
                "history": [{"page": p + 1, "type": pt, "question": q, "answer": a, "text": t, "time": ts}
                    for _, p, pt, q, a, t, ts in history_data]
            }
            st.download_button("📊 JSON", json.dumps(json_data, ensure_ascii=False, indent=2), 
                             file_name=f"{display_name}.json", mime="application/json", use_container_width=True)
        
        with col3:
            if st.button("🗑️ Clear", use_container_width=True):
                if st.session_state.get('confirm_clear'):
                    clear_book_history(st.session_state.username, st.session_state.current_book)
                    st.session_state.confirm_clear = False
                    st.success("✅ Cleared!")
                    st.rerun()
                else:
                    st.session_state.confirm_clear = True
                    st.warning("⚠️ Click again")
        
        st.markdown("---")
        
        history = get_book_history(st.session_state.username, st.session_state.current_book)
        
        if history:
            st.info(f"📚 {len(history)} conversations")
            st.markdown("---")
            
            for item_id, page_num, prompt_type, question, answer, text_snippet, timestamp in history:
                st.markdown(f"""
                <div class='history-chat-item'>
                    <div style='margin-bottom: 1rem;'>
                        <span class='page-badge'>📄 Page {page_num + 1}</span>
                        <span class='timestamp-badge'>⏰ {timestamp[:16]}</span>
                    </div>
                    <div class='history-prompt'><strong>{prompt_type}</strong><br>{question}</div>
                """, unsafe_allow_html=True)
                
                if text_snippet:
                    snippet = text_snippet[:300] + "..." if len(text_snippet) > 300 else text_snippet
                    st.markdown(f"<div class='history-text'><strong>📄:</strong><br>{snippet}</div>", unsafe_allow_html=True)
                
                st.markdown(f"<div class='history-response'><strong>🤖:</strong><br>{answer}</div>", unsafe_allow_html=True)
                
                col_a1, col_a2 = st.columns([3, 1])
                with col_a1:
                    if st.button(f"📍 Page {page_num + 1}", key=f"goto_{item_id}", use_container_width=True):
                        st.session_state.view_mode = "reader"
                        st.session_state.current_page = page_num
                        st.session_state.page_image = None
                        st.session_state.page_text = ""
                        st.rerun()
                
                with col_a2:
                    if st.button(f"🗑️", key=f"del_{item_id}", use_container_width=True):
                        delete_history_item(item_id)
                        st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.info("📭 No history")

st.markdown("---")
st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.9rem;'>Built with ❤️ using Gemini 2.0</div>", unsafe_allow_html=True)