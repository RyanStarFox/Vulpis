import streamlit as st
import os
import base64
import sys
import time

# Fix path to allow importing modules from root
sys.path.append(os.getcwd())
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit.components.v1 as components
from core.kb_manager import KBManager
from core import ui_components
from core import task_manager


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

@st.dialog("⚠️ 确认删除")
def confirm_delete_dialog(kb_name):
    st.warning(f'确定要永久删除知识库 "{kb_name}" 吗？\n此操作将删除所有文件和索引，且不可恢复。')
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("确认删除", type="primary", use_container_width=True):
            # Re-init manager to ensure context
            manager = KBManager()
            if manager.delete_kb(kb_name):
                st.success(f"已删除 {kb_name}")
                st.rerun()
            else:
                st.error("删除失败")

@st.dialog("✏️ 重命名知识库")
def rename_kb_dialog(old_name):
    st.info(f"当前知识库名称：**{old_name}**")
    new_name = st.text_input("新名称", placeholder="输入新的知识库名称")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("确认重命名", type="primary", use_container_width=True):
            if not new_name:
                st.error("请输入新名称")
            elif new_name == old_name:
                st.warning("新名称与旧名称相同")
            else:
                manager = KBManager()
                if manager.rename_kb(old_name, new_name):
                    st.success(f"已将 '{old_name}' 重命名为 '{new_name}'")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("重命名失败：新名称已存在或操作失败")
    with col2:
        if st.button("取消", use_container_width=True):
            st.rerun()


def render_task_progress(kb_name):
    """渲染任务进度条"""
    active_tasks = task_manager.get_kb_active_tasks(kb_name)
    recent_tasks = task_manager.get_kb_recent_tasks(kb_name, max_age_seconds=15)
    
    has_active_tasks = len(active_tasks) > 0
    
    # 显示正在进行的任务
    for task_id, task in active_tasks.items():
        task_type = task.get("type", "unknown")
        task_icons = {
            "upload": "📤",
            "rebuild": "🔄",
            "update": "⚡️",
            "indexing": "📚",
            "importing": "📥"
        }
        icon = task_icons.get(task_type, "⏳")
        
        # 任务类型名称映射
        type_names = {
            "upload": "上传处理",
            "rebuild": "重建索引",
            "update": "增量更新",
            "indexing": "文件索引",
            "importing": "文件夹导入"
        }
        type_name = type_names.get(task_type, "后台任务")
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 12px 16px; border-radius: 10px; margin-bottom: 8px;
                    color: white; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <span style="font-weight: 600;">{icon} {type_name} 进行中</span>
                <span style="opacity: 0.9; font-size: 0.9em;">{int(task['progress'] * 100)}%</span>
            </div>
            <div style="margin-top: 8px; font-size: 0.85em; opacity: 0.9;">{task['message']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Streamlit 进度条
        st.progress(task['progress'])
    
    # 显示最近完成的任务
    for task_id, task in recent_tasks.items():
        if task["status"] == "completed":
            st.success(f"✅ {task['message']}")
        elif task["status"] == "failed":
            st.error(f"❌ {task['message']}")
    
    return has_active_tasks


st.set_page_config(page_title="知识库管理", page_icon="logo.png", layout="wide")

# Sidebar CSS (已包含 <style> 标签)
st.markdown(ui_components.get_sidebar_css(), unsafe_allow_html=True)

# 页面样式
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    img { image-rendering: -webkit-optimize-contrast; }
    
    /* 进度条动画 */
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 25%, #764ba2 50%, #667eea 75%);
        background-size: 200% 100%;
        animation: shimmer 2s infinite;
    }
