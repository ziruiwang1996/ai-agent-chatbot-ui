import streamlit as st, requests, time
import json
from typing import List, Dict, Any

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

# API endpoints (use environment variable for production)
#API_BASE_URL = "http://0.0.0.0:8000"  # Change to production URL when deploying
API_BASE_URL = "https://ai-agent-latest-xo5b.onrender.com"

# ═══════════════════════════════════════════════════════════════
# PAGE SETUP
# ═══════════════════════════════════════════════════════════════

st.title("💬 Research Agent Chatbot")
st.caption("📝 Agent server will spin down with inactivity, which can delay requests by 50 seconds or more")
st.caption("🚀 Model Context Protocol–compliant chatbot, powered by Gemini")
st.caption("🔨 Ask me tools I can use to help you with your research.")
st.caption("📄 NEW: Upload documents (PDF/TXT) for context-aware answers!")

# ═══════════════════════════════════════════════════════════════
# SESSION STATE INITIALIZATION
# ═══════════════════════════════════════════════════════════════
# Streamlit's session_state persists data across reruns within a user session

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = None

# New: Track uploaded documents for this session
if "uploaded_documents" not in st.session_state:
    st.session_state["uploaded_documents"] = []

# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def upload_document_to_server(uploaded_file, thread_id: str) -> Dict[str, Any]:
    """
    Upload a document to the server for RAG processing.
    
    Process:
    1. Prepare multipart/form-data request
    2. Send file + thread_id to /documents/upload
    3. Server processes and stores in vector store
    4. Return document metadata
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        thread_id: Current thread ID
        
    Returns:
        Dictionary with document metadata or error info
        
    Learning Note:
        - Streamlit's UploadedFile has a file-like interface
        - We use 'files' and 'data' params for multipart uploads
        - Server returns metadata (chunks, size, etc.)
    """
    try:
        # Prepare multipart form data
        # 'file': the actual file content
        # 'thread_id': form field with thread identifier
        files = {
            'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
        }
        data = {
            'thread_id': thread_id
        }
        
        # Send POST request to upload endpoint
        response = requests.post(
            f"{API_BASE_URL}/documents/upload",
            files=files,
            data=data,
            timeout=30  # 30 second timeout for large files
        )
        
        if response.ok:
            return response.json()
        else:
            return {"error": f"Upload failed: {response.status_code}"}
    
    except Exception as e:
        return {"error": str(e)}


def get_uploaded_documents(thread_id: str) -> List[Dict[str, Any]]:
    """
    Get list of documents uploaded for current thread.
    
    Args:
        thread_id: Current thread ID
        
    Returns:
        List of document metadata dictionaries
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/documents/list/{thread_id}",
            timeout=10
        )
        
        if response.ok:
            data = response.json()
            return data.get("documents", [])
        else:
            return []
    
    except Exception as e:
        st.error(f"Error fetching documents: {e}")
        return []


def clear_documents_on_server(thread_id: str) -> bool:
    """
    Clear all documents for a thread on the server.
    
    Args:
        thread_id: Thread to clear documents for
        
    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.delete(
            f"{API_BASE_URL}/documents/clear/{thread_id}",
            timeout=10
        )
        return response.ok
    except Exception as e:
        st.error(f"Error clearing documents: {e}")
        return False


def _do_reset_chat():
    """
    Reset chat on the server and clear local messages.
    
    This function:
    1. Clears documents on server (RAG cleanup)
    2. Resets the thread (new conversation)
    3. Clears local UI state
    
    Learning Note:
        - Order matters: clear docs before resetting thread
        - Server handles both thread config and RAG cleanup
        - UI state must be synchronized with server state
    """
    try:
        # Prepare payload with current thread_id
        payload = {"thread_id": st.session_state.thread_id} if st.session_state.thread_id else {}
        
        # Send reset request to server
        resp = requests.post(f"{API_BASE_URL}/chat/reset", json=payload)
        
        if resp.ok:
            data = resp.json()
            
            # Update session state with new thread_id
            st.session_state.thread_id = data.get("thread_id")
            
            # Clear local messages
            st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]
            
            # Clear uploaded documents list
            st.session_state["uploaded_documents"] = []
            
            # Show success message
            st.toast("Started a new conversation thread.")
            
            # Show if documents were cleared
            if data.get("documents_cleared"):
                st.toast("Previous documents cleared.", icon="🗑️")
        else:
            st.warning("Failed to reset chat on server.")
    
    except Exception as e:
        st.error(f"Reset error: {e}")


# ═══════════════════════════════════════════════════════════════
# SIDEBAR: Document Upload & Management
# ═══════════════════════════════════════════════════════════════

