import streamlit as st
import json
import unicodedata
from io import BytesIO
from anthropic import Anthropic
from templates import TEMPLATES
from agent import validate_dataset
from dotenv import load_dotenv
import os
import tempfile
import re

from pdfminer.high_level import extract_text
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image

# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(
    page_title="PDF to Dataset",
    page_icon="🤖",
    layout="wide"
)

load_dotenv()

# --------------------------------------------------
# Tamil Text Cleaning (SAFE)
# --------------------------------------------------
def clean_tamil_text(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFC", text)
    text = text.replace("\x00", "")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# --------------------------------------------------
# Detect Corrupted Tamil
# --------------------------------------------------
def is_tamil_corrupted(text: str) -> bool:
    if not text:
        return True

    tamil_chars = re.findall(r'[\u0B80-\u0BFF]', text)
    ratio = len(tamil_chars) / max(len(text), 1)

    return ratio < 0.1  # Less than 10% Tamil → probably corrupted


# --------------------------------------------------
# OCR Extraction
# --------------------------------------------------
def extract_with_ocr(pdf_bytes):
    st.info("🔎 Running OCR... (Tamil language)")

    images = convert_from_bytes(pdf_bytes, dpi=300)

    full_text = ""

    for img in images:
        text = pytesseract.image_to_string(img, lang="tam")
        full_text += text + "\n\n"

    return clean_tamil_text(full_text)


# --------------------------------------------------
# Main Extraction Logic
# --------------------------------------------------
def extract_text_from_pdf(pdf_bytes):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        text = extract_text(tmp_path)
        text = clean_tamil_text(text)

        if is_tamil_corrupted(text):
            st.warning("⚠️ Text looks corrupted. Switching to OCR...")
            return extract_with_ocr(pdf_bytes)

        return text

    except Exception as e:
        st.warning(f"⚠️ Direct extraction failed. Using OCR. Error: {e}")
        return extract_with_ocr(pdf_bytes)


# --------------------------------------------------
# JSON Safe Clean
# --------------------------------------------------
def clean_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)

    text = unicodedata.normalize("NFC", text)
    text = text.encode("utf-8", "ignore").decode("utf-8")
    text = text.replace("\x00", "")

    return text


# --------------------------------------------------
# Session state
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
st.title("🤖 PDF to Dataset Creator")
st.caption("Transform PDFs into LLM training datasets with AI validation")
st.info("📚 Smart extraction: Direct + Auto OCR fallback (Tamil supported)")

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
    uploaded = st.file_uploader("Upload PDF", type=["pdf"])

    if uploaded and st.button("Extract Text"):
        with st.spinner("Extracting text..."):
            pdf_bytes = uploaded.read()
            extracted_text = extract_text_from_pdf(pdf_bytes)

            st.session_state.text = extracted_text
            num_chars = len(extracted_text)

            st.success(f"✅ Extracted {num_chars:,} characters")
            st.text_area("Preview", extracted_text[:1000], height=200)

# --------------------------------------------------
# TAB 2 — Generate Dataset
# --------------------------------------------------
with tab2:
    if not st.session_state.text:
        st.info("👈 Upload and extract a PDF first")
    else:
        if st.button("⚡ Generate Dataset", type="primary"):
            client = Anthropic(api_key=st.session_state.api_key)

            text = clean_text(st.session_state.text)

            chunks = [
                text[i:i + chunk_size]
                for i in range(0, len(text), chunk_size - 200)
            ]

            progress = st.progress(0.0)
            all_entries = []

            for i, chunk in enumerate(chunks):
                safe_chunk = clean_text(chunk)

                try:
                    response = client.messages.create(
                        model="claude-3-5-haiku-20241022",
                        max_tokens=2048,
                        temperature=temperature,
                        system=template["prompt"],
                        messages=[
                            {
                                "role": "user",
                                "content": (
                                    "Follow the schema exactly.\n"
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

                except Exception as e:
                    st.warning(f"⚠️ Skipped chunk {i + 1}: {e}")

                progress.progress((i + 1) / len(chunks))

            st.session_state.dataset = all_entries
            st.success(f"✅ Generated {len(all_entries)} entries")

            if st.button("🔍 Validate with AI"):
                with st.spinner("Validating dataset..."):
                    report = validate_dataset(
                        all_entries,
                        st.session_state.api_key
                    )
                    st.subheader("Validation Report")
                    st.write(report)

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
            st.metric("Entries", len(dataset))

        with col2:
            st.download_button(
                "💾 Download JSON",
                json.dumps(dataset, indent=2, ensure_ascii=False),
                "dataset.json",
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
                "dataset.jsonl",
                "application/json"
            )

        st.divider()
        st.subheader("Preview")

        for i, entry in enumerate(dataset[:5]):
            with st.expander(f"Entry {i + 1}"):
                st.json(entry)

        with st.expander("Full Dataset"):
            st.json(dataset)
