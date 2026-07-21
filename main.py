"""
Omni-Writer AI (全栈工业化终局版)
CLI 命令行入口 —— 交互式网文创作流水线

流水线：灵感 -> 大纲 -> RAG检索 -> 谈判模拟 -> 正文生成 -> 雷达自检 -> 脱敏精修 -> 状态更新
支持：多本书管理 | 章节回退 | 大纲续写 | 全书导出 | 章节浏览 | 帮助
"""

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
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.text import Text
import re
import json
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)

console = Console()


def extract_json_from_text(text):
    """从可能包含杂质的文本中提取 JSON（非贪婪匹配）"""
    match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r'(\{.*?\})', text, re.DOTALL)
    if match:
        return match.group(1)
    return None


def spinner_task(description, func, *args, **kwargs):
    """带加载动画的任务执行"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        progress.add_task(description, total=None)
        result = func(*args, **kwargs)
    return result


def select_book():
    """选择或创建书籍"""
    StateManager.migrate_legacy_data()
    books = StateManager.list_books()

    if books:
        console.print("\n[bold cyan]📚 已有书籍：[/bold cyan]")
        for i, b in enumerate(books, 1):
            sm = StateManager(b)
            om = OutlineManager(b)
            ch = sm.state.get('current_chapter', 0)
            title = om.outline_data.get('book_title', b) if om.outline_data else b
            console.print(f"  {i}. {title} [dim]({b}) — 第 {ch} 章[/dim]")
        console.print(f"  {len(books) + 1}. [bold green]➕ 新建书籍[/bold green]")

        choice = console.input("\n[bold green]请选择编号: [/bold green]")
        try:
            idx = int(choice)
            if 1 <= idx <= len(books):
                return books[idx - 1]
        except ValueError:
            pass

    book_name = console.input("[bold green]输入新书籍名称（英文或拼音）: [/bold green]").strip()
    if not book_name:
        book_name = "default"
    return book_name


def initialize_project(book_name):
    """初始化项目"""
    router = LLMRouter()
    state_manager = StateManager(book_name)
    kb = KnowledgeBase()
    outline_manager = OutlineManager(book_name)

    if not outline_manager.outline_data:
        console.print(f"[bold red]⚠️ 「{book_name}」未检测到小说大纲，我们需要先创世！[/bold red]")
        inspiration = console.input(
            "[bold cyan]请输入你的一句话灵感（例如：修仙+赛博朋克+黑客流）：[/bold cyan] "
        )

        outline_str = spinner_task(
            "🧠 正在构建整书大纲架构...",
            router.chat,
            task_type="planner",
            system_prompt=PLANNER_SYSTEM_PROMPT,
            user_prompt=build_planner_user_prompt(inspiration)
        )
        outline_manager.save_outline(outline_str)
        outline_manager.print_outline_summary()

        if outline_manager.outline_data:
            state_manager.state['character_current_state'] = \
                outline_manager.outline_data.get('protagonist_setting', '初始状态')
            state_manager.save_state()

    return router, state_manager, kb, outline_manager


def show_book_status(state_manager, outline_manager):
    """显示当前书籍状态面板"""
    current = state_manager.state.get('current_chapter', 0)
    total = outline_manager.get_total_chapters()
    fs_count = len(state_manager.state.get('active_foreshadowing', []))
    char_state = state_manager.state.get('character_current_state', '未知')

    pct = min(100, int(current / total * 100)) if total > 0 else 0
    bar_len = 20
    filled = int(bar_len * pct / 100)
    bar = "█" * filled + "░" * (bar_len - filled)
    color = "green" if pct >= 80 else "yellow" if pct >= 40 else "blue"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("项", style="cyan", width=8)
    table.add_column("值", style="green")

    title = outline_manager.outline_data.get('book_title', '未命名') if outline_manager.outline_data else '未命名'
    table.add_row("📖 书名", title)
    table.add_row("📊 进度", f"[{color}]{bar}[/{color}] {current}/{total} 章 ({pct}%)")
    table.add_row("📌 伏笔", f"{fs_count} 条未回收")
    table.add_row("👤 主角", char_state[:60] + ("..." if len(char_state) > 60 else ""))

    console.print(Panel(table, title="[bold]当前状态[/bold]", border_style="blue", padding=(0, 1)))


def show_help():
    """显示帮助"""
    help_table = Table(title="📖 命令帮助", show_header=True, header_style="bold magenta")
    help_table.add_column("命令", style="cyan", width=6)
    help_table.add_column("说明", style="white")
    help_table.add_row("n", "生成下一章正文")
    help_table.add_row("r", "局部重绘上一章的指定段落")
    help_table.add_row("l", "浏览已生成的章节列表")
    help_table.add_row("b", "回退到指定章节（删除后续章节）")
    help_table.add_row("e", "续写下一卷大纲")
    help_table.add_row("x", "导出全书为 TXT / Markdown")
    help_table.add_row("s", "切换书籍")
    help_table.add_row("h", "显示本帮助")
    help_table.add_row("q", "退出程序")
    console.print(help_table)


def cmd_browse_chapters(state_manager):
    """浏览章节列表"""
    chapters_dir = state_manager.chapters_dir
    import os
    if not os.path.exists(chapters_dir):
        console.print("[bold red]暂无已生成章节。[/bold red]")
        return

    files = sorted(f for f in os.listdir(chapters_dir) if f.endswith('.txt'))
    if not files:
        console.print("[bold red]暂无已生成章节。[/bold red]")
        return

    console.print("\n[bold cyan]📚 已生成章节：[/bold cyan]")
    for f in files:
        ch_num = int(f.replace("chapter_", "").replace(".txt", ""))
        filepath = os.path.join(chapters_dir, f)
        size = os.path.getsize(filepath)
        console.print(f"  第 {ch_num:>3} 章  [dim]({size/1024:.1f} KB)[/dim]")

    choice = console.input("\n[bold green]输入章节号查看内容（回车取消）: [/bold green]").strip()
    if not choice:
        return
    try:
        ch_num = int(choice)
        text = state_manager.get_chapter_text(ch_num)
        if text:
            console.print(Panel(
                Markdown(text),
                title=f"📖 第 {ch_num} 章",
                border_style="green",
                padding=(1, 2)
            ))
        else:
            console.print(f"[bold red]第 {ch_num} 章不存在。[/bold red]")
    except ValueError:
        console.print("[bold red]请输入数字。[/bold red]")


def cmd_rollback(state_manager):
    """章节回退"""
    current = state_manager.state.get('current_chapter', 0)
    if current == 0:
        console.print("[bold red]当前还没有任何章节。[/bold red]")
        return

    console.print(f"[bold cyan]当前在第 {current} 章。[/bold cyan]")
    target = console.input("[bold cyan]回退到第几章？[/bold cyan] ")
    try:
        target = int(target)
        if 0 <= target < current:
            confirm = console.input(
                f"[bold yellow]⚠️ 将删除第 {target+1}~{current} 章，确认？[y/n]: [/bold yellow]"
            )
            if confirm.lower() != 'y':
                console.print("[dim]已取消。[/dim]")
                return
            success, msg = state_manager.rollback_to_chapter(target)
            icon = "✅" if success else "❌"
            console.print(f"[bold {'green' if success else 'red'}]{icon} {msg}[/bold {'green' if success else 'red'}]")
        else:
            console.print("[bold red]无效章节号。[/bold red]")
    except ValueError:
        console.print("[bold red]请输入数字。[/bold red]")


def cmd_extend_outline(router, state_manager, outline_manager):
    """续写下一卷大纲"""
    if not outline_manager.outline_data:
        console.print("[bold red]请先创建大纲。[/bold red]")
        return

    volumes = outline_manager.outline_data.get('volumes', [])
    if not volumes:
        console.print("[bold red]大纲为空。[/bold red]")
        return

    last_vol = volumes[-1]
    summary = {
        'total_volumes': len(volumes),
        'next_volume_num': last_vol['volume_number'] + 1,
        'last_volume_title': last_vol.get('volume_title', ''),
        'last_volume_conflict': last_vol.get('core_conflict', '')
    }

    console.print(f"\n[bold magenta]🧠 正在续写第 {summary['next_volume_num']} 卷大纲...[/bold magenta]")

    prompt = build_extend_prompt(
        book_title=outline_manager.outline_data.get('book_title', ''),
        synopsis=outline_manager.outline_data.get('synopsis', ''),
        current_volumes_summary=summary,
        protagonist_state=state_manager.state.get('character_current_state', ''),
        active_foreshadowing=state_manager.state.get('active_foreshadowing', [])
    )

    new_vol_str = spinner_task(
        f"🧠 正在续写第 {summary['next_volume_num']} 卷...",
        router.chat,
        task_type="planner",
        system_prompt=PLANNER_SYSTEM_PROMPT,
        user_prompt=prompt
    )

    if outline_manager.extend_outline(new_vol_str):
        console.print("[bold green]✅ 大纲续写成功！[/bold green]")
        outline_manager.print_outline_summary()
    else:
        console.print("[bold red]❌ 大纲续写失败，请重试。[/bold red]")


def cmd_export(state_manager, book_name):
    """导出全书"""
    console.print("\n[bold cyan]导出格式：1=TXT  2=Markdown[/bold cyan]")
    choice = console.input("[bold green]请选择: [/bold green]").strip()
    fmt = "md" if choice == "2" else "txt"
    path, msg = export_book(book_name, fmt)
    icon = "✅" if path else "❌"
    console.print(f"[bold {'green' if path else 'red'}]{icon} {msg}[/bold {'green' if path else 'red'}]")


def main():
    # 配置预检
    import os, sys
    if not os.path.exists("config.yaml"):
        console.print("[bold red]❌ 未找到 config.yaml 配置文件[/bold red]")
        console.print("\n解决方法：")
        console.print("  1. 双击运行 [bold]install.bat[/bold]（推荐，自动配置）")
        console.print("  2. 复制 config.example.yaml 为 config.yaml 并填入 API Key")
        console.print("  3. 运行 [bold]python demo_mode.py[/bold] 体验演示模式（无需 Key）")
        sys.exit(1)

    import yaml
    with open("config.yaml", 'r', encoding='utf-8') as f:
        _cfg = yaml.safe_load(f)
    if _cfg['llm_config']['api_key'].startswith("sk-your"):
        console.print("[bold red]⚠️  config.yaml 中的 API Key 还是占位符[/bold red]")
        console.print("请替换为真实 DeepSeek API Key：")
        console.print("https://platform.deepseek.com/api_keys")
        sys.exit(1)

    console.print(Panel(
        "[bold green]🚀 Omni-Writer AI[/bold green]\n"
        "[dim]多书管理 | 章节回退 | 大纲续写 | 全书导出 | 章节浏览[/dim]",
        border_style="blue"
    ))

    book_name = select_book()
    console.print(f"\n[bold cyan]📖 当前书籍：「{book_name}」[/bold cyan]")

    router, state_manager, kb, outline_manager = initialize_project(book_name)

    if kb.collection.count() == 0:
        console.print("[bold yellow]📦 素材库为空，正在注入测试素材...[/bold yellow]")
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

    last_sanitized_text = state_manager.get_latest_chapter_text() or ""

    while True:
        console.print()
        show_book_status(state_manager, outline_manager)
        console.print(
            "[bold green]"
            "n=下一章 | r=重绘 | l=浏览章节 | b=回退 | e=续写大纲 | x=导出 | s=切换 | h=帮助 | q=退出"
            "[/bold green]"
        )
        cmd = console.input("[bold green]> [/bold green]").strip().lower()

        if cmd == 'q':
            console.print("[bold cyan]👋 再见！[/bold cyan]")
            break

        elif cmd == 'h':
            show_help()
            continue

        elif cmd == 'l':
            cmd_browse_chapters(state_manager)
            continue

        elif cmd == 's':
            book_name = select_book()
            console.print(f"\n[bold cyan]📖 切换到：「{book_name}」[/bold cyan]")
            router, state_manager, kb, outline_manager = initialize_project(book_name)
            last_sanitized_text = state_manager.get_latest_chapter_text() or ""
            continue

        elif cmd == 'b':
            cmd_rollback(state_manager)
            last_sanitized_text = state_manager.get_latest_chapter_text() or ""
            continue

        elif cmd == 'e':
            cmd_extend_outline(router, state_manager, outline_manager)
            continue

        elif cmd == 'x':
            cmd_export(state_manager, book_name)
            continue

        elif cmd == 'r':
            if not last_sanitized_text:
                console.print("[bold red]暂无上一章文本可供重绘。[/bold red]")
                continue

            console.print(Markdown(last_sanitized_text))
            console.print(
                "\n[bold cyan]请从上面的文本中，复制你需要重写的【一个段落】：[/bold cyan] "
            )
            selected_text = console.input("> ")
            if selected_text not in last_sanitized_text:
                console.print("[bold red]未能匹配到该段落，请准确复制。[/bold red]")
                continue

            instruction = console.input(
                "[bold cyan]输入修改要求（可留空直接回车）：[/bold cyan] "
            )

            idx = last_sanitized_text.find(selected_text)
            text_before = last_sanitized_text[:idx]
            text_after = last_sanitized_text[idx + len(selected_text):]

            redrawn_text = spinner_task(
                "🖌️ 正在进行激进重绘...",
                router.chat,
                task_type="planner",
                system_prompt=REDRAWER_SYSTEM_PROMPT,
                user_prompt=build_redrawer_user_prompt(
                    text_before, selected_text, text_after, instruction
                )
            )
            console.print("\n[bold green]✨ 重绘结果：[/bold green]")
            console.print(Panel(Markdown(redrawn_text), border_style="green"))

            replace = console.input(
                "\n[bold yellow]是否用重绘结果替换原文？[y/n]: [/bold yellow]"
            )
            if replace.lower() == 'y':
                last_sanitized_text = text_before + redrawn_text + text_after
                current_ch = state_manager.state.get('current_chapter', 0)
                if current_ch > 0:
                    state_manager.save_chapter(current_ch, last_sanitized_text)
                console.print("[bold green]✅ 已替换并同步存档。[/bold green]")
            continue

        elif cmd == 'n':
            current_ch = state_manager.state['current_chapter'] + 1
            ch_info = outline_manager.get_next_chapter_info(current_ch)
            chapter_outline = ch_info['outline']
            scene_type = ch_info['scene_type']

            console.print(
                f"\n[bold cyan]📋 本章大纲节点：[/bold cyan] "
                f"{chapter_outline} (场景类型: {scene_type})"
            )

            negotiation_dialogue = ""
            if scene_type == "negotiation":
                console.print(
                    "\n[bold yellow]🎭 检测到智斗场景，启动多 Agent 谈判模拟器...[/bold yellow]"
                )
                characters = {
                    "主角": "隐藏实力，试图套出对方的底牌",
                    "反派长老": "咄咄逼人，怀疑主角身份，试图打压"
                }
                negotiation_dialogue = spinner_task(
                    "🎭 多 Agent 谈判模拟中...",
                    router.chat,
                    task_type="planner",
                    system_prompt=NEGOTIATOR_SYSTEM_PROMPT,
                    user_prompt=build_negotiator_user_prompt(
                        chapter_outline, characters
                    )
                )
                console.print(
                    f"[bold yellow]谈判记录生成完毕：\n{negotiation_dialogue}[/bold yellow]"
                )

            context = {
                "current_chapter": current_ch,
                "chapter_outline": chapter_outline,
                "character_state": state_manager.state['character_current_state'],
                "active_foreshadowing": state_manager.state['active_foreshadowing'],
                "negotiation_dialogue": negotiation_dialogue
            }

            console.print("\n[bold cyan]🔍 正在从知识库检索相关素材...[/bold cyan]")
            retrieved_materials = kb.retrieve_materials(
                context['chapter_outline'], top_k=2
            )
            context['retrieved_materials'] = retrieved_materials

            raw_output = spinner_task(
                "📝 正在生成正文初稿...",
                router.chat,
                task_type="writer",
                system_prompt=WRITER_SYSTEM_PROMPT,
                user_prompt=build_writer_user_prompt(context)
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

            radar_response = spinner_task(
                "📡 原创性雷达扫描中...",
                router.chat,
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
                    fixed_text = radar_data.get("fixed_text", raw_text_part)

                    score_color = "green" if score >= 80 else "red"
                    issue_text = (
                        f"得分: [{score_color}]{score}[/{score_color}]\n"
                        f"发现问题:\n- " + "\n- ".join(issues)
                        if issues else "无"
                    )
                    console.print(Panel(
                        issue_text,
                        title="🚨 原创性雷达扫描报告",
                        expand=False,
                        border_style=score_color
                    ))

                    if score < 80 or issues:
                        console.print(
                            "[bold yellow]🛠️ 检测到毒点/套路，已自动触发重写修复...[/bold yellow]"
                        )
                        checked_text = fixed_text
                except Exception as e:
                    console.print(
                        f"[bold red]雷达数据解析失败: {e}，使用原文本继续。[/bold red]"
                    )
            else:
                console.print(
                    "[bold red]未能提取雷达 JSON，使用原文本继续。[/bold red]"
                )

            sanitized_text = spinner_task(
                "🛡️ 正在进行 AI 痕迹脱敏与人类化处理...",
                router.chat,
                task_type="sanitizer",
                system_prompt=SANITIZER_SYSTEM_PROMPT,
                user_prompt=build_sanitizer_user_prompt(checked_text)
            )

            final_output = (
                f"{sanitized_text}\n\n<state_update_json>\n{json_part}\n</state_update_json>"
            )
            console.print("\n[bold yellow]🧠 正在更新长程记忆状态...[/bold yellow]")
            state_manager.update_state_from_chapter(final_output)
            state_manager.save_chapter(current_ch, sanitized_text)
            state_manager.create_snapshot()

            console.print(Panel(
                Markdown(sanitized_text),
                title=f"📖 第 {current_ch} 章（已脱敏+已自检）",
                border_style="green",
                padding=(1, 2)
            ))

            last_sanitized_text = sanitized_text

        else:
            console.print(f"[dim]未知命令 '{cmd}'，输入 h 查看帮助。[/dim]")


if __name__ == "__main__":
    main()
