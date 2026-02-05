import streamlit as st
import time
import base64
import os
import sys



# Fix path: Intelligent Search for Project Root
try:
    current_scan_dir = os.path.dirname(os.path.abspath(__file__))
    found_root = None
    # Scan up to 4 levels
    for i in range(4):
        if os.path.exists(os.path.join(current_scan_dir, "kb_manager.py")):
            found_root = current_scan_dir
            break
        current_scan_dir = os.path.dirname(current_scan_dir)

    if found_root:
        if found_root not in sys.path:
            sys.path.insert(0, found_root) # Insert at beginning
        # Add to debug log without printing
        # st.success(f"✅ Auto-fixed path: {found_root}")
    else:
        # Fallback strategies
        sys.path.append(os.getcwd())
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
except Exception as e:
    st.error(f"Path Fix Error: {e}")

import streamlit.components.v1 as components
try:
    from core.kb_manager import KBManager
    from core import ui_components
    from core.rag_agent import RAGAgent
except ImportError as e:
    st.error(f"❌ CRITICAL IMPORT ERROR: {e}")
    st.info("Check the debug info above to see the search paths.")
    st.stop()

# Inject JS for keyboard shortcut (Cmd/Ctrl + ,)
components.html("""
<script>
document.addEventListener('keydown', function(e) {
    if ((e.metaKey || e.ctrlKey) && (e.key === ',' || e.keyCode === 188)) {
        e.preventDefault();
        window.top.postMessage({type: 'open-settings'}, '*');
    }
}, true);
</script>
""", height=0, width=0)

st.set_page_config(page_title="智能助教", page_icon="logo.png", layout="wide")

st.markdown(f"""
<style>
    .block-container {{ padding-top: 2rem; }}
    img {{ image-rendering: -webkit-optimize-contrast; }}
    
    .stChatMessage {{ 
        padding: 1.2rem; 
        border-radius: 16px; 
        margin-bottom: 1rem; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); 
        border: 1px solid rgba(128, 128, 128, 0.1);
    }}
    
    /* Sidebar Styles from ui_components */
    {ui_components.get_sidebar_css()}
</style>
""", unsafe_allow_html=True)

# sidebar
ui_components.render_sidebar()

st.title("🧠 智能助教")

# KB Selection with persistence
kb_manager = KBManager()
kbs = kb_manager.list_kbs()

if not kbs:
    st.warning("⚠️ 未检测到知识库。请先前往【知识库管理】页面上传文档。")
    st.stop()

# Load last selected KB from disk (shared with Quiz page)
from core.settings_utils import get_last_selected_kb, set_last_selected_kb
stored_kb = get_last_selected_kb()
default_index = kbs.index(stored_kb) if stored_kb and stored_kb in kbs else 0

selected_kb = st.sidebar.selectbox("📚 选择知识库", kbs, index=default_index, key="kb_selector_assistant")

# Save selection to disk when changed (only if different from stored)
if selected_kb != stored_kb:
    set_last_selected_kb(selected_kb)

# Initialize Agent
if "agent" not in st.session_state or st.session_state.get("agent_kb") != selected_kb:
    with st.spinner(f"正在加载知识库 {selected_kb}..."):
        st.session_state.agent = RAGAgent(kb_name=selected_kb)
        st.session_state.agent_kb = selected_kb
        
        # Auto-vectorization check
        count = st.session_state.agent.vector_store.get_collection_count()
        if count == 0:
            files = kb_manager.list_files(selected_kb)
            if files:
                st.info(f"📚 检测到知识库 '{selected_kb}' 尚未向量化，正在首次处理，这可能需要比较久的时间...")
                # Use a new spinner for the long task
                with st.spinner("正在进行向量化处理，请耐心等待..."):
                    kb_manager.rebuild_kb_index(selected_kb)
                st.success("✅ 向量化完成！")
                # Reload agent to see new data
                st.session_state.agent = RAGAgent(kb_name=selected_kb)
        
        st.session_state.messages = [
            {"role": "assistant", "content": f"👋 你好！我是基于 **{selected_kb}** 的智能助教。有什么我可以帮你的吗？"}
        ]
        # Reset uploader key
        st.session_state.uploader_key = 0

agent = st.session_state.agent

