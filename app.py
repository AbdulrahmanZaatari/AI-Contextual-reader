# --- 1. IMPORTS AND CONFIGURATION ---
import streamlit as st
from PIL import Image
import fitz  # PyMuPDF
from google import genai
from google.genai import types
import io
import base64
from pathlib import Path

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
    
    .pdf-viewer {
        border: 2px solid #e2e8f0;
        border-radius: 8px;
        overflow: auto;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        background: white;
        max-height: 70vh;
        text-align: center;
    }
    
    .info-box {
        background: #f0fdf4;
        border-left: 4px solid #22c55e;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .extracted-text-area {
        background: white;
        border: 2px solid #e2e8f0;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        font-family: 'Traditional Arabic', 'Simplified Arabic', 'Segoe UI', sans-serif;
        font-size: 1.4rem;
        line-height: 2.5;
        direction: rtl;
        text-align: right;
        max-height: 500px;
        overflow-y: auto;
        user-select: text;
        cursor: text;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

# --- PATHS AND DIRECTORIES ---
BOOK_DIR = Path("books_library")
BOOK_DIR.mkdir(exist_ok=True)

# --- GEMINI API CONFIGURATION ---
try:
    API_KEY = st.secrets["google_api_key"]
    client = genai.Client(api_key=API_KEY)
except KeyError:
    st.error("🔑 API key not found. Please create `.streamlit/secrets.toml` with your `google_api_key`.")
    st.stop()
except Exception as e:
    st.error(f"❌ Error initializing Gemini client: {e}")
    st.stop()

# --- 2. HELPER FUNCTIONS ---

def get_books():
    """Scans the book library directory and returns a list of PDF files."""
    return sorted([f.name for f in BOOK_DIR.glob("*.pdf")])

def pdf_page_to_image(pdf_path, page_number, zoom=2.0):
    """Convert PDF page to high-quality image for OCR."""
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_number]
        
        # Render at high quality for better OCR
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        doc.close()
        return img
    except Exception as e:
        st.error(f"❌ Error rendering PDF: {e}")
        return None

def extract_text_with_gemini_vision(image, client):
    """
    Extract text using Gemini's vision capabilities.
    This works like Google Lens and is FREE with your API key!
    """
    try:
        # Convert PIL image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=95)
        img_bytes = img_byte_arr.getvalue()
        
        # Create the proper Part object for the image
        image_part = types.Part.from_bytes(
            data=img_bytes,
            mime_type="image/jpeg"
        )
        
        # Create the prompt
        prompt = """
Extract ALL the text from this image EXACTLY as it appears.
- Preserve the original formatting and line breaks
- Keep the text in its original language (Arabic, English, etc.)
- Maintain right-to-left direction for Arabic text
- Do NOT translate or interpret
- Do NOT add any explanations
- Just return the raw extracted text

Text:
"""
        
        # Send request to Gemini with the image
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, image_part]
        )
        
        return response.text.strip()
        
    except Exception as e:
        st.error(f"❌ Gemini Vision Error: {e}")
        return ""

def extract_page_content(pdf_path, page_number, zoom=2.0):
    """
    Extract page content using the best available method.
    """
    # First, render page as image
    image = pdf_page_to_image(pdf_path, page_number, zoom)
    
    if not image:
        return "", None, "Error"
    
    # Try direct PDF text extraction first (fast for digital PDFs)
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_number]
        direct_text = page.get_text("text").strip()
        doc.close()
        
        # If we got substantial text, use it
        if direct_text and len(direct_text) > 100:
            return direct_text, image, "Direct PDF Text"
    except:
        pass
    
    # For scanned PDFs or poor direct extraction, use Gemini Vision
    st.info("📸 Using Gemini Vision to extract text (like Google Lens)...")
    text = extract_text_with_gemini_vision(image, client)
    return text, image, "Gemini Vision OCR"

def get_gemini_explanation(client, text_snippet, prompt_type="explain"):
    """
    Generates contextual explanation using Gemini with different prompt types.
    """
    prompt_templates = {
        "translate": f"""
Translate this Arabic text to English and provide a detailed explanation.
Include:
1. Direct translation
2. Meaning and context
3. Any cultural or religious significance
4. Word-by-word breakdown if it's a complex phrase

Arabic Text: {text_snippet}
""",
        
        "explain": f"""
Analyze and explain this text clearly.
If it's in Arabic, translate it first, then explain the meaning and context.
Focus on making it easy to understand.

Text: {text_snippet}
""",
        
        "eli5": f"""
Explain this text in very simple terms, as if to a 5-year-old child.
If it's in Arabic, translate it first, then explain simply with examples.

Text: {text_snippet}
""",
        
        "historical": f"""
Provide historical and cultural context for this text.
If it's in Arabic, include:
1. Translation
2. Historical period and context
3. Cultural significance
4. Related historical events or figures

Text: {text_snippet}
""",
        
        "summary": f"""
Provide a brief, concise summary.
If it's in Arabic, translate and summarize the main points.

Text: {text_snippet}
""",
        
        "research": f"""
Provide academic resources and scholarly context for this text.
Include:
1. Translation (if Arabic)
2. Relevant academic fields
3. Key scholars or works
4. Suggested further reading

Text: {text_snippet}
"""
    }
    
    prompt = prompt_templates.get(prompt_type, prompt_templates["explain"])
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"❌ API Error: {str(e)}"

