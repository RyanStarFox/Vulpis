import streamlit as st
import time
import json
import threading
import base64
import os
import sys

# Fix path to allow importing modules from root
sys.path.append(os.getcwd())
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit.components.v1 as components
from core.question_db import QuestionDB
from openai import OpenAI
from core.config import OPENAI_API_KEY, OPENAI_API_BASE, VL_MODEL_NAME, MODEL_NAME
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

st.set_page_config(page_title="错题整理", page_icon="logo.png", layout="wide")

# 1. Inject sidebar CSS separately (No f-string conflict)
st.markdown(ui_components.get_sidebar_css(), unsafe_allow_html=True)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    img { image-rendering: -webkit-optimize-contrast; }
</style>
""", unsafe_allow_html=True)

# sidebar
ui_components.render_sidebar()

st.title("📓 错题整理")

# Page Context Management: Reset dialogs when entering from another page
if st.session_state.get("last_page") != "mistakes":
    st.session_state.active_dialog_id = None
    st.session_state.active_dialog_type = None
    st.session_state.last_page = "mistakes"

# 自定义 CSS 样式
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    img { image-rendering: -webkit-optimize-contrast; }
    /* 全局按钮样式优化 - 仅限主内容区域 */
    [data-testid="stMain"] .stButton button {
        border-radius: 8px !important;
        border: 1px solid #e8e8e8;
        transition: all 0.3s ease;
        padding-top: 0.2rem !important;
        padding-bottom: 0.2rem !important;
        height: auto !important;
        min-height: 0px !important;
    }
    
    [data-testid="stMain"] .stButton button:hover {
        border-color: #FF4B4B !important;
        background-color: #FFF5F5 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(255,75,75,0.1);
    }
    
    /* 调整查看详情按钮的高度 */
    .view-det-btn button {
        padding-top: 0.1rem !important;
        padding-bottom: 0.1rem !important;
    }

    /* 保证垂直居中 */
    [data-testid="stHorizontalBlock"] {
        align-items: center;
    }

    /* 紧凑化带边框的容器 */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 0.05rem 0.5rem !important; /* Extremely minimal vertical padding */
        gap: 0px !important;
    }
    
    /* 强制水平块 (columns row) 垂直居中及高度控制 */
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] {
        align-items: center !important;
        min-height: 24px !important; /* Reduced min-height */
        height: auto !important;
    }
    
    /* 强制每个列垂直居中其内容 */
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="column"] {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 24px !important; /* Match horizontal block */
    }
    
    /* 强制列内所有子元素也居中 */
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="column"] > div {
        display: flex !important;
        align-items: center !important;
        width: 100%;
        min-height: 24px !important;
    }

    /* Checkbox 样式重置 */
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stCheckbox"] {
        min-height: unset !important;
        height: 24px !important;
        margin: 0px !important;
        padding: 0px !important;
        justify-content: center !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stCheckbox"] label {
        min-height: unset !important;
        margin: 0px !important;
        padding: 0px !important;
    }
    
    /* Markdown 容器垂直居中 */
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stMarkdownContainer"] {
        display: flex !important;
        align-items: center !important;
        min-height: 24px !important;
    }
    
    /* Markdown 文本样式 */
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stMarkdownContainer"] p {
        margin: 0px !important;
        padding: 0px !important;
        line-height: 1.2 !important; /* Tighter line height */
        font-size: 15px !important;
    }
    
    /* 按钮容器样式 */
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stButton"] {
        margin: 0px !important;
        padding: 0px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 24px !important;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stButton"] button {
        margin: 0px !important;
        padding: 0.1rem 0.5rem !important; /* Smaller button padding */
        min-height: 24px !important;
        height: 24px !important;
        line-height: 1 !important;
    }
    
    
    
    /* Primary按钮样式统一 */
    .stButton button[kind="primary"] {
        background-color: #FF4B4B;
        color: white;
        border: 2px solid #FF4B4B;
    }
    
    .stButton button[kind="primary"]:hover {
        background-color: #FF3333 !important;
        border-color: #FF3333 !important;
        color: white !important;
    }
    
    /* 菜单按钮样式 */
    button[kind="secondary"] {
        background: transparent;
        border: 1px solid #e0e0e0;
    }
    button[kind="secondary"]:hover {
        background: #f5f5f5;
        border-color: #FF4B4B !important;
    }
</style>
""", unsafe_allow_html=True)

question_db = QuestionDB()

# Session State 初始化
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "list"  # list: 错题本列表, detail: 错题详情

if "selected_mistake_book" not in st.session_state:
    st.session_state.selected_mistake_book = "默认错题本"

if "mistake_index" not in st.session_state:
    st.session_state.mistake_index = 0

if "mistake_mode" not in st.session_state:
    st.session_state.mistake_mode = "list"  # list, quiz

if "selected_questions" not in st.session_state:
    st.session_state.selected_questions = set()

# --- Global Helper Functions & Dialogs ---