# Sidebar - Image Uploader
with st.sidebar:
    st.markdown("### 📸 题目助手")
    uploaded_file = st.file_uploader(
        "上传题目或图表截图", 
        type=["jpg", "png", "jpeg"],
        key=f"uploader_{st.session_state.get('uploader_key', 0)}" 
    )
    
    image_base64 = None
    if uploaded_file:
        st.image(uploaded_file, caption="已添加图片", use_container_width=True)
        image_base64 = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
    
    st.markdown("---")
    if st.button("🗑️ 清空对话历史"):
        st.session_state.messages = [
            {"role": "assistant", "content": f"对话已重置。我是基于 **{selected_kb}** 的智能助教。"}
        ]
        st.session_state.uploader_key = st.session_state.get("uploader_key", 0) + 1
        st.rerun()

# Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": f"👋 你好！我是基于 **{selected_kb}** 的智能助教。有什么我可以帮你的吗？"}
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🧑‍🎓" if message["role"] == "user" else "🦊"):
        if "image_base64" in message and message["image_base64"]:
            st.image(base64.b64decode(message["image_base64"]), width=300)
        st.markdown(message["content"])

# Input
if prompt := st.chat_input("请输入问题..."):
    # User message
    user_msg = {"role": "user", "content": prompt, "_needs_response": True}
    if image_base64:
        user_msg["image_base64"] = image_base64
    st.session_state.messages.append(user_msg)
    
    if uploaded_file:
        st.session_state.uploader_key = st.session_state.get("uploader_key", 0) + 1
    
    st.rerun()

# Response Logic - process if last user message needs a response
last_msg = st.session_state.messages[-1] if st.session_state.messages else None
needs_response = last_msg and last_msg.get("role") == "user" and last_msg.get("_needs_response", False)

if needs_response:
    prompt = last_msg["content"]
    current_image_data = last_msg.get("image_base64", None)
    
    with st.chat_message("assistant", avatar="🤖"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # 检查是否是简单的选择题回答
            is_simple_answer = len(prompt) < 10 and "选" in prompt
            
            # 检索上下文
            docs = []
            context = ""
            if not is_simple_answer:
                with st.spinner("正在检索资料..."):
                    context, docs = agent.retrieve_context(prompt)
            
            message_placeholder.markdown("🤔 正在生成回复...")
            
            from core.rag_agent import RAGAgent
            
            # 构建消息
            messages = [{"role": "system", "content": agent.system_prompt}]
            
            if st.session_state.messages[:-1]:
                clean_history = []
                for msg in st.session_state.messages[:-1][-5:]:
                    content = msg.get("content", "")
                    role = msg.get("role", "user")
                    clean_history.append({"role": role, "content": content})
                messages.extend(clean_history)
            
            if is_simple_answer:
                user_text = f"""(用户正在回答上一轮的选择题)
学生回答：{prompt}
请执行【作业批改】：判断对错并解析。
"""
            else:
                user_text = f"""请阅读资料回答问题。
=== 课程资料 ===
{context if context else "（未检索到资料，尝试基于常识回答）"}
=== 结束 ===
学生问题：{prompt}
"""
            
            if current_image_data:
                content_payload = [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{current_image_data}"}}
                ]
                current_model = agent.vl_model
            else:
                content_payload = user_text
                current_model = agent.model
            
            messages.append({"role": "user", "content": content_payload})
            
            # 流式调用 API
            stream = agent.client.chat.completions.create(
                model=current_model,
                messages=messages,
                temperature=0.3,
                max_tokens=1500,
                stream=True
            )
            
            # 流式显示
            for chunk in stream:
                if not chunk.choices:
                    continue
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            
            # 应用 LaTeX 格式修复
            full_response = agent.fix_latex_format(full_response)
            message_placeholder.markdown(full_response)
            
            # 显示参考资料
            if docs:
                with st.expander(f"📚 参考资料 ({len(docs)} 条)", expanded=False):
                    context_str = ""
                    for i, doc_info in enumerate(docs):
                        context_str += f"【资料 {i+1}】({doc_info['source_label']}):\n{doc_info['content']}\n\n"
                    st.markdown(context_str)
        
        except Exception as e:
            full_response = f"❌ 发生错误: {str(e)}"
            message_placeholder.markdown(full_response)
    
    # 标记已处理并保存响应
    last_msg["_needs_response"] = False
    st.session_state.messages.append({"role": "assistant", "content": full_response})