def load_custom_prompts():
    """Load user's custom prompts from session state."""
    if 'custom_prompts' not in st.session_state:
        st.session_state.custom_prompts = {
            "🌍 Translate": "translate",
            "💡 Explain": "explain",
            "👶 Explain Simply": "eli5",
            "📚 Historical": "historical",
            "📝 Summary": "summary"
        }
    return st.session_state.custom_prompts

# --- 3. SESSION STATE INITIALIZATION ---
if 'current_book' not in st.session_state:
    st.session_state.current_book = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'total_pages' not in st.session_state:
    st.session_state.total_pages = 0
if 'zoom_level' not in st.session_state:
    st.session_state.zoom_level = 2.0
if 'last_explanation' not in st.session_state:
    st.session_state.last_explanation = None
if 'page_text' not in st.session_state:
    st.session_state.page_text = ""
if 'page_image' not in st.session_state:
    st.session_state.page_image = None
if 'extraction_method' not in st.session_state:
    st.session_state.extraction_method = ""

# --- 4. UI AND APPLICATION FLOW ---
st.title("📚 AI Contextual Reader")
st.markdown("*Powered by Google Gemini Vision - Perfect for Arabic & English texts!*")
st.markdown("---")

# --- SIDEBAR ---
with st.sidebar:
    st.header("📖 My Library")

    uploaded_file = st.file_uploader("Upload PDF", type="pdf", help="Upload your book")
    if uploaded_file:
        file_path = BOOK_DIR / uploaded_file.name
        if not file_path.exists():
            with st.spinner(f"Saving '{uploaded_file.name}'..."):
                file_path.write_bytes(uploaded_file.getvalue())
            st.success(f"✅ Added!")
            st.rerun()
        else:
            st.info("📘 Already in library.")

    st.markdown("---")

    book_list = get_books()
    if not book_list:
        st.info("📚 Upload a PDF to start.")
    else:
        selected_book = st.selectbox(
            "Select book:",
            book_list,
            index=book_list.index(st.session_state.current_book) if st.session_state.current_book in book_list else 0
        )
        if selected_book != st.session_state.current_book:
            st.session_state.current_book = selected_book
            st.session_state.current_page = 0
            st.session_state.last_explanation = None
            st.session_state.page_text = ""
            st.session_state.page_image = None
            st.rerun()

    st.markdown("---")
    st.header("⚙️ Settings")
    
    zoom_level = st.slider(
        "🔍 Image Quality",
        min_value=1.5,
        max_value=3.0,
        value=st.session_state.zoom_level,
        step=0.25,
        help="Higher = better text extraction (but slower)"
    )
    if zoom_level != st.session_state.zoom_level:
        st.session_state.zoom_level = zoom_level
        st.session_state.page_text = ""
        st.session_state.page_image = None
        st.rerun()
    
    if st.session_state.extraction_method:
        st.success(f"✓ {st.session_state.extraction_method}")
    
    st.markdown("---")
    
    if st.button("🔄 Refresh Page", use_container_width=True):
        st.session_state.page_text = ""
        st.session_state.page_image = None
        st.session_state.last_explanation = None
        st.rerun()
    
    with st.expander("💡 How to Use"):
        st.markdown("""
        **Steps:**
        1. 📤 Upload your PDF
        2. ⏳ Wait for text extraction (10-20 sec)
        3. 👀 See extracted text below
        4. ✂️ Select & copy any text
        5. 📋 Paste in the analysis box
        6. 🤖 Click an action button!
        
        **Perfect for:**
        - ✅ Arabic books & documents
        - ✅ Scanned PDFs
        - ✅ Mixed Arabic/English text
        - ✅ Religious texts
        - ✅ Historical documents
        """)

# --- MAIN PANEL ---
if not st.session_state.current_book:
    st.markdown("""
    <div class='info-box'>
        <h3>👋 Welcome to AI Contextual Reader!</h3>
        <p><strong>✨ Powered by Google Gemini Vision - Like Google Lens!</strong></p>
        <ul>
            <li>📸 <strong>Excellent Arabic OCR</strong> - Better than traditional OCR</li>
            <li>🎯 <strong>Smart text extraction</strong> - Works with scanned PDFs</li>
            <li>🤖 <strong>AI translations & explanations</strong></li>
            <li>🌍 <strong>Perfect for Arabic religious texts</strong></li>
            <li>⚡ <strong>Fast and accurate</strong></li>
        </ul>
        <p>👉 Upload a PDF to get started!</p>
    </div>
    """, unsafe_allow_html=True)
