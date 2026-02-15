import streamlit as st
import json
import unicodedata
from io import BytesIO
from anthropic import Anthropic
import os
import re

# Try multiple PDF libraries (fallback order)
try:
    import pdfplumber
    PDF_LIB = "pdfplumber"
except ImportError:
    try:
        import fitz  # PyMuPDF
        PDF_LIB = "pymupdf"
    except ImportError:
        import PyPDF2
        PDF_LIB = "pypdf2"

# --------------------------------------------------
# TEMPLATES (inline for now)
# --------------------------------------------------
TEMPLATES = {
    "tamil_qa": {
        "name": "🇮🇳 Tamil Q&A (Government Schemes)",
        "prompt": (
            "You are a Tamil language dataset creator.\n"
            "Extract information from Tamil government documents and create Q&A pairs.\n"
            "Output ONLY valid JSON. No explanations. No markdown.\n"
            "Return a JSON ARRAY. Each item must follow this schema:\n"
            "{ question: string (in Tamil), answer: string (in Tamil), category: string, source: string }\n"
            "IMPORTANT: Write questions and answers in proper Tamil script (தமிழ்), not in English.\n"
            "Create questions about schemes, eligibility, benefits, application process, etc.\n"
        ),
        "example": [
            {
                "question": "முதலமைச்சரின் விரிவான மருத்துவக் காப்பீட்டுத் திட்டம் என்றால் என்ன?",
                "answer": "இது தமிழ்நாடு அரசு நடத்தும் இலவச மருத்துவக் காப்பீட்டுத் திட்டமாகும்...",
                "category": "health_scheme",
                "source": "TN Government Document"
            }
        ]
    },
    "qa": {
        "name": "❓ Q&A",
        "prompt": (
            "You are a JSON extraction engine.\n"
            "Output ONLY valid JSON. No explanations. No markdown.\n"
            "Return a JSON ARRAY. Each item must follow this schema:\n"
            "{ question: string, answer: string, difficulty: string, topic: string }\n"
        ),
        "example": [
            {
                "question": "What is X?",
                "answer": "X is...",
                "difficulty": "medium",
                "topic": "subject"
            }
        ]
    },
    "instruction": {
        "name": "📝 Instruction",
        "prompt": (
            "You are a JSON extraction engine.\n"
            "Output ONLY valid JSON. No explanations. No markdown.\n"
            "Return a JSON ARRAY. Each item must follow this schema:\n"
            "{ instruction: string, input: string|null, output: string, complexity: string }\n"
        ),
        "example": [
            {
                "instruction": "Task description",
                "input": "Context if needed",
                "output": "Complete response",
                "complexity": "moderate"
            }
        ]
    }
}

# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(
    page_title="PDF to Tamil Dataset",
    page_icon="🤖",
    layout="wide"
)

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def extract_text_from_pdf(pdf_bytes):
    """Extract text from PDF using best available library"""
    
    if PDF_LIB == "pdfplumber":
        # BEST for Tamil
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            text = ''
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
            return clean_tamil_text(text)
    
    elif PDF_LIB == "pymupdf":
        # GOOD for Tamil
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ''
        for page in pdf:
            text += page.get_text() + '\n'
        return clean_tamil_text(text)
    
    else:
        # FALLBACK - PyPDF2 (not great for Tamil)
        reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))
        text = "\n\n".join(
            page.extract_text() or "" for page in reader.pages
        )
        return clean_tamil_text(text)


def clean_tamil_text(text: str) -> str:
    """Clean Tamil text - remove duplicates and fix spacing"""
    if not text:
        return ""
    
    # Step 1: Remove duplicate consecutive characters
    # But preserve spaces and newlines
    cleaned = []
    prev_char = ''
    
    for char in text:
        # Always keep structural characters
        if char in [' ', '\n', '\t', '.', ',', '!', '?']:
            if not (char == ' ' and prev_char == ' '):  # No double spaces
                cleaned.append(char)
            prev_char = char
            continue
        
        # For Tamil/other characters, skip exact duplicates
        if char != prev_char:
            cleaned.append(char)
        
        prev_char = char
    
    result = ''.join(cleaned)
    
    # Step 2: Unicode normalization
    result = unicodedata.normalize("NFC", result)
    
    # Step 3: Clean up whitespace
    result = re.sub(r' +', ' ', result)  # Multiple spaces → single space
    result = re.sub(r'\n\n+', '\n\n', result)  # Multiple newlines → double newline
    result = result.strip()
    
    return result


def clean_text(text: str) -> str:
    """Make text safe for JSON + LLM APIs"""
    if not isinstance(text, str):
        text = str(text)
    text = unicodedata.normalize("NFC", text)  # Changed from NFKC to NFC for Tamil
    text = text.encode("utf-8", "ignore").decode("utf-8")
    text = text.replace("\x00", "")
    return text


# --------------------------------------------------
# Session state init
# --------------------------------------------------
if "dataset" not in st.session_state:
    st.session_state.dataset = []

if "text" not in st.session_state:
    st.session_state.text = ""

if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("CLAUDE_API_KEY", "")

# --------------------------------------------------
# Header
# --------------------------------------------------
st.title("🤖 PDF to Tamil Dataset Creator")
st.caption("Transform Tamil government PDFs into LLM training datasets")
st.info(f"📚 Using: **{PDF_LIB}** for PDF extraction")

