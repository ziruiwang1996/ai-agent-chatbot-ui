import streamlit as st, requests, time


st.title("💬 Chatbot")
st.caption("📝 Agent server will spin down with inactivity, which can delay requests by 50 seconds or more")
st.caption("🚀 Model Context Protocol–compliant chatbot, powered by Gemini")
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

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
            response = requests.post(
                "https://ai-agent-latest-xo5b.onrender.com/chat",
                json={"query": prompt},
                stream=True 
            )

            text_accum = ""
            for chunk in response.iter_content(chunk_size=32, decode_unicode=True):
                if not chunk: continue
                text_accum += chunk
                response_placeholder.markdown(text_accum)
                time.sleep(0.01)
            # final render without cursor
            response_placeholder.markdown(text_accum)
            st.session_state.messages.append({"role":"assistant","content":text_accum})

    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
        st.chat_message("assistant").write(f"Error: {str(e)}")