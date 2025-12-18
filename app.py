import streamlit as st
import PyPDF2
import json
from io import BytesIO
from anthropic import Anthropic
from .templates import TEMPLATES
from .agent import validate_dataset
from dotenv import load_dotenv
import os

st.set_page_config(page_title="PDF to Dataset", page_icon="🤖", layout="wide")

load_dotenv()

# Initialize
if 'dataset' not in st.session_state:
    st.session_state.dataset = []
if 'text' not in st.session_state:
    st.session_state.text = ""
if "api_key" not in st.session_state:
    # langchain-google-genai uses GOOGLE_API_KEY by default
    st.session_state.api_key = os.getenv("CLAUDE_API_KEY", "")
# Header
st.title("🤖 PDF to Dataset Creator")
st.caption("Transform PDFs into LLM training datasets with AI validation")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Key input
    api_key_input = st.text_input(
        "Claude API Key",
        value=st.session_state.api_key,
        type="password",
    )

    if api_key_input:
        st.session_state.api_key = api_key_input
        os.environ["CLAUDE_API_KEY"] = st.session_state.api_key
        st.success("✅ API Key configured")
    else:
        st.warning("⚠️ Please enter your Claude API key")
    
    template_key = st.selectbox(
        "Template",
        options=list(TEMPLATES.keys()),
        format_func=lambda x: TEMPLATES[x]["name"]
    )
    template = TEMPLATES[template_key]
    
    with st.expander("Example"):
        st.json(template["example"])
    
    chunk_size = st.slider("Chunk Size", 2000, 8000, 4000)
    temp = st.slider("Temperature", 0.0, 1.0, 0.7)

# Main tabs
tab1, tab2, tab3 = st.tabs(["📤 Upload", "🤖 Generate", "📊 Export"])

with tab1:
    uploaded = st.file_uploader("Upload PDF", type=['pdf'])
    
    if uploaded and st.button("Extract Text"):
        reader = PyPDF2.PdfReader(BytesIO(uploaded.read()))
        text = "\n\n".join([p.extract_text() for p in reader.pages])
        st.session_state.text = text
        st.success(f"✅ Extracted {len(reader.pages)} pages")
        st.text_area("Preview", text[:1000], height=200)

with tab2:
    if not st.session_state.text:
        st.info("👈 Upload and extract PDF first")
    else:
        if st.button("⚡ Generate Dataset", type="primary"):
            client = Anthropic(api_key=st.session_state.api_key)
            
            # Chunk text
            text = st.session_state.text
            chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size-200)]
            
            progress = st.progress(0)
            all_entries = []
            
            for i, chunk in enumerate(chunks):
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    temperature=temp,
                    system=template["prompt"],
                    messages=[{"role": "user", "content": f"Extract dataset from:\n{chunk}"}]
                )
                
                try:
                    text_response = response.content[0].text.strip()
                    text_response = text_response.replace("```json", "").replace("```", "")
                    entries = json.loads(text_response)
                    if isinstance(entries, list):
                        all_entries.extend(entries)
                except:
                    pass
                
                progress.progress((i+1)/len(chunks))
            
            st.session_state.dataset = all_entries
            st.success(f"✅ Generated {len(all_entries)} entries")
            
            # Quick validation
            if st.button("🔍 Validate with AI"):
                with st.spinner("Validating..."):
                    report = validate_dataset(all_entries, st.session_state.api_key)
                    st.markdown("### Validation Report")
                    st.write(report)

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
                "💾 JSON",
                json.dumps(dataset, indent=2),
                "dataset.json",
                "application/json"
            )
        with col3:
            jsonl = "\n".join([json.dumps(e) for e in dataset])
            st.download_button(
                "📄 JSONL",
                jsonl,
                "dataset.jsonl"
            )
        
        st.divider()
        st.subheader("Preview")
        for i, entry in enumerate(dataset[:5]):
            with st.expander(f"Entry {i+1}"):
                st.json(entry)
        
        with st.expander("Full Dataset"):
            st.json(dataset)