def process_question_async(rid, book_name, q_c, q_o, q_correct, q_e, ocr_b64, attachment_b64, f_type):
    try:
        from openai import OpenAI
        import json
        import os
        import re
        from dotenv import load_dotenv
        from core.question_db import QuestionDB
        from core import config
        
        # 强制重新加载环境变量
        load_dotenv(override=True)
        
        # Fetch credentials
        vl_key = os.getenv("VL_API_KEY") or os.getenv("OPENAI_API_KEY")
        vl_base = os.getenv("VL_API_BASE") or os.getenv("OPENAI_API_BASE")
        vl_model = os.getenv("VL_MODEL_NAME", "gpt-4o")
        
        text_key = os.getenv("OPENAI_API_KEY") or vl_key
        text_base = os.getenv("OPENAI_API_BASE") or vl_base
        text_model = os.getenv("MODEL_NAME", vl_model)

        # Check API Key
        if not vl_key:
             print("Process Error: Missing API Key")
             try:
                 qk = QuestionDB()
                 qk.update_result(rid, book_name, {
                     "status": "failed", 
                     "question": "❌ API Key 未配置", 
                     "explanation": "后台进程无法读取 API Key。请在设置中配置。"
                 })
             except Exception as db_e:
                 print(f"Failed to update DB: {db_e}")
             return

        # Initialize clients
        vl_client = config.get_openai_client(api_key=vl_key, base_url=vl_base)
        text_client = config.get_openai_client(api_key=text_key, base_url=text_base)
        
        # Helper function to clean JSON responses
        def clean_json_string(s):
            if not s: return "{}"
            s = s.strip()
            # Remove markdown code blocks
            s = re.sub(r'^```json\s*', '', s, flags=re.MULTILINE)
            s = re.sub(r'^```\s*', '', s, flags=re.MULTILINE)
            s = re.sub(r'\s*```$', '', s, flags=re.MULTILINE)
            # Extract JSON object
            start = s.find('{')
            end = s.rfind('}')
            if start != -1 and end != -1:
                s = s[start:end+1]
            
            # CRITICAL FIX for LaTeX in JSON:
            # Problem: \nabla -> \n (newline) + "abla", \rho -> \r + "ho", \frac -> \f + "rac"
            # Solution: Escape ALL backslashes, then restore only intended newlines
            
            # Step 1: Escape ALL backslashes (turn \ into \\)
            s = s.replace('\\', '\\\\')
            
            # Step 2: Restore intended escape sequences:
            # - \\n followed by digit, space, punctuation, or quote → real newline (\n)
            # - \\n followed by letter → LaTeX command like \nabla, keep as \\n
            # Same logic for \\r, \\t, etc.
            
            # Restore \\n → \n only when NOT followed by a letter (i.e., it's a real newline)
            s = re.sub(r'\\\\n(?![a-zA-Z])', r'\\n', s)
            # Restore \\r → \r only when NOT followed by a letter
            s = re.sub(r'\\\\r(?![a-zA-Z])', r'\\r', s)
            # Restore \\t → \t only when NOT followed by a letter  
            s = re.sub(r'\\\\t(?![a-zA-Z])', r'\\t', s)
            # Restore \\\\ → \\ (escaped backslash for JSON)
            s = s.replace('\\\\\\\\', '\\\\')
            # Restore \\" → \" (escaped quote)
            s = s.replace('\\\\"', '\\"')
            
            return s

        # ========== STAGE 1: PURE OCR ==========
        print("Starting Stage 1: Pure OCR...")
        source_text = q_c if q_c else ""
        
        if ocr_b64 and not source_text:
            # Simple OCR-only prompt
            ocr_prompt = r"""
你是一个OCR识别专家。请将图片中的文字完整提取出来。

**格式要求**：
- 数学公式使用 LaTeX，必须用 $...$ 或 $$...$$ 包裹
- 示例：$\sqrt{\dfrac{a^2}{b}}$ 而不是 √a²/b
- 保持原有换行和列表格式
- 不要添加任何解释或分析

直接输出文字内容即可，不需要JSON格式。
"""
            try:
                ocr_resp = vl_client.chat.completions.create(
                    model=vl_model,
                    messages=[
                        {"role": "system", "content": ocr_prompt},
                        {"role": "user", "content": [
                            {"type": "text", "text": "请提取这张图片中的文字："},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{ocr_b64}"}}
                        ]}
                    ],
                    temperature=0.1,
                    max_tokens=2048
                )
                source_text = ocr_resp.choices[0].message.content.strip()
                print(f"Stage 1 OCR Output: {source_text[:100]}...")
            except Exception as e:
                print(f"Stage 1 OCR Error: {e}")
                qk = QuestionDB()
                qk.update_result(rid, book_name, {
                    "status": "failed",
                    "question": "❌ OCR识别失败",
                    "explanation": f"图像识别错误: {str(e)}"
               })
                return
        
        if not source_text:
            print("No source text available")
            # Update status to failed with helpful message
            qk = QuestionDB()
            qk.update_question_status(
                record_id=rid,
                question_data={"question": "❌ 未提供内容", "explanation": "请输入题目内容或上传图片"},
                summary="❌ 未提供内容",
                status="failed",
                mistake_book=book_name
            )
            return

        # ========== STAGE 2: CLASSIFICATION ==========
        print("Starting Stage 2: Question Type Classification...")
        detected_type = f_type if f_type else None
        
        if not detected_type:
            classify_prompt = r"""
分析以下题目文本，判断题型并输出JSON。

**题型定义**：
- multiple_choice: 单选题（ABCD选项）
- multi_select: 多选题（多个正确答案）
- boolean: 判断题（对错）
- fill_in_blank: 填空题（有空格待填）
- short_answer: 解答题/计算题
- proof: 证明题/推导题
- mixed: 混合题型（包含多个小题，且涉及不同类型）

输出格式：{"type": "...", "confidence": "high/medium/low"}
"""
            try:
                classify_resp = text_client.chat.completions.create(
                    model=text_model,
                    messages=[
                        {"role": "system", "content": classify_prompt},
                        {"role": "user", "content": f"题目文本：\n{source_text}"}
                    ],
                    temperature=0,
                    max_tokens=100
                )
                classify_raw = classify_resp.choices[0].message.content
                classify_res = json.loads(clean_json_string(classify_raw), strict=False)
                detected_type = classify_res.get("type", "short_answer")
                print(f"Stage 2 Classification: {detected_type} (confidence: {classify_res.get('confidence', 'unknown')})")
            except Exception as e:
                print(f"Stage 2 Classification Error: {e}, defaulting to short_answer")
                detected_type = "short_answer"
        
        # ========== STAGE 3: SOLVING & GENERATION ==========
        print(f"Starting Stage 3: Solving question (Type: {detected_type})...")
        
        # --- Prompt Construction ---
        # 1. Base Instruction (Shared)
        base_prompt = r"""
你是一位资深的数学解题专家。你的任务是解答题目并输出标准JSON。

**绝对格式规则**：
1. **公式格式**：必须且只能使用 $...$ (行内) 或 $$...$$ (行间) 包裹。严禁使用 \[ \] 或 \( \)。
   - ❌ [错误]: √ a^2/b 或 \[\sqrt{\dfrac{a^2}{b}}\] 或 \(\sqrt{\dfrac{a^2}{b}}\)
   - ✅ [正确]: $\sqrt{\dfrac{a^2}{b}}$
2. **排版格式**：`explanation` 必须分行显示，使用 `\n` 换行。
   - ✅ [正确]: "解：\n1. 第一步...\n2. 第二步..."
3. **必填项**：`answers` 和 `explanation` 绝不能为空。

请输出 JSON:
{
    "summary": "知识点摘要",
    "question": "规范化后的题目文本",
    "explanation": "详细解析（分步骤）",
    "answers": ["结果1", "结果2"],  // 最终答案数组。选择题留空。
    "options": [],                // 仅选择题填写，否则为空数组 []
    "correct_answer": ""          // 仅选择题填写，否则为空字符串
}
"""

        # 2. Type-Specific Examples
        type_prompts = {
            "multiple_choice": r"""
**当前任务**：处理【单项选择题】。
请提取选项列表，并给出正确选项。

【示例】
Type: multiple_choice
Text: 1+1=? A.1 B.2
Output:
{
    "summary": "基础加法",
    "question": "1+1=?",
    "explanation": "1+1=2，所以选B。",
    "answers": [],
    "options": ["A. 1", "B. 2"],
    "correct_answer": "B"
}
""",
            "multi_select": r"""
**当前任务**：处理【多项选择题】。
请提取选项列表，并给出所有正确选项（例如 "AC"）。

【示例】
Type: multi_select
Text: 已知集合 $A=\{1, 2, 3\}$，则下列结论正确的是？
A. $1 \in A$
B. $4 \in A$
C. $\{1, 2\} \subseteq A$
D. $\emptyset \in A$
Output:
{
    "summary": "集合的性质",
    "question": "已知集合 $A=\{1, 2, 3\}$，则下列结论正确的是？",
    "explanation": "解：\n1. 元素1在集合A中，故A正确。\n2. 元素4不在集合A中，故B错误。\n3. $\{1, 2\}$是A的子集，故C正确。\n4. 空集是任意集合的子集，但不是A的元素，故D错误。\n综上选AC。",
    "answers": [],
    "options": ["A. $1 \\in A$", "B. $4 \\in A$", "C. $\{1, 2\} \\subseteq A$", "D. $\\emptyset \\in A$"],
    "correct_answer": "AC"
}
""",
            "boolean": r"""
**当前任务**：处理【判断题】。
请判断对错。正确填"True"，错误填"False"（作为 correct_answer）。

【示例】
Type: boolean
Text: 函数 $f(x) = x^2$ 是奇函数。
Output:
{
    "summary": "函数奇偶性",
    "question": "函数 $f(x) = x^2$ 是奇函数。",
    "explanation": "解：\n1. 定义域为 R。\n2. 计算 $f(-x) = (-x)^2 = x^2 = f(x)$。\n3. 满足偶函数定义，故不是奇函数。\n4. 题干说法错误。",
    "answers": [],
    "options": [],
    "correct_answer": "False"
}
""",
            "mixed": r"""
**当前任务**：处理【混合题型】。
此类题目通常包含填空、选择、计算等多个部分，或者结构复杂。
请生成完整的题目文本和详细解析。
`answers` 字段请填 `["见解析"]`。

【示例】
Type: mixed
Text: (1)填空：... (2)计算：...
Output:
{
    "summary": "综合练习",
    "question": "完整题目...",
    "explanation": "详解...",
    "answers": ["见解析"],
    "options": [],
    "correct_answer": ""
}
""",
            "fill_in_blank": r"""
**当前任务**：处理【填空题】。
请计算出结果填入 `answers` 数组。

**答案格式规则**：
1. **数学公式必须用LaTeX**：用 $...$ 包裹，如 `$x^2+1$`

2. **多个空格**：每个空格一个数组元素，用换行区分
   - 示例：`["第一空答案", "第二空答案"]`

3. **多解（任选一个）**：用 | 或 ｜ 分隔备选答案
   - 示例：`["答案A｜答案B｜答案C"]` （用户填任何一个都算对）

4. **一个答案包含多个部分**：直接作为整体写入
   - 示例：`["$x=1, y=2$"]` 或 `["$\\alpha=30°, \\beta=60°$"]`

【示例1：单空题】
Type: fill_in_blank
Text: 勾股定理公式是____。
Output:
{
    "summary": "勾股定理",
    "question": "勾股定理公式是____。",
    "explanation": "直角三角形两条直角边的平方和等于斜边的平方。",
    "answers": ["$a^2+b^2=c^2$"],
    "options": [],
    "correct_answer": ""
}

【示例2：多空题】
Type: fill_in_blank
Text: 求解方程组：(1) x+y=5的一组解是x=____，y=____。(2) 2x=10，则x=____。
Output:
{
    "summary": "方程组求解",
    "question": "求解方程组：(1) x+y=5的一组解是x=____，y=____。(2) 2x=10，则x=____。",
    "explanation": "解：\n1. (1)可以是x=1,y=4或x=2,y=3等\n2. (2)解得x=5",
    "answers": ["1｜2｜3", "4｜3｜2", "5"],
    "options": [],
    "correct_answer": ""
}

【示例3：一个空多个值都要写】
Type: fill_in_blank
Text: 方程$x^2-1=0$的解为____。
Output:
{
    "summary": "一元二次方程",
    "question": "方程$x^2-1=0$的解为____。",
    "explanation": "解：$x^2=1$，故$x=\\pm 1$，即$x_1=1, x_2=-1$",
    "answers": ["$x_1=1, x_2=-1$｜$x=\\pm 1$"],
    "options": [],
    "correct_answer": ""
}
""",
            "short_answer": r"""
**当前任务**：处理【解答题/计算题】。
请给出详细推导过程和**最终答案**。

**答案格式规则**：
1. **数学公式必须用LaTeX**：用 $...$ 包裹，如 `$x^2+1$`

2. **多个小题**：每一问一个数组元素 `["第一问", "第二问"]`

3. **多解（任选一个）**：用 | 或 ｜ 分隔 `["答案A｜答案B"]`

4. **一个答案包含多个部分**：作为整体 `["$x=1, y=2$"]`

**重要**：`answers`数组必须包含最终结果，不能为空！如果有多问，每一问都要填入。

【示例】
Type: short_answer
Text: 解方程 $x^2 - 1 = 0$
Output:
{
    "summary": "一元二次方程求解",
    "question": "解方程 $x^2 - 1 = 0$",
    "explanation": "解：\n1. 移项得 $x^2=1$。\n2. 开平方得 $x=\pm 1$。\n3. 即 $x_1=1, x_2=-1$。",
    "answers": ["$x=\\pm 1$｜$x_1=1, x_2=-1$"],
    "options": [],
    "correct_answer": ""
}
""",
            "proof": r"""
**当前任务**：处理【证明题】。
请仅生成解析，`answers` 填 `["见解析"]`。

【示例】
Type: proof
Text: 求证：对顶角相等。
Output:
{
    "summary": "几何基础",
    "question": "求证：对顶角相等。",
    "explanation": "证明：设直线AB、CD相交于O...\n所以 $\angle AOC = \angle BOD$。",
    "answers": ["见解析"],
    "options": [],
    "correct_answer": ""
}
"""
        }

        # 3. Assemble Prompt
        # Default to short_answer if type unknown
        specific_prompt = type_prompts.get(detected_type, type_prompts["short_answer"])
        sys_prompt_2 = base_prompt + "\n" + specific_prompt
        user_content = f"【题目文本】:\n{source_text}\n\n【题型】: {detected_type}\n"
        if q_correct:
            user_content += f"【用户提供的答案】: {q_correct}\n"
        
        msgs_2 = [{"role": "system", "content": sys_prompt_2}]
        payload_2 = [{"type": "text", "text": user_content}]
        if attachment_b64: # Context image
            payload_2.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{attachment_b64}"}})
        
        msgs_2.append({"role": "user", "content": payload_2}) # type: ignore
        # CRITICAL: Force complete generation
        msgs_2.append({"role": "user", "content": """
【重要】你必须输出完整的JSON，包含所有字段：
- summary (必填)
- question (必填)  
- explanation (必填，不能为空，必须有详细步骤)
- answers (必填，不能为空数组)
- options
- correct_answer

不要在生成question后就停止！必须继续生成explanation和answers！
"""})

        # Retry mechanism for Stage 3
        max_retries = 3
        res_2 = {}
        
        for attempt in range(max_retries):
            try:
                print(f"Stage 3 Generation (Attempt {attempt+1}/{max_retries})...")
                resp_2 = vl_client.chat.completions.create(
                    model=vl_model,
                    messages=msgs_2, # type: ignore
                    temperature=0.3 + (attempt * 0.1),
                    max_tokens=4096
                    # Removed response_format to avoid premature termination
                )
                raw_2 = resp_2.choices[0].message.content
                print(f"Stage 3 Raw Output (first 200 chars): {raw_2[:200]}...")
                print(f"Stage 3 Raw Output (last 200 chars): ...{raw_2[-200:]}")
                print(f"Stage 3 Output length: {len(raw_2)} characters") 
                
                try:
                    cleaned = clean_json_string(raw_2)
                    print(f"Cleaned JSON (first 300 chars): {cleaned[:300]}")
                    curr_res = json.loads(cleaned, strict=False)
                    print(f"Parse SUCCESS! Keys: {list(curr_res.keys())}")
                    print(f"explanation present: {bool(curr_res.get('explanation'))}")
                    print(f"answers present: {bool(curr_res.get('answers'))}")
                except Exception as parse_err:
                    print(f"JSON Parse Error: {parse_err}")
                    curr_res = {}
                
                # --- Validation Logic ---
                is_valid = True
                missing_fields = []
                
                # 1. Check Explanation (Required for all types)
                if not curr_res.get("explanation") or len(str(curr_res.get("explanation", ""))) < 5:
                    # 对于 proof 题，explanation 是核心；对于其他题也很重要
                    is_valid = False
                    missing_fields.append("explanation")
                    print(f"Explanation validation failed. Value: {curr_res.get('explanation', 'N/A')[:50]}")
                
                # 2. Check Answer based on type
                dt = detected_type
                if dt in ["multiple_choice", "multi_select", "boolean"]:
                    if not curr_res.get("correct_answer"):
                        is_valid = False
                        missing_fields.append("correct_answer")
                elif dt in ["fill_in_blank", "short_answer"]:
                    # Must have answers array
                    ans = curr_res.get("answers")
                    if not ans or not isinstance(ans, list) or len(ans) == 0:
                         is_valid = False
                         missing_fields.append("answers")
                         print(f"Answers validation failed. Value: {ans}")
                # proof / mixed types check skipped for answers
                
                if is_valid:
                    res_2 = curr_res
                    print("Stage 3 Validation Passed.")
                    break
                else:
                    print(f"Stage 3 Validation Failed. Missing: {missing_fields}")
                    res_2 = curr_res # Keep it anyway in case we run out of retries
                    
                    if attempt < max_retries - 1:
                        # Add feedback for next retry
                        feedback_msg = f"上一次生成缺失了以下必须字段: {', '.join(missing_fields)}。请务必补充完整。"
                        # Append textual feedback to history
                        msgs_2.append({"role": "assistant", "content": raw_2}) 
                        msgs_2.append({"role": "user", "content": f"请重新生成。注意：{feedback_msg}"})
            
            except Exception as e:
                print(f"Stage 3 Error (Attempt {attempt+1}): {e}")
                res_2 = {} # Clear on crash

        # --- Post-Processing ---
        final_question = q_c if q_c else res_2.get("question", source_text)
        final_explanation = q_e if q_e else res_2.get("explanation", "")
        
        ai_options = res_2.get("options", [])
        
        # Options Logic
        if q_o:
            final_options = q_o
        else:
            if detected_type in ["multiple_choice", "multi_select", "boolean"] and ai_options:
                final_options = "\n".join(ai_options)
            elif detected_type == "fill_in_blank" and ai_options: 
                 final_options = "\n".join(ai_options)
                 detected_type = "multiple_choice"
            elif detected_type == "boolean":
                 # Ensure standard True/False options if missing
                 final_options = "True\nFalse"
            else:
                final_options = ""

        # Helper for mapping various formats to Uppercase Letters
        def _map_to_letter(s):
            s = s.strip()
            mapping = {
                '1': 'A', '１': 'A', 'I': 'A', '甲': 'A', '对': 'T', 'T': 'T', 'True': 'T', 'TRUE': 'T', '√': 'T',
                '2': 'B', '２': 'B', 'II': 'B', '乙': 'B', '错': 'F', 'F': 'F', 'False': 'F', 'FALSE': 'F', '×': 'F',
                '3': 'C', '３': 'C', 'III': 'C', '丙': 'C',
                '4': 'D', '４': 'D', 'IV': 'D', '丁': 'D',
                '5': 'E', '５': 'E', 'V': 'E', '戊': 'E'
            }
            # Special Boolean handling if detected type is boolean
            if detected_type == "boolean":
                if s in ['A', 'T', 't', '1', '对', '√', 'True', 'TRUE']: return "True"
                if s in ['B', 'F', 'f', '0', '错', '×', 'False', 'FALSE']: return "False"
            
            return mapping.get(s, s.upper())

        # Answer Logic
        # Answer Logic
        final_correct = ""
        ans_list = []
        
        # Determine final_correct string based on user input or AI output
        if q_correct:
            raw_correct = q_correct
        else:
            raw_correct = res_2.get("correct_answer", "")
            
        # Special handling for fill_in_blank encoding
        if detected_type == "fill_in_blank":
             if q_correct:
                 # If user provided answer manually, split by any newline type (hard or soft)
                 # splitlines() handles \n, \r, \r\n, \u2028 (Line Separator), etc.
                 cleaned = q_correct.strip()
                 # Check if there are multiple lines
                 lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
                 
                 if len(lines) > 1:
                     ans_list = lines
                 else:
                     ans_list = [cleaned]
             else:
                 # Use AI generated answers array
                 ans_list = res_2.get("answers", [])
                 # Fallback to correct_answer string if answers array is empty
                 if not ans_list and raw_correct:
                     ans_list = [raw_correct]
             
             # Encode into final_options/correct_answer using the protocol
             if ans_list:
                 final_options = "FILL_IN_BLANK:" + json.dumps(ans_list, ensure_ascii=False)
                 final_correct = "FILL_IN_BLANK"
             else:
                 final_options = ""
                 final_correct = ""
        
        else:
            # For other types (MC, boolean, short_answer, etc.)
            final_correct = raw_correct
            if detected_type in ["multiple_choice", "boolean"]:
                  final_correct = _map_to_letter(final_correct)
        
        # Multi-select normalization fallback
        # Note: Use final_correct (not q_correct) to normalize AI-generated answers too
        if detected_type == "multi_select" and final_correct:
             cleaned = final_correct.replace('，', ',').replace('|', ',').replace(' ', ',')
             # Check if it looks like "13" (digits string) or just comma separated
             if ',' not in cleaned and len(cleaned) > 1:
                # Treat "13" as "1", "3"
                final_parts = [_map_to_letter(c) for c in cleaned]
             else:
                parts = [p.strip() for p in cleaned.split(',') if p.strip()]
                final_parts = [_map_to_letter(p) for p in parts]
             
             final_correct = ", ".join(sorted(list(set(final_parts)))) # Sort and Dedup

        # Save
        q_data = {
            "question_type": detected_type,
            "question": final_question,
            "options": final_options.split('\n') if final_options and "FILL_IN_BLANK" not in final_options else [],
            "answers": json.loads(final_options[14:]) if final_options and "FILL_IN_BLANK" in final_options else (res_2.get("answers", []) if detected_type in ["short_answer", "fill_in_blank"] else None),
            "correct_answer": final_correct if "FILL_IN_BLANK" not in str(final_correct) else None,
            "explanation": final_explanation
        }
        if attachment_b64: q_data["image"] = attachment_b64
        
        final_summary = res_2.get("summary", final_question[:20])
        question_db.update_question_status(record_id=rid, question_data=q_data, summary=final_summary, status="completed", mistake_book=book_name)
        
    except Exception as e:
        print(f"Process Error: {e}")
        error_msg = str(e)
        if "os" in error_msg: error_msg = "System Error (Import)"
        question_db.update_question_status(record_id=rid, status="failed", mistake_book=book_name)