with st.sidebar:
    st.header("📄 Document Upload (RAG)")
    
    st.markdown("""
    Upload documents to enhance chatbot responses with your content!
    
    **Supported formats:**
    - PDF (`.pdf`)
    - Text (`.txt`)
    - Markdown (`.md`)
    - Word (`.docx`)
    """)
    
    # File uploader widget
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "txt", "md", "docx"],
        help="Upload a document to enable context-aware answers"
    )
    
    # Handle file upload
    if uploaded_file is not None:
        # Create button to trigger upload
        if st.button("📤 Upload Document", type="primary"):
            # Ensure we have a thread_id
            if not st.session_state.thread_id:
                st.warning("Please send a message first to start a thread.")
            else:
                with st.spinner(f"Uploading {uploaded_file.name}..."):
                    result = upload_document_to_server(uploaded_file, st.session_state.thread_id)
                    
                    if "error" in result:
                        st.error(f"Upload failed: {result['error']}")
                    else:
                        st.success(f"✓ Uploaded: {uploaded_file.name}")
                        
                        # Show document info
                        doc_info = result.get("document", {})
                        st.info(f"""
                        **Document processed:**
                        - Chunks: {doc_info.get('num_chunks', 'N/A')}
                        - Pages: {doc_info.get('num_pages', 'N/A')}
                        - Size: {doc_info.get('file_size', 0) / 1024:.1f} KB
                        """)
                        
                        # Refresh document list
                        st.session_state["uploaded_documents"] = get_uploaded_documents(
                            st.session_state.thread_id
                        )
                        
                        # Force rerun to update UI
                        st.rerun()
    
    st.divider()
    
    # Display uploaded documents
    st.subheader("📚 Uploaded Documents")
    
    if st.session_state.thread_id and st.session_state.get("uploaded_documents"):
        # Refresh documents list from server
        if st.button("🔄 Refresh List"):
            st.session_state["uploaded_documents"] = get_uploaded_documents(
                st.session_state.thread_id
            )
            st.rerun()
        
        # Display each document
        for idx, doc in enumerate(st.session_state["uploaded_documents"]):
            with st.expander(f"📄 {doc['filename']}", expanded=False):
                st.write(f"**Chunks:** {doc['num_chunks']}")
                st.write(f"**Pages:** {doc.get('num_pages', 'N/A')}")
                st.write(f"**Size:** {doc['file_size'] / 1024:.1f} KB")
                st.write(f"**Uploaded:** {doc['upload_time'][:19]}")  # Trim milliseconds
        
        # Clear all documents button
        if st.button("🗑️ Clear All Documents", type="secondary"):
            with st.spinner("Clearing documents..."):
                if clear_documents_on_server(st.session_state.thread_id):
                    st.session_state["uploaded_documents"] = []
                    st.success("Documents cleared!")
                    st.rerun()
                else:
                    st.error("Failed to clear documents")
    
    else:
        st.info("No documents uploaded yet.")
        st.caption("Upload a document above to get started!")
    
    st.divider()
    
    # Learning tips
    with st.expander("💡 How RAG Works", expanded=False):
        st.markdown("""
        **Retrieval Augmented Generation (RAG):**
        
        1. **Upload:** Document is split into chunks
        2. **Embed:** Each chunk gets a vector embedding
        3. **Store:** Embeddings saved in vector database
        4. **Query:** Your question is also embedded
        5. **Retrieve:** Most similar chunks are found
        6. **Generate:** LLM uses chunks to answer
        
        **Benefits:**
        - Answer questions from YOUR documents
        - No model fine-tuning needed
        - Documents stay in your session
        - Automatic cleanup when you close
        """)

# ═══════════════════════════════════════════════════════════════
# MAIN CHAT INTERFACE
# ═══════════════════════════════════════════════════════════════

cols = st.columns([2, 1, 6])
with cols[0]:
    # Use non-breaking spaces to keep the label on one line: "| reset chat |"
    with st.popover("reset chat"):
        st.markdown("### Start a new chat?")
        st.caption("This will reset the server thread, clear the conversation history, and remove all uploaded documents.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="confirm_reset"):
                with st.spinner("Resetting chat…"):
                    _do_reset_chat()
                    st.rerun()  # Force UI refresh
        with c2:
            st.button("Cancel", use_container_width=True, key="cancel_reset")

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    # if not gemini_api_key:
    #     st.info("Please add your Gemini API key to continue.")
    #     st.stop()

    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # Send query to GeminiChatBot API and handle streaming response


    try:
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            # Include thread_id if we have one to preserve server-side memory
            payload = {"query": prompt}
            if st.session_state.thread_id:
                payload["thread_id"] = st.session_state.thread_id

            response = requests.post(
                f"{API_BASE_URL}/chat/stream",
                json=payload,
                stream=True
            )

            text_accum = ""
            
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                
                # Parse SSE format: "data: {json}"
                if line.startswith('data: '):
                    try:
                        # Extract JSON from "data: {json}" format
                        json_str = line[6:]  # Remove 'data: ' prefix
                        data = json.loads(json_str)
                        
                        if data['type'] == 'thread_id':
                            # Always store/update the server-provided thread_id
                            st.session_state.thread_id = data['thread_id']
                        
                        elif data['type'] == 'content':
                            text_accum += data['content']
                            response_placeholder.markdown(text_accum + "▊")  # Show cursor
                            time.sleep(0.01)
                        
                        elif data['type'] == 'done':
                            break
                        
                        elif data['type'] == 'error':
                            st.error(f"API Error: {data['content']}")
                            break
                            
                    except json.JSONDecodeError:
                        # Skip malformed JSON lines
                        continue
            
            # Final render without cursor
            response_placeholder.markdown(text_accum)
            st.session_state.messages.append({"role": "assistant", "content": text_accum})

    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
        st.chat_message("assistant").write(f"Error: {str(e)}")