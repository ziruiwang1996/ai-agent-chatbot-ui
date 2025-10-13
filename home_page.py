import streamlit as st, requests, time
import json

st.title("💬 Research Agent Chatbot")
st.caption("📝 Agent server will spin down with inactivity, which can delay requests by 50 seconds or more")
st.caption("🚀 Model Context Protocol–compliant chatbot, powered by Gemini")
st.caption("🔨 Ask me tools I can use to help you with your research.")
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = None

def _do_reset_chat():
    """Reset chat on the server and clear local messages."""
    try:
        payload = {"thread_id": st.session_state.thread_id} if st.session_state.thread_id else {}
        resp = requests.post("https://ai-agent-latest-xo5b.onrender.com/chat/reset", json=payload)
        if resp.ok:
            data = resp.json()
            st.session_state.thread_id = data.get("thread_id")
            st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]
            st.toast("Started a new conversation thread.")
        else:
            st.warning("Failed to reset chat on server.")
    except Exception as e:
        st.error(f"Reset error: {e}")


cols = st.columns([2, 1, 6])
with cols[0]:
    # Use non-breaking spaces to keep the label on one line: "| reset chat |"
    with st.popover("reset chat"):
        st.markdown("### Start a new chat?")
        st.caption("This will reset the server thread and clear the conversation history.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="confirm_reset"):
                with st.spinner("Resetting chat…"):
                    _do_reset_chat()
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
                "https://ai-agent-latest-xo5b.onrender.com/chat/stream",
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