@st.dialog("重命名错题本", width="small")
def rename_book_dialog(old_name):
    st.markdown(f"✍️ 正在重命名: **{old_name}**")
    new_name = st.text_input("新名称", value=old_name, placeholder="输入新名称...", key=f"rename_val_{old_name}")
    if st.button("💾 保存修改", type="primary", use_container_width=True, key=f"rename_confirm_{old_name}"):
        if new_name and new_name != old_name:
            if question_db.rename_mistake_book(old_name, new_name):
                st.toast(f"✅ 已重命名为 {new_name}")
                time.sleep(0.5)
                st.rerun()
            else: st.error("❌ 重命名失败 (可能名称已存在)")
        else: st.warning("⚠️ 名称未变更")

@st.dialog("�️ 确认删除", width="small")
def delete_book_dialog(book_name):
    st.warning(f"⚠️ 确定要彻底删除错题本 **{book_name}** 吗？\n\n此操作将删除该本中的**所有题目**，且**不可恢复**！")
    col_del_1, col_del_2 = st.columns(2)
    with col_del_1:
         if st.button("🔥 确认删除", type="primary", use_container_width=True, key=f"dialog_confirm_del_{book_name}"):
            if question_db.delete_mistake_book(book_name):
                st.toast("✅ 已删除")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ 删除失败")
    with col_del_2:
        if st.button("取消", use_container_width=True, key=f"dialog_cancel_del_{book_name}"):
            st.rerun()

@st.dialog("➕ 新建错题本", width="small")
def create_book_dialog():
    new_book_name = st.text_input("错题本名称", placeholder="例如：数学错题本")
    if st.button("立即创建", type="primary", use_container_width=True, key="dialog_create_book_btn"):
        if new_book_name:
            if question_db.create_mistake_book(new_book_name):
                st.toast(f"✅ 创建成功")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ 错题本已存在")
        else:
            st.warning("请输入错题本名称")

