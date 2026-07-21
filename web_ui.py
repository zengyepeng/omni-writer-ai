"""
Omni-Writer AI (全栈工业化终局版)
Gradio Web 可视化创作控制台

访问地址：http://127.0.0.1:7860
支持：多本书管理 | 章节回退 | 大纲续写 | 全书导出 | 章节浏览 | 进度可视化
"""

import gradio as gr
import re
import json
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)

from engine.llm_router import LLMRouter
from engine.state_manager import StateManager
from engine.knowledge_base import KnowledgeBase
from engine.outline_manager import OutlineManager
from engine.exporter import export_book
from prompts.writer_prompt import WRITER_SYSTEM_PROMPT, build_writer_user_prompt
from prompts.material_prompt import MATERIAL_SYSTEM_PROMPT, build_material_user_prompt
from prompts.sanitizer_prompt import SANITIZER_SYSTEM_PROMPT, build_sanitizer_user_prompt
from prompts.planner_prompt import PLANNER_SYSTEM_PROMPT, build_planner_user_prompt, build_extend_prompt
from prompts.negotiator_prompt import NEGOTIATOR_SYSTEM_PROMPT, build_negotiator_user_prompt
from prompts.redrawer_prompt import REDRAWER_SYSTEM_PROMPT, build_redrawer_user_prompt
from prompts.radar_prompt import RADAR_SYSTEM_PROMPT, build_radar_user_prompt

# ================= 初始化 =================
import sys

if not os.path.exists("config.yaml"):
    print("=" * 55)
    print("  ❌ 未找到 config.yaml 配置文件")
    print("=" * 55)
    print()
    print("  解决方法（任选其一）：")
    print("  1. 双击运行 install.bat（推荐，自动配置）")
    print("  2. 复制 config.example.yaml 为 config.yaml 并填入 API Key")
    print("  3. 运行 python demo_mode.py 体验演示模式（无需 Key）")
    print()
    sys.exit(1)

StateManager.migrate_legacy_data()

router = LLMRouter()
kb = KnowledgeBase()

# API Key 预检
_test_key = router.config['llm_config']['api_key']
if _test_key.startswith("sk-your"):
    print("=" * 55)
    print("  ⚠️  config.yaml 中的 API Key 还是占位符")
    print("=" * 55)
    print()
    print("  请把 config.yaml 里的 sk-your-api-key-here")
    print("  替换为你的真实 DeepSeek API Key：")
    print("  https://platform.deepseek.com/api_keys")
    print()
    sys.exit(1)

current_book = "default"
state_manager = StateManager(current_book)
outline_manager = OutlineManager(current_book)


def extract_json_from_text(text):
    """从可能包含杂质的文本中提取 JSON（非贪婪匹配）"""
    match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r'(\{.*?\})', text, re.DOTALL)
    if match:
        return match.group(1)
    return None


def get_book_choices():
    books = StateManager.list_books()
    if not books:
        books = ["default"]
    return books + ["➕ 新建书籍..."]


def get_chapter_list():
    """获取已生成章节列表"""
    chapters_dir = state_manager.chapters_dir
    if not os.path.exists(chapters_dir):
        return []
    files = sorted(
        f for f in os.listdir(chapters_dir) if f.endswith('.txt')
    )
    result = []
    for f in files:
        ch_num = int(f.replace("chapter_", "").replace(".txt", ""))
        result.append(f"第 {ch_num} 章")
    return result


def load_chapter(chapter_label):
    """加载指定章节内容"""
    if not chapter_label:
        return "请选择一个章节", ""
    ch_num = int(chapter_label.replace("第 ", "").replace(" 章", ""))
    text = state_manager.get_chapter_text(ch_num)
    if text:
        return f"✅ 已加载第 {ch_num} 章", text
    return f"❌ 第 {ch_num} 章不存在", ""


def get_progress_html():
    """生成进度可视化 HTML"""
    current = state_manager.state.get('current_chapter', 0)
    total = outline_manager.get_total_chapters()
    if total == 0:
        pct = 0
    else:
        pct = min(100, int(current / total * 100))

    color = "#22c55e" if pct >= 80 else "#f59e0b" if pct >= 40 else "#3b82f6"
    bar_width = max(pct, 2)

    return f"""
    <div style="margin:8px 0;">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
        <span style="font-size:13px;color:#666;">写作进度</span>
        <span style="font-size:13px;font-weight:600;color:{color};">{current}/{total} 章 ({pct}%)</span>
      </div>
      <div style="background:#e5e7eb;border-radius:6px;height:10px;overflow:hidden;">
        <div style="background:{color};width:{bar_width}%;height:100%;border-radius:6px;transition:width 0.5s ease;"></div>
      </div>
    </div>
    """


