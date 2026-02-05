import streamlit as st
import time
import base64
import os
import sys

# Fix path to allow importing modules from root
sys.path.append(os.getcwd())
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit.components.v1 as components
from core.kb_manager import KBManager
from core import ui_components
from core.rag_agent import RAGAgent

from core.question_db import QuestionDB # Import DB

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

st.set_page_config(page_title="智能大纲生成", page_icon="logo.png", layout="wide")

st.markdown(f"""
<style>
    .block-container {{ padding-top: 2rem; }}
    img {{ image-rendering: -webkit-optimize-contrast; }}
    
    /* Sidebar Styles from ui_components */
    {ui_components.get_sidebar_css()}
</style>
""", unsafe_allow_html=True)

# sidebar
ui_components.render_sidebar()

st.title("📑 智能大纲生成")

kb_manager = KBManager()
question_db = QuestionDB() # Initialize DB
kbs = kb_manager.list_kbs()

if not kbs:
    st.warning("⚠️ 请先在【知识库管理】中添加知识库")
    st.stop()

# Define layout columns for header
col_kb, col_btn = st.columns([3, 1], vertical_alignment="bottom")

with col_kb:
    # Get last selected from session state or default
    default_kb_index = 0
    if "current_view_kb" in st.session_state and st.session_state.current_view_kb in kbs:
        default_kb_index = kbs.index(st.session_state.current_view_kb)
    
    selected_kb = st.selectbox("📚 选择知识库", kbs, index=default_kb_index)

# Handle KB switch: Clear state to force reload
if "current_view_kb" not in st.session_state or st.session_state.current_view_kb != selected_kb:
    st.session_state.current_view_kb = selected_kb
    st.session_state.pop("outline_result", None)
    st.session_state.pop("pdf_data", None) # Clear generated PDF cache

# Now fetch the status for the ACTUAL selected KB
existing_outline = question_db.get_outline(selected_kb)
current_status = existing_outline.get("status") if existing_outline else None

def run_background_generate(kb_name):
    """后台生成函数"""
    try:
        # 使用独立的 DB 和 Agent 实例
        db = QuestionDB()
        agent = RAGAgent(kb_name=kb_name)
        # 记录开始处理
        db.save_outline(kb_name, "（大纲正在后台生成中，请耐心等待...）", status="processing")
        
        # 执行生成
        outline_md = agent.generate_outline()
        
        # 记录完成
        db.save_outline(kb_name, outline_md, status="completed")
    except Exception as e:
        # 记录失败
        db = QuestionDB()
        db.save_outline(kb_name, f"❌ 生成失败: {str(e)}", status="failed")

with col_btn:
    btn_label = "🚀 生成大纲" if current_status != "completed" else "🔄 重新生成"
    if st.button(btn_label, type="primary", use_container_width=True):
        # Auto-vectorization check
        temp_agent = RAGAgent(kb_name=selected_kb)
        count = temp_agent.vector_store.get_collection_count()
        if count == 0:
            files = kb_manager.list_files(selected_kb)
            if files:
                st.info(f"📚 检测到知识库 '{selected_kb}' 尚未向量化，正在首次处理...")
                with st.spinner("正在向量化..."):
                    kb_manager.rebuild_kb_index(selected_kb)
            else:
                st.error("⚠️ 该知识库为空，请先上传文档。")
                st.stop()
        
        # Start background thread
        import threading
        thread = threading.Thread(target=run_background_generate, args=(selected_kb,))
        thread.daemon = True
        thread.start()
        
        # Set local status to avoid race condition before first DB write in thread
        question_db.save_outline(selected_kb, "（生成中...）", status="processing")
        st.success("✅ 已开始后台生成！")
        time.sleep(0.5)
        st.rerun()

# Check for existing outline and status
if current_status == "processing":
    st.info("⏳ **大纲正在生成/修改中...**")
    if st.button("🔄 刷新查看状态", use_container_width=True):
        st.rerun()
    st.stop()

if existing_outline and current_status == "completed" and "outline_result" not in st.session_state:
    st.session_state.outline_result = existing_outline["content"]
    st.info(f"📅 已加载历史大纲 (生成时间: {time.strftime('%Y-%m-%d %H:%M', time.localtime(existing_outline['timestamp']))})")

if current_status == "failed":
    st.error(existing_outline["content"])