@st.dialog("�📓 错题详情与编辑", width="large")
def mistake_detail_dialog(item, book_name, is_archived):
    # 使用 session_state 控制内部模式，避免嵌套 Dialog
    mode_key = f"dialog_mode_{item['id']}"
    # Only initialize if not already set (allows external setting from quiz page)
    current_mode = st.session_state.get(mode_key, "view")
    
    if current_mode == "view":
        # --- VIEW MODE ---
        # Move Buttons to Top
        c_edit, c_arch, c_del = st.columns([1, 1, 1])
        with c_edit:
            def _enter_edit(): st.session_state[mode_key] = "edit"
            st.button("✏️ 编辑", use_container_width=True, key=f"btn_go_edit_{item['id']}", on_click=_enter_edit)
        with c_arch:
            btn_arch_label = "📤 取消归档" if is_archived else "📥 归档"
            if st.button(btn_arch_label, use_container_width=True, key=f"btn_dia_arch_{item['id']}"):
                question_db.toggle_archive(item['id'], mistake_book=book_name)
                # Auto deselect
                if item['id'] in st.session_state.get('selected_questions', set()):
                    st.session_state.selected_questions.discard(item['id'])
                st.toast("操作成功")
                time.sleep(0.5)
                st.rerun()
        with c_del:
            if st.button("🗑️ 删除", use_container_width=True, type="primary", key=f"btn_dia_del_{item['id']}"):
                question_db.remove_wrong_question(item['id'], mistake_book=book_name)
                st.toast("已删除")
                time.sleep(0.5)
                st.rerun()
        
        st.divider()

        q = item["question"]
        st.markdown(f"### 题目")
        if q.get("image"):
            try:
                # Decide if base64 or url (assuming base64 for now as per adder)
                img_data = q.get("image")
                if img_data.startswith("http"):
                    st.image(img_data)
                else:
                    st.image(base64.b64decode(img_data))
            except:
                st.warning("图片加载失败")
                
        display_q = q.get('question', '')
        if not display_q and q.get('image'):
            display_q = "_（此题为纯图片模式，无文字描述）_"
        st.markdown(display_q)
        
        q_type = q.get("question_type", "")
        options = q.get("options", [])
        
        if q_type in ["multiple_choice", "multi_select", "boolean"] or options:
            st.markdown("**选项：**")
            for opt in options:
                st.markdown(f"- {opt}")
            st.success(f"**正确答案：** {q.get('correct_answer')}")
        else:
            st.markdown("**正确答案：**")
            answers = q.get("answers") or []
            if answers:
                for ans in answers:
                    st.markdown(f"- {ans}")
            else:
                st.caption("（无标准答案记录）")
                
        st.markdown(f"### 💡 解析\n\n{q.get('explanation', '暂无解析')}", unsafe_allow_html=True)
        st.divider()
        
        st.divider()
                
    else:
        # --- EDIT MODE ---
        q = item["question"]
        current_type = q.get("question_type", "multiple_choice")
        # Type Selector (Only in Edit Mode)
        st.markdown("#### 修改题型")
        type_opts = {
            "单选题": "multiple_choice",
            "多选题": "multi_select",
            "判断题": "boolean",
            "填空题": "fill_in_blank",
            "解答题": "short_answer",
            "证明题": "proof",
            "混合题": "mixed"
        }
        curr_type_idx = list(type_opts.values()).index(current_type) if current_type in type_opts.values() else 0
        new_type_display = st.radio("题目类型", list(type_opts.keys()), index=curr_type_idx, horizontal=True, label_visibility="collapsed")
        new_type = type_opts[new_type_display]

        new_q = st.text_area("题目内容", value=q.get("question", ""), height=150, key=f"edit_q_{item['id']}")
        
        # Image Edit
        curr_img = q.get("image")
        if curr_img:
            st.markdown("**当前图片：**")
            try: st.image(base64.b64decode(curr_img), width=200)
            except: st.text("图片加载失败")
            if st.button("🗑️ 删除图片", key=f"del_img_{item['id']}"):
                q["image"] = None
                st.rerun()
        
        # 粘贴或上传新图片
        st.markdown("**更换/上传图片：**")
        try:
            from streamlit_paste_button import paste_image_button
            paste_edit_img = paste_image_button(
                label="📋 粘贴图片",
                text_color="theme.textColor",
                background_color="theme.secondaryBackgroundColor",
                hover_background_color="#FF4B4B",
                key=f"paste_img_edit_{item['id']}"
            )
        except ImportError:
            paste_edit_img = None
            
        new_img_file = st.file_uploader("或浏览上传", type=["png", "jpg", "jpeg"], key=f"up_img_edit_{item['id']}", label_visibility="collapsed")
        
        # 显示粘贴/上传的预览
        new_img_b64 = curr_img
        if paste_edit_img and paste_edit_img.image_data:
            st.image(paste_edit_img.image_data, caption="已粘贴新图片", width=200)
            import io
            buffer = io.BytesIO()
            paste_edit_img.image_data.save(buffer, format="PNG")
            new_img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        elif new_img_file:
            st.image(new_img_file, caption="已上传新图片", width=200)
            new_img_b64 = base64.b64encode(new_img_file.getvalue()).decode('utf-8')
        
        if new_type in ["multiple_choice", "multi_select", "boolean"]:
            # If switching, handle missing options
            options_val = q.get("options", [])
            options_str = "\n".join(options_val) if isinstance(options_val, list) else ""
            
            new_o = st.text_area("选项 (每行一个)", value=options_str, height=120, key=f"edit_o_{item['id']}")
            new_a = st.text_input("正确答案", value=q.get("correct_answer", ""), key=f"edit_a_{item['id']}", help="多选题答案可用逗号或空格分隔")
            new_data = {
                "question_type": new_type,
                "question": new_q,
                "options": [o.strip() for o in new_o.split("\n") if o.strip()],
                "correct_answer": new_a.strip(),
                "explanation": st.text_area("解析", value=q.get("explanation", ""), height=150, key=f"edit_e_{item['id']}")
            }
        elif new_type in ["fill_in_blank", "short_answer"]:
            answers_val = q.get("answers") or []
            if not answers_val and q.get("correct_answer"): answers_val = [q.get("correct_answer")]
            answers_str = "\n".join(answers_val) if isinstance(answers_val, list) else ""
            
            new_ans = st.text_area("正确答案 (每行一个，同一空多个可能答案用 | 分隔)", value=answers_str, height=120, key=f"edit_ans_{item['id']}")
            new_data = {
                "question_type": new_type,
                "question": new_q,
                "answers": [a.strip() for a in new_ans.split("\n") if a.strip()],
                "explanation": st.text_area("解析", value=q.get("explanation", ""), height=150, key=f"edit_e_blank_{item['id']}")
            }
        else: # Proof
            new_data = {
                "question_type": "proof",
                "question": new_q,
                "explanation": st.text_area("解析与证明过程", value=q.get("explanation", ""), height=200, key=f"edit_proof_e_{item['id']}")
            }
        
        if new_img_b64:
            new_data["image"] = new_img_b64
        
        # Familiarity Score Editing
        st.divider()
        current_score = item.get("familiarity_score", 2)
        new_score = st.slider("📊 陌生度", min_value=0, max_value=5, value=current_score, key=f"edit_score_{item['id']}")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 保存修改", type="primary", use_container_width=True, key=f"btn_save_edit_{item['id']}"):
                question_db.update_question_status(record_id=item["id"], question_data=new_data, summary=new_q[:20], status="completed", mistake_book=book_name)
                # Update familiarity score if changed
                if new_score != current_score:
                    question_db.set_familiarity_score(item['id'], new_score, book_name)
                
                st.toast("✅ 修改已保存")
                
                # Check for Return to Quiz
                if st.session_state.get("return_to_quiz"):
                     st.session_state.mistake_mode = "quiz"
                     st.session_state.active_dialog_id = None
                     st.session_state.active_dialog_type = None
                     del st.session_state["return_to_quiz"]
                     time.sleep(0.5); st.rerun()
                else:
                    st.session_state[mode_key] = "view"
                    time.sleep(0.5); st.rerun()
                    
        with c2:
            if st.button("❌ 取消", use_container_width=True, key=f"btn_cancel_edit_{item['id']}"):
                if st.session_state.get("return_to_quiz"):
                     st.session_state.mistake_mode = "quiz"
                     st.session_state.active_dialog_id = None
                     del st.session_state["return_to_quiz"]
                     st.rerun()
                else:
                     st.session_state[mode_key] = "view"
                     st.rerun()
                
    st.divider()
    if st.button("❌ 关闭", use_container_width=True, key=f"btn_close_dlg_{item['id']}"):
        st.session_state.active_dialog_id = None
        st.rerun()

@st.dialog("📚 批量已选详情", width="large")
def batch_view_dialog(items):
    st.markdown(f"### 已选择 {len(items)} 道题目")
    st.divider()
    
    for i, item in enumerate(items):
        q = item["question"]
        st.markdown(f"#### 题目 {i+1}")
        
        # Batch View Image Support
        if q.get("image"):
             try:
                b_img = q.get("image")
                if b_img.startswith("http"): st.image(b_img, width=300)
                else: st.image(base64.b64decode(b_img), width=300)
             except: st.error("图片加载错")

        st.info(q.get("question", "（无内容）"))
        
        options = q.get("options", [])
        if func_q_type := q.get("question_type", "") == "multiple_choice" or options:
            st.markdown("**选项：**")
            for opt in options:
                st.markdown(f"- {opt}")

        with st.expander("查看答案与解析", expanded=True):
            q_type = q.get("question_type", "")
            if q_type == "multiple_choice":
                st.markdown(f"**正确选项：** {q.get('correct_answer')}")
            else:
                st.markdown("**正确答案：**")
                answers = q.get("answers") or []
                for ans in answers: st.markdown(f"- {ans}", unsafe_allow_html=True)
            st.markdown(f"**解析：**\n\n{q.get('explanation', '暂无解析')}", unsafe_allow_html=True)
        st.divider()
        
    if st.button("❌ 关闭所有", use_container_width=True, key="btn_close_batch_view"):
        st.session_state.active_dialog_id = None
        st.session_state.active_dialog_type = None
        st.rerun()