def get_foreshadowing_html():
    """生成伏笔列表 HTML"""
    fs_list = state_manager.state.get('active_foreshadowing', [])
    if not fs_list:
        return "<div style='color:#999;font-size:13px;padding:8px;'>暂无未回收伏笔</div>"
    items = "".join(
        f"<li style='margin:4px 0;font-size:13px;color:#555;'>📌 {fs}</li>"
        for fs in fs_list[-10:]  # 最多显示10条
    )
    return f"<ul style='margin:0;padding-left:16px;'>{items}</ul>"


def get_status():
    """获取当前状态"""
    current = state_manager.state.get('current_chapter', 0)
    total = outline_manager.get_total_chapters()
    fs_count = len(state_manager.state.get('active_foreshadowing', []))
    char_state = state_manager.state.get('character_current_state', '未知')
    title = outline_manager.outline_data.get('book_title', '未命名') if outline_manager.outline_data else '未命名'

    return (
        f"📖 {title} | 进度: 第{current}章 / 已规划{total}章 | "
        f"伏笔: {fs_count}条 | 主角: {char_state[:40]}"
    )


def refresh_all():
    """刷新所有面板"""
    return (
        get_status(),
        get_progress_html(),
        get_foreshadowing_html(),
        gr.update(choices=get_chapter_list()),
    )


# ================= 界面回调函数 =================

def switch_book(book_choice, new_book_name):
    global current_book, state_manager, outline_manager

    if book_choice == "➕ 新建书籍...":
        if not new_book_name.strip():
            return "请输入新书籍名称", gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
        book_name = new_book_name.strip()
    else:
        book_name = book_choice

    current_book = book_name
    state_manager = StateManager(book_name)
    outline_manager = OutlineManager(book_name)

    status = f"📖 已切换到「{book_name}」"
    if outline_manager.outline_data:
        status += f" | 书名：{outline_manager.outline_data.get('book_title', '未命名')}"
        status += f" | 进度：第 {state_manager.state.get('current_chapter', 0)} 章"
    else:
        status += " | 尚未创建大纲，请前往「创世引擎」"

    return (
        status,
        gr.update(choices=get_book_choices(), value=book_name),
        get_progress_html(),
        get_foreshadowing_html(),
        gr.update(choices=get_chapter_list()),
        ""
    )


def init_project_ui(inspiration):
    if outline_manager.outline_data:
        return "大纲已存在，无需重复生成。", gr.update(visible=True)

    if not inspiration:
        return "请输入灵感。", gr.update(visible=False)

    outline_str = router.chat(
        task_type="planner",
        system_prompt=PLANNER_SYSTEM_PROMPT,
        user_prompt=build_planner_user_prompt(inspiration)
    )
    outline_manager.save_outline(outline_str)

    if outline_manager.outline_data:
        state_manager.state['character_current_state'] = \
            outline_manager.outline_data.get('protagonist_setting', '初始状态')
        state_manager.save_state()

    outline_summary = (
        f"📚 书名：{outline_manager.outline_data.get('book_title')}\n"
        f"📝 简介：{outline_manager.outline_data.get('synopsis')}\n"
        f"👤 主角：{outline_manager.outline_data.get('protagonist_setting')}\n\n"
        f"✅ 大纲生成完毕，可以开始生成正文了！"
    )
    return outline_summary, gr.update(visible=True)