if "outline_result" in st.session_state:
    outline = st.session_state.outline_result
    
    st.markdown("### 📥 下载大纲")
    
    # Helper for Auto-Download (defined once)
    def auto_download_file(data, filename, mime_type, key_suffix, success_msg):
        import base64
        import time as t
        b64 = base64.b64encode(data).decode()
        link_id = f"auto_dl_{key_suffix}_{int(t.time())}"
        
        html = f"""
            <a id="{link_id}" href="data:{mime_type};base64,{b64}" download="{filename}" style="display:none;">Download</a>
            <script>
                (function() {{
                    setTimeout(function() {{
                        var link = document.getElementById("{link_id}");
                        if (link) link.click();
                    }}, 150);
                }})();
            </script>
        """
        st.markdown(html, unsafe_allow_html=True)
        st.success(success_msg)
        st.toast("已保存在系统“下载”文件夹")
        
        st.download_button(
            label=f"💾 点击保存 {filename}",
            data=data,
            file_name=filename,
            mime=mime_type,
            type="primary",
            use_container_width=True,
            key=f"manual_dl_btn_{key_suffix}_{int(t.time())}"
        )
    
    # Download buttons row - only buttons, no generation logic here
    dl_col1, dl_col2, dl_col3 = st.columns(3)
    
    with dl_col1:
        if st.button("⬇️ 下载 Markdown (.md)", use_container_width=True, type="secondary", key="dl_md_btn_v4"):
            auto_download_file(outline.encode('utf-8'), f"{selected_kb}_大纲.md", "text/markdown", "md", "✅ Markdown 已就绪")
    
    with dl_col2:
        gen_pdf_clicked = st.button("⬇️ 生成并下载 PDF", use_container_width=True, type="secondary", key="gen_pdf_btn_final")
    
    with dl_col3:
        gen_docx_clicked = st.button("⬇️ 生成并下载 Word", use_container_width=True, type="secondary", key="gen_docx_btn")
    
    # PDF Generation - outside columns
    if gen_pdf_clicked:
        import subprocess, tempfile, os, re
        
        common_paths = ["/opt/homebrew/bin", "/usr/local/bin", "/Library/TeX/texbin"]
        for p in common_paths:
            if os.path.exists(p) and p not in os.environ["PATH"]:
                os.environ["PATH"] += os.pathsep + p
                
        try:
            with st.spinner("正在通过 Pandoc 生成 PDF..."):
                outline_safe = outline
                outline_safe = re.sub(r'(?<!\\)\$[ \t]+', '$', outline_safe)                
                outline_safe = re.sub(r'[ \t]+(?<!\\)\$', '$', outline_safe)
                outline_safe = outline_safe.replace(r"\symcal", r"\mathcal")
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as md_file:
                    md_file.write(outline_safe)
                    md_path = md_file.name
                    
                pdf_path = md_path.replace('.md', '.pdf')
                from core.settings_utils import get_pandoc_path
                pandoc_cmd = get_pandoc_path() or 'pandoc'
                
                cmd = [
                    pandoc_cmd, md_path, '-o', pdf_path,
                    '--pdf-engine=xelatex',
                    '-V', 'CJKmainfont=Heiti SC',
                    '-V', 'geometry:margin=2.5cm',
                    '-V', 'fontsize=11pt',
                    '--highlight-style=tango'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0 and os.path.exists(pdf_path):
                    with open(pdf_path, 'rb') as f:
                        pdf_bytes = f.read()
                    auto_download_file(pdf_bytes, f"{selected_kb}_大纲.pdf", "application/pdf", "pdf", "✅ PDF 生成成功！")
                else:
                    st.error("❌ PDF 生成失败")
                    with st.expander("📜 错误日志"):
                        st.code(result.stderr, language="text")
                    if "xelatex" in (result.stderr or "").lower():
                        st.info("💡 提示：缺少 XeLaTeX 引擎。")
                        
        except Exception as e:
            st.error(f"出错: {e}")
        finally:
            if 'md_path' in locals() and os.path.exists(md_path): os.unlink(md_path)
            if 'pdf_path' in locals() and os.path.exists(pdf_path): os.unlink(pdf_path)

    # Word Generation - outside columns
    if gen_docx_clicked:
        import subprocess, tempfile, os, re
        
        try:
            with st.spinner("正在转换 Word 文档..."):
                outline_safe = outline.replace(r"\symcal", r"\mathcal")
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as md_file:
                    md_file.write(outline_safe)
                    md_path = md_file.name
                
                docx_path = md_path.replace('.md', '.docx')
                from core.settings_utils import get_pandoc_path
                pandoc_cmd = get_pandoc_path() or 'pandoc'
                
                cmd = [
                    pandoc_cmd, md_path, '-o', docx_path,
                    '--highlight-style=tango'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0 and os.path.exists(docx_path):
                    with open(docx_path, 'rb') as f:
                        docx_bytes = f.read()
                    auto_download_file(docx_bytes, f"{selected_kb}_大纲.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx", "✅ Word 生成成功！")
                else:
                    st.error("❌ Word 生成失败")
                    with st.expander("📜 错误日志"):
                        st.code(result.stderr, language="text")
                        
        except Exception as e:
            st.error(f"出错: {e}")
        finally:
             if 'md_path' in locals() and os.path.exists(md_path): os.unlink(md_path)
             if 'docx_path' in locals() and os.path.exists(docx_path): os.unlink(docx_path)


    st.markdown("---")
    st.markdown("### 📝 预览与修改")
    
    tab_view, tab_refine = st.tabs(["👁️ 预览大纲", "✏️ 修改大纲"])
    
    with tab_view:
        st.markdown(outline)
        
    with tab_refine:
        st.info("💡 如果对大纲不满意，可以提出修改意见让 AI 进行调整（例如：'增加关于动态规划的章节' 或 '精简第一章的内容'）。")
        user_feedback = st.text_area("请输入你的修改意见：", height=100)
        if st.button("✨ 提交修改意见", type="primary"):
            if user_feedback.strip():
                # 后台修改函数
                def run_background_refine(kb_name, current_outline, feedback):
                    try:
                        db = QuestionDB()
                        db.save_outline(kb_name, "（正在根据您的意见调整大纲...）", status="processing")
                        
                        agent = RAGAgent(kb_name=kb_name)
                        new_outline = agent.refine_outline(current_outline, feedback)
                        
                        db.save_outline(kb_name, new_outline, status="completed")
                    except Exception as e:
                        db = QuestionDB()
                        db.save_outline(kb_name, f"❌ 修改失败: {str(e)}", status="failed")
                
                # 启动后台线程
                import threading
                thread = threading.Thread(target=run_background_refine, args=(selected_kb, outline, user_feedback))
                thread.daemon = True
                thread.start()
                
                question_db.save_outline(selected_kb, "（修改中...）", status="processing")
                st.success("✅ 已开始后台修改！请稍后刷新页面查看结果。")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("请先输入修改意见。")

    st.markdown("---")