@st.dialog("➕ 添加错题", width="large")
def add_mistake_dialog(selected_book):
    # Custom CSS to center file uploaders and adjust layout
    st.markdown("""
    <style>
    /* File Uploader 200px Height & Centering */
    div[data-testid="stFileUploader"] label { width: 100%; text-align: center; }
    div[data-testid="stFileUploader"] button { margin: 0 auto; display: block; }
    section[data-testid="stFileUploaderDropzone"] { 
        min-height: 160px !important; 
        height: 160px !important;
        display: flex;
        justify-content: center;
        align-items: center;
        flex-direction: column;
    }
    /* Checkbox optical adjustment */
    div[data-testid="stCheckbox"] { transform: translateY(-2px); }
    </style>
    """, unsafe_allow_html=True)

    st.info("💡 上传图片或输入文本，系统将自动填充空白部分（答案、解析等）。可以点击粘贴按钮后按 Cmd/Ctrl+V 粘贴截图。")
    # Only show unarchived books for adding new mistakes
    books = question_db.list_mistake_books(include_archived=False)
    target = st.selectbox("📚 目标错题本", books, index=books.index(selected_book) if selected_book in books else 0)
    
    # 尝试导入粘贴组件
    try:
        from streamlit_paste_button import paste_image_button
        paste_available = True
    except ImportError:
        paste_available = False
    
    # Row 1: Images (Paste + Upload), Question, Options
    c1, c2, c3, c4 = st.columns([1, 1, 2, 2])
    
    # 初始化粘贴结果变量
    paste_ocr = None
    paste_fig = None
    
    with c1:
        st.markdown("**📸 识别源**")
        if paste_available:
            paste_ocr = paste_image_button(
                label="📋 粘贴识别源",
                text_color="theme.textColor",
                background_color="theme.secondaryBackgroundColor",
                hover_background_color="#FF4B4B",
                key="paste_ocr_new"
            )
            if paste_ocr and paste_ocr.image_data:
                st.image(paste_ocr.image_data, caption="已粘贴", use_container_width=True)
        u_ocr = st.file_uploader("或浏览上传", type=["jpg", "png", "jpeg"], key="u_ocr_new", label_visibility="collapsed")
        if u_ocr:
            st.image(u_ocr, caption="已上传", use_container_width=True)
            
    with c2:
        st.markdown("**🖼️ 配图**")
        if paste_available:
            paste_fig = paste_image_button(
                label="📋 粘贴配图",
                text_color="theme.textColor",
                background_color="theme.secondaryBackgroundColor",
                hover_background_color="#FF4B4B",
                key="paste_fig_new"
            )
            if paste_fig and paste_fig.image_data:
                st.image(paste_fig.image_data, caption="已粘贴", use_container_width=True)
        u_fig = st.file_uploader("或浏览上传", type=["jpg", "png", "jpeg"], key="u_fig_new", label_visibility="collapsed")
        if u_fig:
            st.image(u_fig, caption="已上传", use_container_width=True)
            
    with c3:
        q_c = st.text_area("题目内容", placeholder="输入题目...", height=200)
    with c4:
        q_o = st.text_area("选项 (可选)", placeholder="A. B. C. D.", height=200)
    
    # Row 2: Answer, Explanation
    c5, c6 = st.columns([1, 5])
    with c5:
        q_a = st.text_area("正确答案", placeholder="例如：A\n填空/解答题：\n1. 多个空/小问请换行\n2. 多解（任选一）用 | 分隔", height=200)
    with c6:
        q_e = st.text_area("解析 (可选)", placeholder="由 AI 自动生成...", height=200)
    
    # 辅助函数：将 PIL Image 转为 base64
    def pil_to_base64(pil_img):
        import io
        buffer = io.BytesIO()
        pil_img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # 判断是否有图片输入（包括粘贴和上传）
    has_ocr = (paste_ocr and paste_ocr.image_data) or u_ocr
    has_fig = (paste_fig and paste_fig.image_data) or u_fig
    
    if st.button("智能识别并添加", type="primary", use_container_width=True):
        if has_ocr or has_fig or q_c:
            i_q = q_c if q_c else "（正在识别中...）"
            
            # Normalize answer separators: Support both half-width and full-width
            normalized_answer = q_a.replace('｜', '|').replace('，', ',') if q_a else ""
            
            i_d = {"question": i_q, "explanation": q_e if q_e else "（处理中...）"}
            
            # 获取 OCR 图片 base64（优先粘贴）
            if paste_ocr and paste_ocr.image_data:
                ocr_b64 = pil_to_base64(paste_ocr.image_data)
            elif u_ocr:
                ocr_b64 = base64.b64encode(u_ocr.getvalue()).decode('utf-8')
            else:
                ocr_b64 = None
            
            # 获取配图 base64（优先粘贴）
            if paste_fig and paste_fig.image_data:
                fig_b64 = pil_to_base64(paste_fig.image_data)
            elif u_fig:
                fig_b64 = base64.b64encode(u_fig.getvalue()).decode('utf-8')
            else:
                fig_b64 = None
            
            # Request 1: Only use figure if explicitly provided (No fallback to OCR)
            final_attachment = fig_b64 
            
            # Initial placeholder
            rid = question_db.add_result(
                kb_name=st.session_state.get("selected_kb", "default"), # Placeholder
                question_data=i_d,
                user_answer="（手动添加）",
                is_correct=False,
                summary=i_q[:20],
                mistake_book=target
            )
            
            # Auto detection mode (None)
            f_type = None 
            
            # Pass normalized answer to backend
            threading.Thread(target=process_question_async, args=(rid, target, q_c, q_o, normalized_answer, q_e, ocr_b64, final_attachment, f_type), daemon=True).start()
            st.session_state.active_dialog_type = None  # Clear dialog state
            st.success("✅ 已添加，正在处理..."); time.sleep(1.0); st.rerun()
        else: st.error("请提供内容或图片")