def generate_next_chapter_ui():
    current_ch = state_manager.state['current_chapter'] + 1
    ch_info = outline_manager.get_next_chapter_info(current_ch)
    chapter_outline = ch_info['outline']
    scene_type = ch_info['scene_type']

    logs = f"📋 本章大纲节点：第 {current_ch} 章 - {chapter_outline} (场景: {scene_type})\n"
    yield logs, "", "", ""

    negotiation_dialogue = ""
    if scene_type == "negotiation":
        logs += "🎭 检测到智斗场景，启动多 Agent 谈判模拟器...\n"
        yield logs, "", "", ""
        characters = {
            "主角": "隐藏实力，试图套出对方的底牌",
            "反派长老": "咄咄逼人，怀疑主角身份，试图打压"
        }
        negotiation_dialogue = router.chat(
            task_type="planner",
            system_prompt=NEGOTIATOR_SYSTEM_PROMPT,
            user_prompt=build_negotiator_user_prompt(chapter_outline, characters)
        )
        logs += "✅ 谈判记录生成完毕。\n"
        yield logs, "", "", ""

    context = {
        "current_chapter": current_ch,
        "chapter_outline": chapter_outline,
        "character_state": state_manager.state['character_current_state'],
        "active_foreshadowing": state_manager.state['active_foreshadowing'],
        "negotiation_dialogue": negotiation_dialogue
    }

    logs += "🔍 正在从知识库检索相关素材...\n"
    yield logs, "", "", ""
    retrieved_materials = kb.retrieve_materials(context['chapter_outline'], top_k=2)
    context['retrieved_materials'] = retrieved_materials

    logs += "📝 正在生成正文初稿...\n"
    yield logs, "", "", ""
    user_prompt = build_writer_user_prompt(context)
    raw_output = router.chat(
        task_type="writer",
        system_prompt=WRITER_SYSTEM_PROMPT,
        user_prompt=user_prompt
    )

    match = re.search(
        r'<state_update_json>(.*)</state_update_json>',
        raw_output, re.DOTALL
    )
    if match:
        raw_text_part = raw_output[:match.start()].strip()
        json_part = match.group(1).strip()
    else:
        raw_text_part = raw_output
        json_part = ""

    logs += "📡 启动原创性雷达，扫描毒点与套路...\n"
    yield logs, "", "", ""
    radar_response = router.chat(
        task_type="planner",
        system_prompt=RADAR_SYSTEM_PROMPT,
        user_prompt=build_radar_user_prompt(raw_text_part)
    )
    radar_json_str = extract_json_from_text(radar_response)
    checked_text = raw_text_part
    radar_score = "未扫描"
    if radar_json_str:
        try:
            radar_data = json.loads(radar_json_str)
            score = radar_data.get("originality_score", 0)
            issues = radar_data.get("issues_found", [])
            radar_score = f"{score}分"
            logs += f"🚨 雷达扫描得分: {score} | 发现问题: {len(issues)}处\n"
            if score < 80 or issues:
                logs += "🛠️ 检测到毒点/套路，已自动触发重写修复...\n"
            checked_text = radar_data.get("fixed_text", raw_text_part)
        except Exception:
            pass
    yield logs, "", "", ""

    logs += "🛡️ 正在进行 AI 痕迹脱敏与人类化处理...\n"
    yield logs, "", "", ""
    sanitized_text = router.chat(
        task_type="sanitizer",
        system_prompt=SANITIZER_SYSTEM_PROMPT,
        user_prompt=build_sanitizer_user_prompt(checked_text)
    )

    final_output = (
        f"{sanitized_text}\n\n<state_update_json>\n{json_part}\n</state_update_json>"
    )
    state_manager.update_state_from_chapter(final_output)
    state_manager.save_chapter(current_ch, sanitized_text)
    state_manager.create_snapshot()

    logs += f"✅ 第 {current_ch} 章生成完毕！雷达得分: {radar_score}\n"

    # 返回时同时刷新章节列表和进度
    yield logs, sanitized_text, get_progress_html(), gr.update(choices=get_chapter_list())


def redraw_ui(selected_text, instruction, current_chapter_text):
    if not selected_text or selected_text not in current_chapter_text:
        return "❌ 未能匹配到选定文本，请从右侧文本框中精确复制一段", current_chapter_text

    idx = current_chapter_text.find(selected_text)
    text_before = current_chapter_text[:idx]
    text_after = current_chapter_text[idx + len(selected_text):]

    redrawn_text = router.chat(
        task_type="planner",
        system_prompt=REDRAWER_SYSTEM_PROMPT,
        user_prompt=build_redrawer_user_prompt(
            text_before, selected_text, text_after, instruction
        )
    )

    new_chapter_text = text_before + redrawn_text + text_after
    current_ch = state_manager.state.get('current_chapter', 0)
    if current_ch > 0:
        state_manager.save_chapter(current_ch, new_chapter_text)

    return "✨ 重绘成功，已替换并同步存档！", new_chapter_text


