import streamlit as st
import base64
import os
import sys

# Fix path to allow importing modules from root
sys.path.append(os.getcwd())
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit.components.v1 as components
from core import ui_components

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

st.set_page_config(page_title="使用说明", page_icon="logo.png", layout="wide")

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

# Custom CSS for card styling
# Initialize navigation state
if 'help_section' not in st.session_state:
    st.session_state.help_section = None

# Base CSS (Always applies)
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    img { image-rendering: -webkit-optimize-contrast; }
    
    .instruction-card {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 10px;
        width: 100%;
        height: 100%;
        transition: transform 0.2s, box-shadow 0.2s;
        cursor: pointer;
    }
    
    .instruction-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-color: #FF4B4B;
    }
    
    .card-icon {
        font-size: 2.5rem;
        margin-bottom: 8px;
        display: block;
    }
    
    .card-title {
        font-size: 1.15rem;
        font-weight: 600;
        margin-bottom: 6px;
        color: var(--text-color);
    }
    
    .card-desc {
        font-size: 0.85rem;
        color: #888;
        line-height: 1.35;
        min-height: 3.2em;
    }
    
    .feature-title {
        font-size: 1.5rem;
        font-weight: 600;
        margin: 20px 0;
        color: #FF4B4B;
    }
    
    .step-item {
        background-color: rgba(128, 128, 128, 0.05);
        padding: 10px 15px;
        border-radius: 6px;
        margin-bottom: 8px;
        border-left: 3px solid #FF4B4B;
    }