# ========== 错题本列表页面 ==========
if st.session_state.view_mode == "list":
    
    # 获取所有错题本 (with archive status)
    all_books = question_db.list_mistake_books(include_archived=True)
    
    # 新建错题本按钮 + 显示已归档切换
    col_manage1, col_manage2, col_manage3 = st.columns([1, 1, 3])
    with col_manage1:
        # Use button + dialog for consistency with other actions
        if st.button("➕ 新建错题本", use_container_width=True):
            create_book_dialog()
    
    with col_manage2:
        # Use a button to toggle archive view instead of st.toggle
        if "show_archived_books" not in st.session_state:
            st.session_state.show_archived_books = False
            
        btn_label = "� 查看未归档" if st.session_state.show_archived_books else "📦 查看已归档"
        # Use secondary type for toggle
        if st.button(btn_label, use_container_width=True):
            st.session_state.show_archived_books = not st.session_state.show_archived_books
            st.rerun()
            
    show_archived = st.session_state.show_archived_books
    
    st.markdown("---")
    
    # 根据切换过滤错题本
    if show_archived:
        # Show only archived books
        display_books = [(name, True) for name, is_archived in all_books if is_archived]
        if not display_books:
            st.info("📦 没有已归档的错题本")
    else:
        # Show only unarchived books
        display_books = [(name, False) for name, is_archived in all_books if not is_archived]
    
    # 显示错题本卡片
    if not display_books:
        if not show_archived:
            st.info("还没有错题本，点击上方按钮创建一个吧！")
    else:
        # Grid Layout: 3 cards per row
        for i in range(0, len(display_books), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(display_books):
                    book_name, is_archived = display_books[i + j]
                    with cols[j]:
                        # 卡片容器
                        with st.container(border=True):
                            # Row 1: Title with archive indicator
                            icon = "📦" if is_archived else "📓"
                            st.markdown(f"<div style='text-align: center; font-size: 1.25rem; margin-bottom: 5px;'><b>{icon} {book_name}</b></div>", unsafe_allow_html=True)
        
                            # Row 2: Statistics
                            questions = question_db.get_wrong_questions(mistake_book=book_name)
                            active_count = len([q for q in questions if not q.get("archived", False)])
                            archived_count = len([q for q in questions if q.get("archived", False)])
                            st.markdown(f"<div style='text-align: center; color: #666; font-size: 0.85rem; margin-bottom: 12px;'>📝 未归档: <b>{active_count}</b> &nbsp;|&nbsp; 📦 已归档: <b>{archived_count}</b></div>", unsafe_allow_html=True)
                            
                            st.divider()
                            
                            if not is_archived:
                                # --- UNARCHIVED BOOK BUTTONS ---
                                # Row 3: Enter, Practice
                                c_enter, c_quiz = st.columns(2)
                                with c_enter:
                                    if st.button("进入错题本", key=f"enter_{book_name}", use_container_width=True):
                                        st.session_state.selected_mistake_book = book_name
                                        st.session_state.view_mode = "detail"
                                        st.session_state.mistake_mode = "list"
                                        st.session_state.active_dialog_id = None # Reset dialog
                                        st.session_state.active_dialog_type = None
                                        st.rerun()
                                with c_quiz:
                                    if st.button("错题练习", key=f"review_{book_name}", use_container_width=True):
                                        st.session_state.selected_mistake_book = book_name
                                        st.session_state.view_mode = "detail"
                                        st.session_state.mistake_mode = "quiz"
                                        st.session_state.mistake_index = 0
                                        _all = question_db.get_wrong_questions(mistake_book=book_name)
                                        _active = [q for q in _all if not q.get("archived", False)]
                                        _active = _active[::-1] 
                                        st.session_state.quiz_ids = [q['id'] for q in _active]
                                        for k in list(st.session_state.keys()):
                                            if k.startswith(("mistake_answered_", "mistake_blanks_", "mq_radio_", "score_res_")):
                                                del st.session_state[k]
                                        st.rerun()
            
                                # Row 4: Rename, Archive
                                c_ren, c_arch = st.columns(2)
                                with c_ren:
                                    if st.button("📝 重命名", key=f"pre_ren_{book_name}", use_container_width=True):
                                        rename_book_dialog(book_name)
                                with c_arch:
                                    if st.button("📥 归档", key=f"arch_{book_name}", use_container_width=True):
                                        question_db.toggle_book_archive(book_name)
                                        st.toast(f"已归档: {book_name}")
                                        time.sleep(0.5)
                                        st.rerun()
                            else:
                                # --- ARCHIVED BOOK BUTTONS ---
                                # Row 3: Enter, Delete
                                c_enter, c_del = st.columns(2)
                                with c_enter:
                                    if st.button("进入错题本", key=f"enter_{book_name}", use_container_width=True):
                                        st.session_state.selected_mistake_book = book_name
                                        st.session_state.view_mode = "detail"
                                        st.session_state.mistake_mode = "list"
                                        st.session_state.active_dialog_id = None # Reset
                                        st.session_state.active_dialog_type = None
                                        st.rerun()
                                with c_del:
                                    if st.button("🗑️ 删除", key=f"pre_del_{book_name}", use_container_width=True):
                                        delete_book_dialog(book_name)
            
                                # Row 4: Rename, Unarchive
                                c_ren, c_unarch = st.columns(2)
                                with c_ren:
                                    if st.button("📝 重命名", key=f"pre_ren_{book_name}", use_container_width=True):
                                        rename_book_dialog(book_name)
                                with c_unarch:
                                    if st.button("📤 移出归档", key=f"unarch_{book_name}", use_container_width=True):
                                        question_db.toggle_book_archive(book_name)
                                        st.toast(f"已取消归档: {book_name}")
                                        time.sleep(0.5)
                                        st.rerun()

# ========== 错题详情页面 ==========
elif st.session_state.view_mode == "detail":
    # 非复习模式下显示 Header
    if st.session_state.mistake_mode != "quiz":
        # Row 1: Back Button
        if st.button("⬅️ 返回", type="secondary"):
            st.session_state.view_mode = "list"
            st.rerun()
        
        # Row 2: Title and Stats
        selected_book = st.session_state.selected_mistake_book
        # 获取错题数据用于统计
        wrong_questions = question_db.get_wrong_questions(mistake_book=selected_book)
        st.markdown(f"#### 📚 当前错题本：{selected_book} | 共 {len(wrong_questions)} 道错题")
    else:
        selected_book = st.session_state.selected_mistake_book
        wrong_questions = question_db.get_wrong_questions(mistake_book=selected_book)
    
    # 检查是否有处理中的题目
    has_processing = False
    if wrong_questions:
        has_processing = any(item.get("status", "completed") == "processing" for item in wrong_questions)

    if wrong_questions:
        has_processing = any(item.get("status", "completed") == "processing" for item in wrong_questions)

# Callbacks for Batch Actions (Defined here to access closure variables effectively if needed, 
# or use st.session_state)
def cb_ba_select_all():
    # Need access to 'cur_list' - we can store IDs in session state or just grab all from DB?
    # Better: The button will execute this. We can pull from session state if we stored the view list?
    # Actually, simplistic approach: Do logic here. BUT 'cur_list' is local.
    # Hack: passing args to callback
    pass 

def cb_ba_cancel():
    for qid in st.session_state.get('selected_questions', []):
        if f"it_chk_{qid}" in st.session_state:
             st.session_state[f"it_chk_{qid}"] = False
    st.session_state.selected_questions = set()
    st.session_state.active_dialog_id = None
    st.session_state.active_dialog_type = None

def cb_ba_archive(sel_qs_arg, book_arg):
    for qid in sel_qs_arg: 
        question_db.toggle_archive(qid, mistake_book=book_arg)
    st.session_state.selected_questions = set()
    st.session_state.active_dialog_id = None
    st.session_state.active_dialog_type = None
    # Cannot toast here easily without rerun context? callbacks run before render. Toast works.
    
def cb_ba_expand():
    st.session_state.active_dialog_id = "batch_view"
    st.session_state.active_dialog_type = "batch"

# --- Mode: List View ---
# --- Mode: List View ---
if st.session_state.view_mode == "detail" and st.session_state.mistake_mode == "list":
    # CSS for List Item Checkbox Alignment
    st.markdown("""<style>div[data-testid="stCheckbox"] { transform: translateY(-2px); }</style>""", unsafe_allow_html=True)

    # Check for active dialog triggers
    active_type = st.session_state.get('active_dialog_type')
    active_id = st.session_state.get('active_dialog_id')
    
    # Simple dispatcher based on Type
    if active_type == "add":
        add_mistake_dialog(selected_book)
        
    elif active_type == "batch" and active_id == "batch_view":
        # Batch View Mode
        sel_qs = st.session_state.get('selected_questions', set())
        cur_all_qs = question_db.get_wrong_questions(mistake_book=selected_book)
        _selected_items = [q for q in cur_all_qs if q['id'] in sel_qs]
        if _selected_items:
            batch_view_dialog(_selected_items)
        else:
            st.session_state.active_dialog_id = None
            st.session_state.active_dialog_type = None
            st.rerun()
            
    elif active_id: # Default to single if ID exists and type is None or 'single'
         # Single Detail Mode
        target_item = next((q for q in wrong_questions if q['id'] == active_id), None)
        if target_item:
            v_arch = st.session_state.get("view_archived", False)
            mistake_detail_dialog(target_item, selected_book, v_arch)
        else:
            # Item might have been deleted
            st.session_state.active_dialog_id = None
            st.rerun()
            
    # 如果有处理中的题目，显示提示和刷新按钮
    if has_processing:
        col_info, col_refresh = st.columns([3, 1])
        with col_info:
            st.info("⏳ 检测到有题目正在后台处理中，请稍候...")
        with col_refresh:
            if st.button("🔄 刷新状态", key="refresh_processing_top"):
                st.rerun()
    
    # 获取归档错题数量
    archived_questions = question_db.get_archived_questions(mistake_book=selected_book)
    archived_count = len(archived_questions)
    
    # 如果错题本为空，显示提示信息
    if not wrong_questions:
        st.info(f"🎉 太棒了！错题本「{selected_book}」是空的。可以手动添加错题或去【做题练习】！")
        if archived_count > 0:
            st.info(f"📦 该错题本有 {archived_count} 道已归档的题目")
        
        c_empty_1, c_empty_2 = st.columns(2)
        with c_empty_1:
            if st.button("➕ 添加错题", type="primary", use_container_width=True, key="add_mistake_empty"):
                st.session_state.active_dialog_id = None 
                st.session_state.active_dialog_type = "add"
                st.rerun()
        with c_empty_2:
            if st.button("➡️ 前往做题练习", use_container_width=True, key="go_quiz_empty_main"):
                st.switch_page("pages/2_📝_做题练习.py")
        st.markdown("---")

    else:
        st.markdown(f"### 共 {len(wrong_questions)} 道错题")
        # Row 3: Control Buttons (Same style/size)
        c_r3_1, c_r3_2, c_r3_3, c_r3_4 = st.columns(4)
        with c_r3_1:
            if st.button("错题练习", use_container_width=True, key="tb_quiz"):
                st.session_state.mistake_mode = "quiz"; st.session_state.mistake_index = 0
                st.session_state.active_dialog_id = None  # Clear dialog state
                
                # Initialize Quiz Queue
                _all = question_db.get_wrong_questions(mistake_book=selected_book)
                _active = [q for q in _all if not q.get("archived", False)]
                
                # Apply current sort order
                s_opt = st.session_state.get("quiz_sort_order", "📅 添加时间(最新)")
                # Database returns DESC (newest first), so "最早" needs reverse
                if s_opt == "📅 添加时间(最早)": _active = _active[::-1]
                elif s_opt == "🔥 陌生度(高→低)": _active.sort(key=lambda x: x.get("familiarity_score", 0), reverse=True)
                elif s_opt == "✨ 陌生度(低→高)": _active.sort(key=lambda x: x.get("familiarity_score", 0))
                
                st.session_state.quiz_ids = [q['id'] for q in _active]
                
                # Reset quiz states
                for k in list(st.session_state.keys()):
                    if k.startswith(("mistake_answered_", "mistake_blanks_", "mq_radio_", "mq_blank_", "mq_multi_selected_", "score_res_")):
                        del st.session_state[k]
                st.rerun()
        with c_r3_2:
            sort_modes = ["📅 时间(最新)", "📅 时间(最早)", "🔥 陌生(高→低)", "✨ 陌生(低→高)"]
            if "sort_idx" not in st.session_state: st.session_state.sort_idx = 0
            if st.button(f"🔄 顺序: {sort_modes[st.session_state.sort_idx]}", use_container_width=True, key="tb_sort"):
                st.session_state.active_dialog_id = None  # Clear dialog state
                st.session_state.sort_idx = (st.session_state.sort_idx + 1) % len(sort_modes)
                st.session_state.quiz_sort_order = ["📅 添加时间(最新)", "📅 添加时间(最早)", "🔥 陌生度(高→低)", "✨ 陌生度(低→高)"][st.session_state.sort_idx]
                st.rerun()
        with c_r3_3:
            v_arch = st.session_state.get("view_archived", False)
            if st.button("📦 查看归档" if not v_arch else "🔙 查看未归档", use_container_width=True, key="tb_arch"):
                st.session_state.view_archived = not v_arch; st.session_state.selected_questions = set(); 
                st.session_state.active_dialog_id = None # Clear dialog
                st.rerun()
        with c_r3_4:
            if st.session_state.get("view_archived", False):
                # Archive View: Show Delete Selected
                 if st.button("🗑️ 删除选中", use_container_width=True, key="tb_del_multi"):
                    sel = st.session_state.get("selected_questions", set())
                    if not sel:
                        st.toast("⚠️ 请先勾选要删除的题目")
                    else:
                        for qid in list(sel):
                            question_db.remove_wrong_question(qid, mistake_book=selected_book)
                        st.session_state.selected_questions = set()
                        st.success(f"已删除 {len(sel)} 道题目")
                        time.sleep(1.0)
                        st.rerun()
            else:
                # Normal View: Show Add Mistake
                if st.button("➕ 添加错题", use_container_width=True, key="tb_add"): 
                    st.session_state.active_dialog_id = None 
                    st.session_state.active_dialog_type = "add"
                    st.rerun() 


        # Row 4: Batch Actions (Below, same style/size)
        c_r4_1, c_r4_2, c_r4_3, c_r4_4 = st.columns(4)
        if v_arch: cur_list = [q for q in wrong_questions if q.get("archived", False)]
        else: cur_list = [q for q in wrong_questions if not q.get("archived", False)]
        
        sel_qs = st.session_state.get('selected_questions', set())
        sel_cnt = len(sel_qs)
        
        with c_r4_1:
            if st.button("✅ 全选", use_container_width=True, key="ba_all"):
                # Handle Select All directly
                all_ids = {it["id"] for it in cur_list if it.get("status") != "processing"}
                st.session_state.selected_questions = all_ids
                for qid in all_ids:
                    st.session_state[f"it_chk_{qid}"] = True
                st.session_state.active_dialog_id = None
                st.session_state.active_dialog_type = None
                st.rerun()
                
        with c_r4_2:
            if st.button("❌ 取消", use_container_width=True, key="ba_none", on_click=cb_ba_cancel):
                pass
                
        with c_r4_3:
            v_arch = st.session_state.get("view_archived", False)
            btn_l = f"📤 批量恢复 ({sel_cnt})" if v_arch and sel_cnt > 0 else (f"📥 批量归档 ({sel_cnt})" if sel_cnt > 0 else "📥 批量归档")
            
            # Using on_click for archive to prevent reload race
            if st.button(btn_l, use_container_width=True, disabled=(sel_cnt == 0), key="ba_arch"): 
                 cb_ba_archive(sel_qs, selected_book) # Direct call or on_click? 
                 # Direct block execution is safer for 'args'.
                 # Let's keep block but ensure state is cleared.
                 st.rerun()

        with c_r4_4:
            btn_exp_label = f"📖 展开选中 ({sel_cnt})" if sel_cnt > 0 else "📖 展开选中"
            if st.button(btn_exp_label, use_container_width=True, disabled=(sel_cnt == 0), key="ba_exp", on_click=cb_ba_expand):
                pass
        
        st.divider()

        # Final Filtering & Rendering
        if wrong_questions:
            v_arch = st.session_state.get("view_archived", False)
            if v_arch: cur_list = [q for q in wrong_questions if q.get("archived", False)]
            else: cur_list = [q for q in wrong_questions if not q.get("archived", False)]
            s_opt = st.session_state.get("quiz_sort_order", "📅 添加时间(最新)")
            # Database returns DESC (newest first), so "最早" needs reverse
            if s_opt == "📅 添加时间(最早)": cur_list = cur_list[::-1]
            elif s_opt == "🔥 陌生度(高→低)": cur_list.sort(key=lambda x: x.get("familiarity_score", 0), reverse=True)
            elif s_opt == "✨ 陌生度(低→高)": cur_list.sort(key=lambda x: x.get("familiarity_score", 0))
            
            if not cur_list:
                st.info("暂无归档题目" if v_arch else "暂无待复习题目")
            else:
                for i, item in enumerate(cur_list):
                    with st.container(border=True):
                        q = item["question"]
                        question_text = q.get('question', "（未知题目）")
                        status = item.get("status", "completed")
                        is_processing = status == "processing"
                        
                        if not question_text and q.get("image"):
                            question_text = "（🖼️ 图片题目）"
                        elif not question_text:
                            question_text = "（📝 无内容）"
                        
                        summary_text = item.get("summary") or (question_text[:25] + "..." if len(question_text) > 25 else question_text)
                        if is_processing: summary_text = f"⏳ 处理中... {summary_text}"
                        
                        # Layout: Checkbox | Question Summary | Score | Details Button
                        c_check, c_summ, c_score, c_btn = st.columns([0.05, 0.78, 0.05, 0.12], vertical_alignment="center")
                        
                        selected_ids = st.session_state.get('selected_questions', set())
                        is_checked = item["id"] in selected_ids
                        
                        with c_check:
                            chk_key = f"it_chk_{item['id']}"
                            # Sync session state with external source of truth (selected_questions)
                            if chk_key not in st.session_state:
                                st.session_state[chk_key] = is_checked
                            elif st.session_state[chk_key] != is_checked:
                                st.session_state[chk_key] = is_checked
                                
                            def _on_check_change(k=chk_key, iid=item["id"]):
                                if st.session_state[k]:
                                    st.session_state.selected_questions.add(iid)
                                else:
                                    st.session_state.selected_questions.discard(iid)
                                    
                            st.checkbox(
                                f"选择题目 {item['id']}", 
                                key=chk_key, 
                                label_visibility="collapsed", 
                                disabled=is_processing,
                                on_change=_on_check_change
                            )
                        
                        with c_summ:
                            # Use plain Markdown to ensure ** and LaTeX are parsed correctly
                            # Vertical alignment is handled by st.columns(..., vertical_alignment="center")
                            st.markdown(f"**{i+1}.** {summary_text}")
                        
                        with c_score:
                            f_score = item.get("familiarity_score", 2)
                            # 使用 st.markdown 保持一致，CSS会处理对齐
                            st.markdown(f"{f_score}")
                            
                        with c_btn:
                            if st.button("🔍 详情", key=f"view_det_{item['id']}", use_container_width=True):
                                st.session_state.active_dialog_id = item["id"]
                                st.session_state.active_dialog_type = "single"
                                st.rerun()

# --- Mode: Quiz View ---
elif st.session_state.view_mode == "detail" and st.session_state.mistake_mode == "quiz":
    # Ensure queue exists
    if "quiz_ids" not in st.session_state:
        st.session_state.mistake_mode = "list"
        st.rerun()
        
    quiz_ids = st.session_state.quiz_ids
    
    if not quiz_ids:
        st.success("🎉 复习完成！暂无待复习题目。")
        if st.button("⬅️ 返回列表", type="primary"):
            st.session_state.mistake_mode = "list"
            st.rerun()
        st.stop()
        
    # Ensure index is valid
    if st.session_state.mistake_index >= len(quiz_ids):
        st.session_state.mistake_index = 0
        
    idx = st.session_state.mistake_index
    current_qid = quiz_ids[idx]
    
    # Fetch fresh data for this ID
    # Use optimized fetch if possible, here filtering list
    all_qs = question_db.get_wrong_questions(mistake_book=st.session_state.selected_mistake_book)
    item = next((q for q in all_qs if q['id'] == current_qid), None)
    
    if not item:
        # Item might be deleted? Skip
        if len(quiz_ids) > 1:
            st.session_state.quiz_ids.pop(idx)
            st.rerun()
        else:
            st.session_state.mistake_mode = "list"
            st.rerun()
        st.stop()

    q = item["question"]
    
    # Back Button
    if st.button("⬅️ 中止练习", type="secondary", key="quiz_back_btn"):
        st.session_state.mistake_mode = "list"
        st.session_state.active_dialog_id = None # Clear any potential dialog ID
        st.rerun()
        
    # Header Area: Progress and Score
    c_p1, c_p2 = st.columns([4, 1])
    # Header Area: Progress and Score
    c_p1, c_p2 = st.columns([4, 1])
    with c_p1:
        st.progress((idx + 1) / len(quiz_ids))
        st.caption(f"当前进度: {idx + 1} / {len(quiz_ids)}")
    with c_p2:
        st.metric("陌生度", item.get("familiarity_score", 2))
    
    st.divider()
    
    # Question Body
    if q.get("image"):
        try:
             quiz_img = q.get("image")
             if quiz_img.startswith("http"): st.image(quiz_img)
             else: st.image(base64.b64decode(quiz_img))
        except: st.warning("图片加载失败")

    q_text = q.get('question', '')
    if not q_text and q.get("image"): q_text = "（请参考图片作答）"
    elif not q_text: q_text = "（题目内容为空）"
    
    # For MC/multi-select with options, avoid showing options twice
    # If question text contains numbered options (1. xxx\n2. xxx), extract only the stem
    question_type = q.get("question_type", "multiple_choice")
    options = q.get("options", [])
    if question_type in ["multiple_choice", "multi_select"] and options:
        # Try to split at the first numbered option pattern
        import re
        stem_match = re.split(r'\n\s*[1-4A-Da-d][\.、\s]', q_text)
        if stem_match and len(stem_match[0].strip()) > 0:
            q_text = stem_match[0].strip()
    
    st.markdown(f"#### {q_text}")
    
    # State for current question feedback
    answered_key = f"mistake_answered_{item['id']}"
    if answered_key not in st.session_state:
        st.session_state[answered_key] = False
    
    answered = st.session_state[answered_key]
    # question_type already defined above
    
    # Input Area
    if question_type in ["fill_in_blank", "short_answer"]:
        answers = q.get("answers") or []
        num_blanks = len(answers)
        
        # 如果没有标准答案，使用证明题的自评流程
        if num_blanks == 0:
            if not answered:
                st.info("📝 该题目没有标准答案数据，请先自行完成题目，完成后点击下方按钮查看解析并自评。")
                if st.button("完成练习，查看解析", type="primary", use_container_width=True, key=f"done_btn_{item['id']}"):
                    st.session_state[answered_key] = "eval"
                    st.rerun()
            elif st.session_state[answered_key] == "eval":
                st.warning("🧐 请根据下方解析对自己的作答进行评估：")
                c_yes, c_no = st.columns(2)
                if c_yes.button("✅ 我做对了", use_container_width=True, type="primary", key=f"yes_{item['id']}"):
                    is_correct = True
                    old_score = item.get("familiarity_score", 2)
                    new_score, archived = question_db.update_familiarity_score(item['id'], is_correct, mistake_book=selected_book)
                    st.session_state[answered_key] = True
                    st.session_state[f"score_res_{item['id']}"] = (is_correct, old_score, new_score, archived)
                    st.rerun()
                if c_no.button("❌ 我做错了 / 有误", use_container_width=True, key=f"no_{item['id']}"):
                    is_correct = False
                    old_score = item.get("familiarity_score", 2)
                    new_score, archived = question_db.update_familiarity_score(item['id'], is_correct, mistake_book=selected_book)
                    st.session_state[answered_key] = True
                    st.session_state[f"score_res_{item['id']}"] = (is_correct, old_score, new_score, archived)
                    st.rerun()
        else:
            # 原有的标准答案判断流程
            if f"mistake_blanks_{item['id']}" not in st.session_state:
                st.session_state[f"mistake_blanks_{item['id']}"] = [""] * num_blanks
                
            if not answered:
                user_inputs = []
                for i in range(num_blanks):
                    val = st.text_input(f"空格 {i+1}", key=f"mq_blank_{item['id']}_{i}")
                    user_inputs.append(val)
                
                if st.button("提交答案", type="primary", use_container_width=True):
                    st.session_state[f"mistake_blanks_{item['id']}"] = user_inputs
                    # Updated logic to support multiple potential answers separated by | or ｜
                    correct_count = 0
                    for u, a_str in zip(user_inputs, answers):
                        # Normalize full-width pipe to half-width
                        normalized_a = a_str.replace('｜', '|')
                        valid_ans = [cand.strip().lower() for cand in normalized_a.split('|')]
                        if u.strip().lower() in valid_ans:
                            correct_count += 1
                    
                    is_correct = (correct_count == num_blanks)
                    old_score = item.get("familiarity_score", 2)
                    new_score, archived = question_db.update_familiarity_score(item['id'], is_correct, mistake_book=selected_book)
                    st.session_state[answered_key] = True
                    st.session_state[f"score_res_{item['id']}"] = (is_correct, old_score, new_score, archived)
                    st.rerun()
            else:
                st.markdown("**你的答案：**")
                if num_blanks > 0:
                    cols_ans = st.columns(num_blanks)
                    # Read from the saved blanks array, which is populated on submit
                    saved_blanks = st.session_state.get(f"mistake_blanks_{item['id']}", [""] * num_blanks)
                    for i in range(num_blanks):
                        val = saved_blanks[i] if i < len(saved_blanks) else ""
                        cols_ans[i].info(f"空格 {i+1}: {val}")
                else:
                    st.warning("数据异常：该题目没有答案数据")
    
    elif question_type in ["proof", "mixed"]:
        if not answered:
            st.info("📝 证明题/简答题/混合题请先自行在草稿本完成，完成后点击下方按钮查看标准答案并自评。")
            if st.button("完成练习，查看解析", type="primary", use_container_width=True):
                st.session_state[answered_key] = "eval" # Intermediate state
                st.rerun()
        elif st.session_state[answered_key] == "eval":
            st.warning("🧐 请根据下方解析对自己的作答进行评估：")
            c_yes, c_no = st.columns(2)
            if c_yes.button("✅ 我做对了", use_container_width=True, type="primary"):
                is_correct = True
                old_score = item.get("familiarity_score", 2)
                new_score, archived = question_db.update_familiarity_score(item['id'], is_correct, mistake_book=selected_book)
                st.session_state[answered_key] = True
                st.session_state[f"score_res_{item['id']}"] = (is_correct, old_score, new_score, archived)
                st.rerun()
            if c_no.button("❌ 我做错了 / 有误", use_container_width=True):
                is_correct = False
                old_score = item.get("familiarity_score", 2)
                new_score, archived = question_db.update_familiarity_score(item['id'], is_correct, mistake_book=selected_book)
                st.session_state[answered_key] = True
                st.session_state[f"score_res_{item['id']}"] = (is_correct, old_score, new_score, archived)
                st.rerun()
    
    elif question_type == "multi_select":
        options = q.get("options", [])
        if not answered:
            st.write("请勾选所有正确选项：")
            # Initialize or retrieve selected options from session state
            if f"mq_multi_selected_{item['id']}" not in st.session_state:
                st.session_state[f"mq_multi_selected_{item['id']}"] = []

            current_selected_opts = []
            for idx, opt in enumerate(options):
                # Use a unique key for each checkbox
                is_checked = opt in st.session_state[f"mq_multi_selected_{item['id']}"]
                if st.checkbox(opt, value=is_checked, key=f"quiz_check_{item['id']}_{idx}"):
                    current_selected_opts.append(opt)
            
            # Update session state with current selections
            st.session_state[f"mq_multi_selected_{item['id']}"] = current_selected_opts
            selected_opts = current_selected_opts # Fix NameError for submit logic

            if st.button("提交答案", type="primary", use_container_width=True):
                # Matching logic for multi-select
                def extract_option_key(s):
                    if not s: return ""
                    s = s.strip()
                    # Check for "A. " pattern
                    if len(s) >= 2 and s[0].isalpha() and s[1] in [".", "、", " "]: return s[0].upper()
                    # Check for "1. " pattern
                    if len(s) >= 2 and s[0].isdigit() and s[1] in [".", "、", " "]: 
                        try:
                            # Map 1->A, 2->B
                            return chr(65 + int(s[0]) - 1)
                        except: pass
                    return s
                
                # User's selected keys (e.g. ['A', 'C'])
                user_keys = set()
                for idx, o_text in enumerate(options):
                   if o_text in selected_opts:
                       extracted = extract_option_key(o_text)
                       # If extracted key is not a single letter (meaning no prefix found), map index to letter
                       if len(extracted) > 1:
                           user_keys.add(chr(65 + idx)) # 0->A, 1->B
                       else:
                           user_keys.add(extracted)
                
                # Correct keys
                # correct_answer is like "A, C" or "A C"
                correct_str = q.get('correct_answer', '').replace(',', ' ').upper()
                correct_keys = set(c.strip() for c in correct_str.split() if c.strip())
                
                is_correct = (user_keys == correct_keys)
                old_score = item.get("familiarity_score", 2)
                new_score, archived = question_db.update_familiarity_score(item['id'], is_correct, mistake_book=selected_book)
                st.session_state[answered_key] = True
                st.session_state[f"score_res_{item['id']}"] = (is_correct, old_score, new_score, archived)
                st.rerun()
        else:
            sel_vals = st.session_state.get(f"mq_multi_selected_{item['id']}", [])
            
            # Convert raw selections to A, B, C... keys
            display_keys = []
            options = q.get("options", [])
            
            # Helper logic copy (since extract_option_key is local above)
            for idx, o in enumerate(options):
                if o in sel_vals:
                     key = str(o)
                     s = o.strip()
                     # Try extract A. prefix
                     if len(s) >= 2 and s[0].isalpha() and s[1] in [".", "、", " "]: 
                         key = s[0].upper()
                     # Try extract 1. prefix
                     elif len(s) >= 2 and s[0].isdigit() and s[1] in [".", "、", " "]:
                         try: key = chr(65 + int(s[0]) - 1)
                         except: key = s
                     
                     # If key is still full text (length > 1), map by index
                     if len(key) > 1:
                         key = chr(65 + idx)
                         
                     display_keys.append(key)
            
            final_display = ", ".join(display_keys) if display_keys else "未选择"
            st.info(f"**你的答案：** {final_display}")

    else: # multiple_choice or boolean
        options = q.get("options", [])
        if not answered:
            # 强化 Radio 的稳定性：显式指定 key
            selected_opt = st.radio("选择答案：", options, index=None, key=f"mq_radio_real_{item['id']}")
            
            if st.button("提交答案", type="primary", use_container_width=True, key=f"btn_sub_quiz_{item['id']}"):
                # 获取最新的 radio 状态
                actual_sel = st.session_state.get(f"mq_radio_real_{item['id']}")
                if actual_sel:
                    # Extract Key Logic for Comparison
                    def extract_option_key(s):
                        s = str(s).strip()
                        # Standard "A. Content"
                        if len(s) >= 2 and s[0].isalpha() and s[1] in [".", "、", " "]: return s[0].upper()
                        return s.strip()
                    
                    user_key = extract_option_key(actual_sel)
                    correct_key = str(q.get('correct_answer')).strip()
                    
                    is_correct = (user_key.upper() == correct_key.upper()) or (actual_sel.strip() == correct_key)
                    
                    old_score = item.get("familiarity_score", 2)
                    new_score, archived = question_db.update_familiarity_score(item['id'], is_correct, mistake_book=selected_book)
                    st.session_state[answered_key] = True
                    st.session_state[f"score_res_{item['id']}"] = (is_correct, old_score, new_score, archived)
                    st.rerun()
                else:
                    st.warning("请在提交前先选择一个选项")
        else:
            sel_val = st.session_state.get(f"mq_radio_real_{item['id']}", '未选择')
            st.info(f"**你的答案：** {sel_val}")

    # Result and Navigation Area (After Answered)
    if answered:
        res = st.session_state.get(f"score_res_{item['id']}")
        if res:
            is_correct, old_score, new_score, archived = res
            arrow = "↘️" if new_score < old_score else ("↗️" if new_score > old_score else "➡️")
            score_txt = f" (陌生度: {old_score} {arrow} {new_score}{', 已自动归档' if archived else ''})"
            
            if is_correct: st.success(f"✅ 回答正确！{score_txt}")
            else: st.error(f"❌ 回答错误！{score_txt}")
        
        st.divider()
        
        # Actions Row
        st.divider()
        
        # Actions Row
        c_nav, c_arch = st.columns(2)
        is_last = (idx + 1) >= len(quiz_ids)
        btn_next_label = "✅ 完成复习" if is_last else "➡️ 下一题"
        
        with c_nav:
            if st.button(btn_next_label, type="primary", use_container_width=True):
                if is_last:
                    st.session_state.mistake_mode = "list"
                    st.session_state.active_dialog_id = None # Clear dialog
                else:
                    st.session_state.mistake_index += 1
                st.rerun()
        
        with c_arch:
            new_is_archived = item.get("archived", False)
            arc_label = "📤 取消归档" if new_is_archived else "📥 归档此题"
            
            if st.button(arc_label, use_container_width=True, key=f"btn_quiz_arc_{item['id']}"):
                question_db.toggle_archive(item['id'], mistake_book=st.session_state.selected_mistake_book)
                st.rerun()
                
        # Report/Edit Feature in Post-Quiz
        def _go_to_edit_from_quiz():
            st.session_state.active_dialog_id = item["id"]
            st.session_state.active_dialog_type = "single"
            st.session_state[f"dialog_mode_{item['id']}"] = "edit"
            st.session_state.mistake_mode = "list" # Switch to list mode to show dialog
            st.session_state.return_to_quiz = True # Set flag to return
            
        st.button("🛠️ 题目/答案有误？点击修改", use_container_width=True, key=f"btn_quiz_err_{item['id']}", on_click=_go_to_edit_from_quiz)
        
        # Explanation Area
        with st.container(border=True):
            st.markdown("### 📝 详解")
            if question_type in ["multiple_choice", "multi_select", "boolean"]:
                st.markdown(f"**正确选项：** {q.get('correct_answer')}")
            else:
                st.markdown("**正确答案：**")
                ans_list = q.get("answers") or []
                if ans_list:
                    for ans in ans_list: st.markdown(f"- {ans}")
                else:
                    st.markdown(f"- {q.get('correct_answer', '（空）')}")
            st.info(q.get("explanation", "暂无解析"))

