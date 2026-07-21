"""
Omni-Writer AI (全栈工业化终局版)
Gradio Web 可视化创作控制台

访问地址：http://127.0.0.1:7860
"""

import gradio as gr
import re
import json
from engine.llm_router import LLMRouter
from engine.state_manager import StateManager
from engine.knowledge_base import KnowledgeBase
from engine.outline_manager import OutlineManager
from prompts.writer_prompt import WRITER_SYSTEM_PROMPT, build_writer_user_prompt
from prompts.material_prompt import MATERIAL_SYSTEM_PROMPT, build_material_user_prompt
from prompts.sanitizer_prompt import SANITIZER_SYSTEM_PROMPT, build_sanitizer_user_prompt
from prompts.planner_prompt import PLANNER_SYSTEM_PROMPT, build_planner_user_prompt
from prompts.negotiator_prompt import NEGOTIATOR_SYSTEM_PROMPT, build_negotiator_user_prompt
from prompts.redrawer_prompt import REDRAWER_SYSTEM_PROMPT, build_redrawer_user_prompt
from prompts.radar_prompt import RADAR_SYSTEM_PROMPT, build_radar_user_prompt

# ================= 初始化全局组件 =================
router = LLMRouter()
state_manager = StateManager()
kb = KnowledgeBase()
outline_manager = OutlineManager()


def extract_json_from_text(text):
    """从可能包含杂质的文本中提取 JSON"""
    match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
        return match.group(1)
    return None


# ================= 界面回调函数 =================

def init_project_ui(inspiration):
    """初始化项目：生成大纲"""
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
    """生成下一章的完整流水线（生成器，支持逐行输出日志）"""
    current_ch = state_manager.state['current_chapter'] + 1
    ch_info = outline_manager.get_next_chapter_info(current_ch)
    chapter_outline = ch_info['outline']
    scene_type = ch_info['scene_type']

    logs = f"📋 本章大纲节点：第 {current_ch} 章 - {chapter_outline} (场景: {scene_type})\n"
    yield logs, ""

    negotiation_dialogue = ""
    if scene_type == "negotiation":
        logs += "🎭 检测到智斗场景，启动多 Agent 谈判模拟器...\n"
        yield logs, ""
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
        yield logs, ""

    context = {
        "current_chapter": current_ch,
        "chapter_outline": chapter_outline,
        "character_state": state_manager.state['character_current_state'],
        "active_foreshadowing": state_manager.state['active_foreshadowing'],
        "negotiation_dialogue": negotiation_dialogue
    }

    logs += "🔍 正在从知识库检索相关素材...\n"
    yield logs, ""
    retrieved_materials = kb.retrieve_materials(context['chapter_outline'], top_k=2)
    context['retrieved_materials'] = retrieved_materials

    logs += "📝 正在生成正文初稿...\n"
    yield logs, ""
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
    yield logs, ""
    radar_response = router.chat(
        task_type="planner",
        system_prompt=RADAR_SYSTEM_PROMPT,
        user_prompt=build_radar_user_prompt(raw_text_part)
    )
    radar_json_str = extract_json_from_text(radar_response)
    checked_text = raw_text_part
    if radar_json_str:
        try:
            radar_data = json.loads(radar_json_str)
            score = radar_data.get("originality_score", 0)
            issues = radar_data.get("issues_found", [])
            logs += f"🚨 雷达扫描得分: {score} | 发现问题: {len(issues)}处\n"
            if score < 80 or issues:
                logs += "🛠️ 检测到毒点/套路，已自动触发重写修复...\n"
            checked_text = radar_data.get("fixed_text", raw_text_part)
        except Exception:
            pass
    yield logs, ""

    logs += "🛡️ 正在进行 AI 痕迹脱敏与人类化处理...\n"
    yield logs, ""
    sanitized_text = router.chat(
        task_type="sanitizer",
        system_prompt=SANITIZER_SYSTEM_PROMPT,
        user_prompt=build_sanitizer_user_prompt(checked_text)
    )

    final_output = (
        f"{sanitized_text}\n\n<state_update_json>\n{json_part}\n</state_update_json>"
    )
    state_manager.update_state_from_chapter(final_output)

    logs += "✅ 本章生成完毕！\n"
    yield logs, sanitized_text


def redraw_ui(selected_text, instruction, current_chapter_text):
    """局部重绘功能"""
    if not selected_text or selected_text not in current_chapter_text:
        return "未能匹配到选定文本，请确保在上方文本框中选中了一段话。", current_chapter_text

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
    return "✨ 重绘成功，已替换文本！", new_chapter_text


# ================= Gradio 界面布局 =================

with gr.Blocks(title="Omni-Writer AI", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🚀 Omni-Writer AI (全栈工业化终局版)
    ### 灵感 -> 大纲 -> RAG检索 -> 谈判模拟 -> 正文生成 -> 雷达自检 -> 脱敏精修 -> 状态更新
    """)

    with gr.Tab("创世引擎"):
        gr.Markdown("### 输入一句话灵感，生成整书大纲骨架")
        inspiration_input = gr.Textbox(
            label="一句话灵感",
            placeholder="例如：修仙+赛博朋克+黑客流，主角靠代码入侵天道系统"
        )
        with gr.Row():
            init_btn = gr.Button("⚡ 开始创世", variant="primary")
        outline_output = gr.Textbox(
            label="大纲概览", lines=10, interactive=False
        )
        start_writing_btn = gr.Button("前往创作流水线 ➡️", visible=False)

        init_btn.click(
            init_project_ui,
            inputs=[inspiration_input],
            outputs=[outline_output, start_writing_btn]
        )

    with gr.Tab("创作流水线"):
        gr.Markdown("### 全自动网文工业流水线")
        with gr.Row():
            with gr.Column(scale=1):
                gen_btn = gr.Button("⚙️ 生成下一章", variant="primary", size="lg")
                gr.Markdown("---")
                redraw_selected = gr.Textbox(
                    label="待重绘文本 (从右侧复制粘贴)", lines=3
                )
                redraw_inst = gr.Textbox(
                    label="重绘要求 (可留空)", placeholder="例如：增加更多微表情描写"
                )
                redraw_btn = gr.Button("🖌️ 局部重绘")
                redraw_status = gr.Textbox(label="重绘状态", interactive=False)

            with gr.Column(scale=2):
                log_output = gr.Textbox(
                    label="工业流水线日志", lines=8, interactive=False
                )
                chapter_output = gr.Textbox(
                    label="本章正文 (已脱敏+已自检，可编辑)",
                    lines=22, interactive=True
                )

        gen_btn.click(
            generate_next_chapter_ui,
            inputs=None,
            outputs=[log_output, chapter_output]
        )
        redraw_btn.click(
            redraw_ui,
            inputs=[redraw_selected, redraw_inst, chapter_output],
            outputs=[redraw_status, chapter_output]
        )


if __name__ == "__main__":
    # 启动时如果没有素材，自动塞入测试素材
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

    demo.launch(server_name="0.0.0.0", server_port=7860)