</style>
""", unsafe_allow_html=True)

# Conditional CSS for Home View Only (Fixed Layout)
if st.session_state.help_section is None:
    st.markdown("""
    <style>
        /* 核心布局调整：消除滚动条 - 仅在导航页生效 */
        .block-container { 
            padding-bottom: 0rem;
        }
        
        /* 仅隐藏 Streamlit 页脚, 保留 header 以便侧边栏按钮正常工作 */
        footer {display: none;}
    </style>
    """, unsafe_allow_html=True)

# Header
st.title("📚 使用说明书")
st.caption("点击下方卡片查看详细功能说明")
st.markdown("---")

# Main Navigation Grid
if st.session_state.help_section is None:
    # Feature configurations
    features = [
        {
            "id": "ai_tutor",
            "icon": "🧠",
            "title": "智能助教",
            "desc": "智能问答助手，解答疑问，提供来源"
        },
        {
            "id": "practice",
            "icon": "📝",
            "title": "做题练习",
            "desc": "自动生成题目，AI 批改，提供解析"
        },
        {
            "id": "mistakes",
            "icon": "📓",
            "title": "错题整理",
            "desc": "自动或手动管理错题，练习错题"
        },
        {
            "id": "outline",
            "icon": "📑",
            "title": "大纲生成",
            "desc": "分析知识库生成的复习大纲"
        },
        {
            "id": "kb",
            "icon": "📚",
            "title": "知识库管理",
            "desc": "上传和管理课程资料"
        },
        {
            "id": "settings",
            "icon": "⚙️",
            "title": "系统设置",
            "desc": "API 配置、模型选择、参数配置"
        }
    ]

    # Render grid (3 columns)
    cols = st.columns(3)
    for i, feature in enumerate(features):
        with cols[i % 3]:
            # Create a clickable card using st.button
            # Note: We use a little CSS hack to make the button look like a card
            # Or simpler: Just use container + button
            with st.container(border=True):
                st.markdown(f"""
                <div style="text-align: center;">
                    <div style="font-size: 3rem; margin-bottom: 10px;">{feature['icon']}</div>
                    <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 5px;">{feature['title']}</div>
                    <div style="color: #666; font-size: 0.9rem; min-height: 40px;">{feature['desc']}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("查看详情", key=f"btn_{feature['id']}", use_container_width=True):
                    st.session_state.help_section = feature['id']
                    st.rerun()

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #888; font-size: 0.8rem;">
        CS4314 智能课程助教系统 v2.0
    </div>
    """, unsafe_allow_html=True)

else:
    # Detail View
    if st.button("← 返回功能列表"):
        st.session_state.help_section = None
        st.rerun()
    
    section = st.session_state.help_section
    
    if section == "ai_tutor":
        st.header("🧠 智能助教：你的 24 小时专属补习老师")
        st.info("💡 想象一下，有一位过目不忘的学霸同桌，他背下了你所有的课本和 PPT，随时准备回答你的问题。这就是「智能助教」。")

        st.markdown("### 🔥 它可以帮你做什么？")
        col1, col2 = st.columns([1, 1])
        with col1:
             st.markdown("""
             **1. 哪里不会问哪里**
             * 遇到不懂的概念（比如“什么是自注意力机制？”），直接问它。它会用通俗易懂的话给你讲明白。
             * **精准定位**：它不仅告诉你答案，还会告诉你这个知识点在课本的 **第几页**，方便你回去查阅。
             
             **2. 看图说话 (多模态能力)**
             * 遇到看不懂的 **物理公式截图**？
             * 遇到复杂的 **生物流程图**？
             * 直接把图片发给它，并在输入框问：“请解释一下这张图是什么意思”，它就能看懂并给你讲解。
             """)
        with col2:
             st.markdown("""
             **3. 跨章节串联知识**
             * 它可以同时参考第一章和第五章的内容，帮你总结知识点之间的联系。
             * 比如问：“这一章提到的理论和之前学的有什么区别？”
             
             **4. 像聊天一样学习**
             * 没听懂？没关系，接着问：“能再简单点解释吗？”或者“能举个生活中的例子吗？”
             * 它记得你们之前的对话，就像真的在聊天一样。
             """)
        
        st.markdown("---")
        st.markdown("### 🎓 提问小贴士")
        st.success("🌟 秘诀：把问题问得越具体，得到的答案就越好！比如：\n\n❌ “讲讲力学”\n✅ “请结合 Lecture 3 的内容，解释一下牛顿第二定律在斜面滑块问题中的应用”")

    elif section == "practice":
        st.header("📝 智能刷题：考前自测神器")
        st.info("💡 无论是期中考还是期末考，“刷题”永远是最有效的复习方式。这里有你的专属题库。")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🎯 怎么开始刷题？")
            st.markdown("""
            **模式一：针对复习 (知识库自测)**
            * 比如明天要考“第三章”，你就选择“第三章”的知识库。
            * AI 会现场阅读这一章的文档，为你“现编”题目，确保考点覆盖全。
            
            **模式二：综合模拟 (题库模式)**
            * 如果你已经导入了历年真题库，选择它，系统会随机抽题，模拟真实考试的感觉。
            """)
        
        with col2:
            st.markdown("### 📊 做完题能得到什么？")
            st.markdown("""
            * **秒出成绩**：点一下选项，立马告诉你对错（绿色✅/红色❌）。
            * **超级解析**：
              * 选对了？它会夸你并巩固一下知识点。
              * **选错了？**这是重点！它会详细告诉你**为什么选错**，以及正确答案的推理过程。
            * **自动收集**：做错的题会自动飞进你的「错题本」，不用你手动抄写。
            """)

    elif section == "mistakes":
        st.header("📓 错题本：消灭你的知识盲区")
        st.info("💡 俗话说“好记性不如烂笔头”，但现在不需要笔头了，AI 帮你自动整理。")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🚀 把错题装进篮子里")
            st.markdown("""
            **1. 自动同步**
            * 你在“做题练习”里做错的每一道题，都会自动出现在这里。
            
            **2. 拍照及录入 (黑科技！)**
            * 试卷发下来了，只有几道题做错了，不想抄？
            * 点击 **“➕ 手动添加”** -> **上传照片**。
            * 系统会自动识别图片上的文字（OCR），把题目和选项变成电子版存进去。你只需要动动手指微调一下。
            """)

        with col2:
            st.markdown("### 🔄 科学复习法")
            st.markdown("""
            系统会给每个错题打上标签：
            * 🔴 **陌生**：刚刚做错，或者很久没复习的题。**优先复习这些！**
            * 🟡 **模糊**：有点印象，但在这个坑里摔过各跤。
            * 🟢 **掌握**：已经完全搞懂了。可以把它移进“归档箱”，眼不见心不烦。
            """)

    elif section == "outline":
        st.header("📑 大纲生成：一键把书读薄")
        st.info("💡 面对几百页的 PPT 头大吗？这个功能帮你把“砖头”变成“薄薄的几页纸”。")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🌟 魔法步骤")
            st.markdown(""" 
            1. 选择你要复习的资料包（比如“期末总复习”）。
            2. 点击 **“生成大纲”** 按钮。
            3. 等待几十秒... ✨
            4. 你会得到一份结构清晰、重点突出的 **复习提纲**，包含了核心定义、公式和关键结论。
            """)
            
        with col2:
            st.markdown("### ✏️ 它是听话的")
            st.markdown("""
            觉得生成的大纲太简单？或者漏了什么？
            在右边的框里告诉它：
            > "请把关于‘光合作用’的那一节写得详细这一波，最好加上反应公式。"
            
            AI 会马上重新修改大纲，直到你满意为止。
            最后，你可以把它 **复制** 下来，打印或者存到你的笔记软件里。
            """)

    elif section == "kb":
        st.header("📚 知识库管理：投喂 AI 的大脑")
        st.info("💡 这里是 AI 的“图书馆”。必须完成下面 **两步**，AI 才能学会你的课件。")
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("### 📂 第一步：上传资料")
            st.info("先把书放进书架")
            st.markdown("""
            **1. 打开文件夹**
            点击 **“📂 打开本地文件夹”** 按钮。系统会弹出一个文件夹窗口。
            
            **2. 拖入文件**
            把你的课件 (`PDF`, `PPT`, `Word`) 直接 **拖** 进这个窗口里。
            
            **💡 小建议**
            文件名写清楚点，比如《物理-第一章.pdf》，方便以后查找。
            """)
            
        with c2:
            st.markdown("### ⚡️ 第二步：建立索引")
            st.error("⚠️ 必须做这一步，否则 AI 看不见！")
            st.markdown("""
            **动作 A：⚡️ 更新增量索引 (推荐)**
            * **只需 3 秒**。
            * 告诉 AI：“我刚放了几本新书，你快读一下。”
            * 适合日常加几个文件。
            * 删除文件也需要更新索引哦～
            
            **动作 B：🔄 重建知识库索引**
            * **彻底重读**。
            * 告诉 AI：“把以前记的都忘掉，重新读一遍。”
            * 适合出错了或者想重置的时候。
            """)

    elif section == "settings":
        st.header("⚙️ 系统设置：控制室")
        st.markdown("这里是给高级玩家准备的，通常情况下默认设置这就够用了。")
        
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("AI模型配置 (重要)")
            st.markdown("""
            * **API Key (密钥)**：
            * 就像你家门的**钥匙**。没有它，进不去 AI 的大门。请在对应的官网（如 DeepSeek, OpenAI）申请。
            
            * **Base URL (服务地址)**：
            * AI 住在哪？你**必须**填它们的地址才能访问到它，比如：
                * `https://api.deepseek.com/v1`
                * `https://api.openai.com/v1`
                * `https://dashscope.aliyuncs.com/compatible-mode/v1`
                * `https://open.bigmodel.cn/api/paas/v4`

            
            * **Model Name (模型代号)**：⚠️ **千万别填错！**
            * 这是 AI 的“身份证号”，差一个字母、大小写都不行，否则会报错。
            * 常见代号：`deepseek-chat`, `qwen-max`, `gpt-4o`。
            * **切记**：不要自己乱起名字，一定要去官网查对应的 `Model Name`。
            """)
        
        with c2:
            st.subheader("🔍 检索与RAG配置")
            st.markdown("""
            * **混合检索**：开启后，AI 会同时用“关键词匹配”（像查字典）和“语义理解”（像读懂意思）两种方式找答案，准确率更高。
            * **混合搜索权重 (Alpha)**：0到1之间。0.5代表平衡。接近1更像普通搜索（关键词），接近0更像语义搜索。
            * **Top K**：AI 回答问题时，参考多少个文档片段。默认 6 个。
            * **出题候选池大小**：解决题目雷同问题。
                * **随机出题候选池**：未指定主题时使用，默认 100。范围越大，题目越不重复。
                * **指定主题候选池**：指定主题时使用，默认 30。范围越小，题目越聚焦于该主题。
            * **出题上下文长度**：给 AI 出题用的资料长度。默认 2000 字符。
            * **对话记忆轮数**：AI 能记得住你们最近聊过的多少句话。默认 10 句。
            """)

            st.subheader("🖊️ 文本处理配置")
            st.markdown("""
            * **切分块大小 (Chunk Size)**：把长文档切成小块。默认 1000 字符。块太小没上下文，太大模型吃不消。
            * **重叠大小 (Overlap)**：相邻两个块之间重复的内容长度，防止把一句话切断。默认 200。
            * **模型最大上下文**：模型一次能处理的最大 Token 数。
            * **长度容错 & 重叠容错**：微调参数。允许切分时有少许误差，优先保证句子不被切断。
            """)

        st.subheader("🛠️ 工具配置")
        st.markdown("""
        * **Pandoc 路径**：
          * PDF 生成功能依赖 Pandoc。系统通常能自动找到它。
          * 如果提示“未找到命令”，请在这里手动填入 `pandoc` 的完整路径（例如 `/usr/local/bin/pandoc`）。
          * 安装教程：<a href="https://pandoc.org/installing.html" target="_blank">Pandoc 官网</a>
          * (如果链接无法点击，请复制地址至浏览器: `https://pandoc.org/installing.html`)
        """, unsafe_allow_html=True)
        
        st.caption("记得修改完后点击最下方的 **“💾 保存并应用”** 噢！")
        
    st.markdown("---")