def rollback_ui(target_chapter):
    try:
        target = int(target_chapter)
    except (ValueError, TypeError):
        return "❌ 请输入有效章节号", "", get_progress_html(), gr.update()

    success, msg = state_manager.rollback_to_chapter(target)
    icon = "✅" if success else "❌"
    return f"{icon} {msg}", "", get_progress_html(), gr.update(choices=get_chapter_list())


def extend_outline_ui():
    if not outline_manager.outline_data:
        return "❌ 请先创建大纲"

    volumes = outline_manager.outline_data.get('volumes', [])
    if not volumes:
        return "❌ 大纲为空"

    last_vol = volumes[-1]
    summary = {
        'total_volumes': len(volumes),
        'next_volume_num': last_vol['volume_number'] + 1,
        'last_volume_title': last_vol.get('volume_title', ''),
        'last_volume_conflict': last_vol.get('core_conflict', '')
    }

    prompt = build_extend_prompt(
        book_title=outline_manager.outline_data.get('book_title', ''),
        synopsis=outline_manager.outline_data.get('synopsis', ''),
        current_volumes_summary=summary,
        protagonist_state=state_manager.state.get('character_current_state', ''),
        active_foreshadowing=state_manager.state.get('active_foreshadowing', [])
    )

    new_vol_str = router.chat(
        task_type="planner",
        system_prompt=PLANNER_SYSTEM_PROMPT,
        user_prompt=prompt
    )

    if outline_manager.extend_outline(new_vol_str):
        return f"✅ 第 {summary['next_volume_num']} 卷续写成功！已追加 {len(new_vol_str)//100} 章"
    return "❌ 续写失败，请重试"


def export_ui(fmt_choice):
    fmt = "md" if "Markdown" in fmt_choice else "txt"
    path, msg = export_book(current_book, fmt)
    icon = "✅" if path else "❌"
    return f"{icon} {msg}"


# ================= Gradio 界面布局 =================

custom_css = """
.gradio-container { max-width: 1400px !important; }
.status-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; border-radius: 12px; padding: 16px 20px;
    font-size: 14px; line-height: 1.6;
}
.status-card b { font-size: 16px; }
"""