# --------------------------------------------------
# Sidebar
# --------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")

    api_key_input = st.text_input(
        "Claude API Key",
        value=st.session_state.api_key,
        type="password",
    )

    if api_key_input:
        st.session_state.api_key = api_key_input
        os.environ["CLAUDE_API_KEY"] = api_key_input
        st.success("✅ API Key configured")
    else:
        st.warning("⚠️ Please enter your Claude API key")

    template_key = st.selectbox(
        "Template",
        options=list(TEMPLATES.keys()),
        format_func=lambda x: TEMPLATES[x]["name"]
    )
    template = TEMPLATES[template_key]

    with st.expander("Template Example"):
        st.json(template["example"])

    chunk_size = st.slider("Chunk Size", 2000, 8000, 4000)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7)

# --------------------------------------------------
# Tabs
# --------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📤 Upload", "🤖 Generate", "📊 Export"])

# --------------------------------------------------
# TAB 1 — Upload
# --------------------------------------------------
with tab1:
    uploaded = st.file_uploader("Upload Tamil PDF", type=["pdf"])

    if uploaded and st.button("Extract Text"):
        with st.spinner("Extracting Tamil text..."):
            pdf_bytes = uploaded.read()
            
            # Extract using best method
            extracted_text = extract_text_from_pdf(pdf_bytes)
            
            st.session_state.text = extracted_text
            
            # Show stats
            num_chars = len(extracted_text)
            num_lines = len(extracted_text.split('\n'))
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Characters", f"{num_chars:,}")
            with col2:
                st.metric("Lines", num_lines)
            with col3:
                st.metric("Est. Chunks", len(extracted_text) // chunk_size)
            
            st.success(f"✅ Extraction complete using {PDF_LIB}")
            
            # Preview
            st.subheader("📄 Text Preview")
            preview_text = extracted_text[:2000]
            st.text_area("First 2000 characters", preview_text, height=300)
            
            # Download extracted text
            st.download_button(
                "💾 Download Extracted Text",
                extracted_text,
                "extracted_tamil.txt",
                "text/plain"
            )

# --------------------------------------------------
# TAB 2 — Generate
# --------------------------------------------------
with tab2:
    if not st.session_state.text:
        st.info("👈 Upload and extract a PDF first")
    else:
        st.write(f"**Ready to process:** {len(st.session_state.text):,} characters")
        
        if st.button("⚡ Generate Dataset", type="primary"):
            client = Anthropic(api_key=st.session_state.api_key)

            text = clean_text(st.session_state.text)

            # Create overlapping chunks for better context
            chunks = [
                text[i:i + chunk_size]
                for i in range(0, len(text), chunk_size - 500)  # 500 char overlap
            ]

            st.write(f"Processing {len(chunks)} chunks...")
            
            progress = st.progress(0.0)
            status = st.empty()
            all_entries = []

            for i, chunk in enumerate(chunks):
                status.text(f"Processing chunk {i + 1}/{len(chunks)}...")
                
                safe_chunk = clean_text(chunk)

                try:
                    response = client.messages.create(
                        model="claude-3-5-haiku-20241022",  # Better for Tamil
                        max_tokens=4096,  # More tokens for Tamil
                        temperature=temperature,
                        system=template["prompt"],
                        messages=[
                            {
                                "role": "user",
                                "content": (
                                    "Follow the schema exactly. Write in Tamil (தமிழ்) if the source is Tamil.\n"
                                    "Example output:\n"
                                    f"{json.dumps(template['example'], indent=2, ensure_ascii=False)}\n\n"
                                    "Text to extract from:\n"
                                    f"{safe_chunk}"
                                )
                            }
                        ]
                    )

                    text_response = response.content[0].text.strip()
                    text_response = (
                        text_response
                        .replace("```json", "")
                        .replace("```", "")
                        .strip()
                    )

                    entries = json.loads(text_response)

                    if isinstance(entries, list):
                        all_entries.extend(entries)
                        status.text(f"✅ Chunk {i + 1}: Generated {len(entries)} entries")

                except Exception as e:
                    st.warning(f"⚠️ Skipped chunk {i + 1}: {e}")

                progress.progress((i + 1) / len(chunks))

            st.session_state.dataset = all_entries
            status.text("")
            st.success(f"🎉 Generated {len(all_entries)} Tamil Q&A pairs!")

# --------------------------------------------------
# TAB 3 — Export
# --------------------------------------------------
with tab3:
    if not st.session_state.dataset:
        st.info("💡 Generate dataset first")
    else:
        dataset = st.session_state.dataset

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Entries", len(dataset))

        with col2:
            st.download_button(
                "💾 Download JSON",
                json.dumps(dataset, indent=2, ensure_ascii=False),
                "tamil_dataset.json",
                "application/json"
            )

        with col3:
            jsonl = "\n".join(
                json.dumps(entry, ensure_ascii=False)
                for entry in dataset
            )
            st.download_button(
                "📄 Download JSONL",
                jsonl,
                "tamil_dataset.jsonl",
                "application/json"
            )

        st.divider()
        st.subheader("📊 Dataset Preview")

        # Show first 10 entries
        for i, entry in enumerate(dataset[:10]):
            with st.expander(f"Entry {i + 1}"):
                st.json(entry)
        
        if len(dataset) > 10:
            st.info(f"Showing 10 of {len(dataset)} entries. Download to see all.")

        with st.expander("📋 Full Dataset (JSON)"):
            st.json(dataset)
        
        # Statistics
        st.divider()
        st.subheader("📈 Dataset Statistics")
        
        if dataset and isinstance(dataset[0], dict):
            # Count by category if available
            if 'category' in dataset[0]:
                categories = {}
                for entry in dataset:
                    cat = entry.get('category', 'unknown')
                    categories[cat] = categories.get(cat, 0) + 1
                
                st.write("**Categories:**")
                st.json(categories)