else:
    book_path = BOOK_DIR / st.session_state.current_book
    
    try:
        doc = fitz.open(book_path)
        st.session_state.total_pages = len(doc)
        doc.close()
    except Exception as e:
        st.error(f"❌ Could not read PDF: {e}")
        st.stop()

    st.markdown(f"<div class='book-title'>📖 {st.session_state.current_book}</div>", unsafe_allow_html=True)

    # Navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("⬅️ Previous", disabled=(st.session_state.current_page == 0), use_container_width=True):
            st.session_state.current_page -= 1
            st.session_state.page_text = ""
            st.session_state.page_image = None
            st.session_state.last_explanation = None
            st.rerun()
    
    with col2:
        st.markdown(f"<div class='page-info'>Page {st.session_state.current_page + 1} of {st.session_state.total_pages}</div>", unsafe_allow_html=True)
        
        page_jump = st.number_input("Jump:", min_value=1, max_value=st.session_state.total_pages, 
                                     value=st.session_state.current_page + 1, label_visibility="collapsed")
        if page_jump - 1 != st.session_state.current_page:
            st.session_state.current_page = page_jump - 1
            st.session_state.page_text = ""
            st.session_state.page_image = None
            st.session_state.last_explanation = None
            st.rerun()
    
    with col3:
        if st.button("Next ➡️", disabled=(st.session_state.current_page >= st.session_state.total_pages - 1), use_container_width=True):
            st.session_state.current_page += 1
            st.session_state.page_text = ""
            st.session_state.page_image = None
            st.session_state.last_explanation = None
            st.rerun()

    st.markdown("---")

    # Extract content
    if not st.session_state.page_text:
        with st.spinner("🔍 Extracting text with Gemini Vision... (10-20 seconds)"):
            text, image, method = extract_page_content(book_path, st.session_state.current_page, st.session_state.zoom_level)
            st.session_state.page_text = text
            st.session_state.page_image = image
            st.session_state.extraction_method = method

    if st.session_state.page_image:
        # Show page image
        st.subheader("📄 Page Image")
        st.markdown("<div class='pdf-viewer'>", unsafe_allow_html=True)
        st.image(st.session_state.page_image, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Show extracted text
        if st.session_state.page_text:
            st.subheader("📝 Extracted Text (Select & Copy)")
            st.caption("💡 Select any text below with your mouse, then copy it (Ctrl+C / Cmd+C)")
            
            st.markdown(f"<div class='extracted-text-area'>{st.session_state.page_text}</div>", unsafe_allow_html=True)
            
            # Also provide in a text area for easier selection
            st.text_area(
                "Or copy from here:",
                value=st.session_state.page_text,
                height=200,
                key="text_display"
            )
        else:
            st.warning("⚠️ No text extracted. Try refreshing or adjusting zoom level.")
        
        st.markdown("---")
        
        # Analysis section
        st.subheader("🎯 Analyze Text with AI")
        selected_text = st.text_area(
            "📋 Paste the text you want to analyze:",
            height=120,
            placeholder="الصق النص هنا... / Paste your text here...",
            key="user_text_input"
        )
        
        if selected_text and selected_text.strip():
            st.markdown(f"<div class='selected-text-box'>📄 {selected_text.strip()}</div>", unsafe_allow_html=True)
            
            st.markdown("**🚀 Quick Actions:**")
            custom_prompts = load_custom_prompts()
            
            cols = st.columns(len(custom_prompts))
            for idx, (prompt_name, prompt_type) in enumerate(custom_prompts.items()):
                with cols[idx]:
                    if st.button(prompt_name, use_container_width=True, key=f"btn_{prompt_type}"):
                        with st.spinner(f"🤖 Processing..."):
                            explanation = get_gemini_explanation(client, selected_text.strip(), prompt_type)
                            st.session_state.last_explanation = (prompt_name, explanation)
                            st.rerun()
            
            if st.session_state.last_explanation:
                prompt_name, explanation = st.session_state.last_explanation
                st.markdown(f"<div class='ai-explanation'><strong>🤖 {prompt_name}:</strong><br><br>{explanation}</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("**💬 Ask Your Own Question:**")
            custom_question = st.text_input("What do you want to know about this text?", key="custom_q")
            if st.button("🔮 Get Answer", disabled=not custom_question):
                with st.spinner("🤖 Thinking..."):
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=f"Text: '{selected_text.strip()}'\n\nQuestion: {custom_question}\n\nProvide a clear, detailed answer:"
                        )
                        st.markdown(f"<div class='ai-explanation'><strong>🤖 Answer:</strong><br><br>{response.text}</div>", unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

st.markdown("---")
st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.9rem;'>Built with ❤️ using Google Gemini Vision API | Perfect for Arabic texts</div>", unsafe_allow_html=True)