with gr.Blocks(
    title="Omni-Writer AI",
    theme=gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="purple",
        neutral_hue="slate"
    ),
    css=custom_css
) as demo:

    # ===== 顶部状态栏 =====
    with gr.Row(elem_classes="status-card"):
        with gr.Column(scale=3):
            status_bar = gr.Textbox(
                label="", interactive=False, value=get_status(),
                show_label=False, container=False
            )
        with gr.Column(scale=1):
            gr.Markdown("### 🚀 Omni-Writer AI")

    # ===== 书籍切换 =====
    with gr.Row():
        book_dropdown = gr.Dropdown(
            choices=get_book_choices(), value=current_book,
            label="📚 当前书籍", scale=2
        )
        new_book_input = gr.Textbox(
            label="新书籍名", placeholder="输入名称", scale=1, visible=False
        )
        switch_btn = gr.Button("🔄 切换", scale=1, variant="secondary")

    def on_book_change(choice):
        return gr.update(visible=(choice == "➕ 新建书籍..."))

    book_dropdown.change(on_book_change, inputs=[book_dropdown], outputs=[new_book_input])

    # ===== 进度与伏笔面板 =====
    with gr.Row():
        with gr.Column(scale=1):
            progress_html = gr.HTML(value=get_progress_html(), label="📊 写作进度")
        with gr.Column(scale=1):
            foreshadowing_html = gr.HTML(value=get_foreshadowing_html(), label="📌 未回收伏笔")

    # ===== 主 Tab 区 =====
    with gr.Tab("✨ 创世引擎"):
        gr.Markdown("### 输入一句话灵感，生成整书大纲骨架")
        inspiration_input = gr.Textbox(
            label="💡 一句话灵感",
            placeholder="例如：修仙+赛博朋克+黑客流，主角靠代码入侵天道系统",
            lines=2
        )
        with gr.Row():
            init_btn = gr.Button("⚡ 开始创世", variant="primary", size="lg")
            extend_btn = gr.Button("📖 续写下一卷大纲", size="lg")
        outline_output = gr.Textbox(label="📋 大纲概览", lines=12, interactive=False)
        extend_status = gr.Textbox(label="续写状态", interactive=False)

        init_btn.click(init_project_ui, inputs=[inspiration_input], outputs=[outline_output, gr.Button(visible=False)])
        extend_btn.click(extend_outline_ui, outputs=[extend_status])

    with gr.Tab("⚙️ 创作流水线"):
        with gr.Row():
            with gr.Column(scale=1):
                gen_btn = gr.Button("⚙️ 生成下一章", variant="primary", size="lg")

                gr.Markdown("---")
                gr.Markdown("### 🖌️ 局部重绘")
                redraw_selected = gr.Textbox(label="待重绘文本（从右侧复制）", lines=3)
                redraw_inst = gr.Textbox(label="重绘要求（可留空）", placeholder="例如：增加更多微表情描写")
                redraw_btn = gr.Button("🖌️ 执行重绘")
                redraw_status = gr.Textbox(label="重绘状态", interactive=False)

                gr.Markdown("---")
                gr.Markdown("### ⏪ 章节回退")
                rollback_input = gr.Number(label="回退到第几章", value=1, precision=0)
                rollback_btn = gr.Button("⏪ 执行回退", variant="stop")
                rollback_status = gr.Textbox(label="回退状态", interactive=False)

            with gr.Column(scale=2):
                log_output = gr.Textbox(label="📟 工业流水线日志", lines=8, interactive=False)
                chapter_output = gr.Textbox(
                    label="📄 本章正文（已脱敏+已自检，可编辑）",
                    lines=24, interactive=True
                )

        gen_btn.click(
            generate_next_chapter_ui,
            outputs=[log_output, chapter_output, progress_html, gr.State()]
        )
        redraw_btn.click(redraw_ui, inputs=[redraw_selected, redraw_inst, chapter_output], outputs=[redraw_status, chapter_output])
        rollback_btn.click(rollback_ui, inputs=[rollback_input], outputs=[rollback_status, chapter_output, progress_html, gr.State()])

    with gr.Tab("📚 章节浏览"):
        gr.Markdown("### 浏览已生成的章节")
        with gr.Row():
            chapter_dropdown = gr.Dropdown(
                choices=get_chapter_list(), label="选择章节", scale=2
            )
            load_btn = gr.Button("📖 加载章节", scale=1)
        load_status = gr.Textbox(label="加载状态", interactive=False)
        chapter_viewer = gr.Textbox(label="章节内容", lines=25, interactive=False)

        load_btn.click(load_chapter, inputs=[chapter_dropdown], outputs=[load_status, chapter_viewer])

    with gr.Tab("📦 导出"):
        gr.Markdown("### 导出全书为单个文件")
        export_fmt = gr.Radio(["TXT", "Markdown"], value="TXT", label="导出格式")
        export_btn = gr.Button("📦 导出全书", variant="primary", size="lg")
        export_status = gr.Textbox(label="导出状态", interactive=False)

        export_btn.click(export_ui, inputs=[export_fmt], outputs=[export_status])

    # ===== 事件绑定 =====
    switch_btn.click(
        switch_book,
        inputs=[book_dropdown, new_book_input],
        outputs=[status_bar, book_dropdown, progress_html, foreshadowing_html, chapter_dropdown, chapter_output]
    )

    # 定时刷新
    refresh_timer = gr.Timer(5)
    refresh_timer.tick(
        lambda: (get_status(), get_progress_html(), get_foreshadowing_html()),
        outputs=[status_bar, progress_html, foreshadowing_html]
    )


if __name__ == "__main__":
    if kb.collection.count() == 0:
        print("[WebUI] 素材库为空，正在注入测试素材...")
        raw_material = (
            "在量子力学中，观察者效应意味着粒子的状态在被测量之前是不确定的。"
            "这可以映射到修仙中：功法境界在被天道'观测'之前，处于成仙与入魔的叠加态。"
        )
        clean_material = router.chat(
            task_type="planner",
            system_prompt=MATERIAL_SYSTEM_PROMPT,
            user_prompt=build_material_user_prompt(raw_material)
        )
        kb.add_material(clean_material, source="量子修仙设定")

    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        max_threads=40,
        show_error=True
    )