</style>
""", unsafe_allow_html=True)

# sidebar
ui_components.render_sidebar()

st.title("🗂️ 知识库管理")

# 全局任务状态提示
all_tasks = task_manager.get_tasks()
running_count = sum(1 for t in all_tasks.values() if t["status"] == "running")
if running_count > 0:
    st.info(f"⏳ 当前有 **{running_count}** 个后台任务正在运行，即使您离开此页面，任务也会继续处理。")
    if st.button("🔄 刷新状态", use_container_width=True):
        st.rerun()

kb_manager = KBManager()
kbs = kb_manager.list_kbs()

# --- Create New KB ---
with st.expander("➕ 新建知识库", expanded=False):
    new_kb_name = st.text_input("知识库名称", placeholder="例如: MyKnowledgeBase")
    if st.button("创建"):
        if new_kb_name:
            if kb_manager.create_kb(new_kb_name):
                st.success(f"知识库 {new_kb_name} 创建成功！")
                time.sleep(1)
                st.rerun()
            else:
                st.error("创建失败：知识库已存在或名称非法")
        else:
            st.warning("请输入名称")

st.markdown("---")

# --- Manage Existing KBs ---
if not kbs:
    st.info("暂无知识库")
else:
    st.markdown("### 现有知识库")
    
    # 按照您的要求，每个一级子文件夹（如 cs_math, docx_test 等）都是一个独立的知识库
    for kb in kbs:
        with st.expander(f"📁 {kb}", expanded=False):
            # --- 显示任务进度 ---
            has_active_tasks = render_task_progress(kb)
            
            # 如果有正在进行的任务，显示提示
            if has_active_tasks:
                st.caption("💡 后台任务进行中，您可以离开此页面，任务会继续运行")
            
            # --- Operation Buttons Section ---
            # Row 1: Normal Operations
            op_col1, op_col2, op_col3 = st.columns(3)
            
            with op_col1:
                if st.button("📂 打开本地文件夹", key=f"open_dir_{kb}", use_container_width=True, disabled=has_active_tasks):
                    kb_path = os.path.join(kb_manager.base_dir, kb)
                    import subprocess, platform
                    try:
                        if platform.system() == "Darwin":
                            subprocess.Popen(["open", kb_path])
                        elif platform.system() == "Windows":
                            os.startfile(kb_path)
                        else:
                            subprocess.Popen(["xdg-open", kb_path])
                        st.toast("已打开文件夹，变更文件后请点击【⚡️ 更新增量索引】")
                    except Exception as e:
                        st.error(f"打开文件夹失败: {e}")

            with op_col2:
                if st.button("⚡️ 更新增量索引", key=f"sync_{kb}", use_container_width=True, 
                            help="仅处理新增或删除的文件（后台运行）", disabled=has_active_tasks):
                    # 启动后台任务
                    task_id = task_manager.start_update_index_task(kb, KBManager)
                    st.success("✅ 已开始后台更新索引！您可以离开此页面")
                    time.sleep(0.5)
                    st.rerun()

            with op_col3:
                if st.button("🔄 重建索引 (全量)", key=f"reindex_{kb}", use_container_width=True, 
                            help="清空库并重新扫描（后台运行）", disabled=has_active_tasks):
                    # 启动后台任务
                    task_id = task_manager.start_rebuild_task(kb, KBManager)
                    st.success("✅ 已开始后台重建索引！您可以离开此页面")
                    time.sleep(0.5)
                    st.rerun()

            # Row 2: Manage Operations (Rename / Delete)
            man_col1, man_col2 = st.columns(2)
            with man_col1:
                if st.button("✏️ 重命名知识库", key=f"rename_kb_{kb}", use_container_width=True, disabled=has_active_tasks):
                    rename_kb_dialog(kb)
            
            with man_col2:
                if st.button("🗑️ 删除整个知识库", key=f"del_kb_{kb}", type="primary", use_container_width=True, disabled=has_active_tasks):
                    confirm_delete_dialog(kb)

            st.markdown("---")

            # --- Content Section ---
            cont_col1, cont_col2 = st.columns([2, 1], gap="medium")
            
            # File List
            with cont_col1:
                files = kb_manager.list_files(kb)
                st.markdown(f"**包含文档 ({len(files)}):**")
                if files:
                    for f in files:
                        c1, c2 = st.columns([4, 1])
                        c1.text(f"📄 {f}")
                        if c2.button("🗑️", key=f"del_file_{kb}_{f}", disabled=has_active_tasks):
                            kb_manager.delete_file(kb, f)
                            st.rerun()
                else:
                    st.caption("_暂无文档_")

            # Upload Section
            with cont_col2:
                st.markdown("**📤 上传新文档:**")
                st.caption("💡 支持 PDF, PPTX, DOCX, MD, TXT")
                
                uploader_key_name = f"uploader_key_{kb}"
                current_key_val = st.session_state.get(uploader_key_name, 0)
                
                uploaded_files = st.file_uploader(
                    f"上传文件到 {kb}", 
                    accept_multiple_files=True, 
                    type=["pdf", "pptx", "docx", "md", "txt"],
                    key=f"up_{kb}_{current_key_val}",
                    label_visibility="collapsed",
                    disabled=has_active_tasks
                )

                if uploaded_files:
                    st.caption(f"已选择 {len(uploaded_files)} 个文件")
                    if st.button("确认上传并处理", key=f"btn_up_{kb}", type="primary", 
                                use_container_width=True, disabled=has_active_tasks):
                        # 准备文件数据（在主线程中读取）
                        files_data = []
                        for uf in uploaded_files:
                            files_data.append((uf.name, uf.getbuffer().tobytes()))
                        
                        # 启动后台任务
                        task_id = task_manager.start_upload_task(kb, files_data, KBManager)
                        
                        st.success("✅ 已开始后台上传处理！")
                        st.session_state[uploader_key_name] = current_key_val + 1
                        time.sleep(0.5)
                        st.rerun()

