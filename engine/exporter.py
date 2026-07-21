"""
Omni-Writer AI - 全书导出器
将所有章节合并导出为单个 TXT 或 Markdown 文件。
"""
import os
import logging

logger = logging.getLogger(__name__)


def export_book(book_name="default", output_format="txt"):
    """
    导出全书为单个文件
    output_format: "txt" 或 "md"
    """
    book_dir = os.path.join("data", "books", book_name)
    chapters_dir = os.path.join(book_dir, "chapters")
    outline_file = os.path.join(book_dir, "outline.json")

    if not os.path.exists(chapters_dir):
        return None, "无章节可导出"

    # 读取大纲获取书名
    book_title = book_name
    if os.path.exists(outline_file):
        import json
        with open(outline_file, 'r', encoding='utf-8') as f:
            outline = json.load(f)
        book_title = outline.get('book_title', book_name)

    # 按顺序读取所有章节
    chapter_files = sorted(
        f for f in os.listdir(chapters_dir) if f.endswith('.txt')
    )

    if not chapter_files:
        return None, "无章节可导出"

    # 合并内容
    if output_format == "md":
        content = f"# {book_title}\n\n"
        for i, fname in enumerate(chapter_files, 1):
            ch_num = int(fname.replace("chapter_", "").replace(".txt", ""))
            with open(os.path.join(chapters_dir, fname), 'r', encoding='utf-8') as f:
                text = f.read()
            content += f"## 第 {ch_num} 章\n\n{text}\n\n"
        ext = "md"
    else:
        content = f"{book_title}\n\n"
        for fname in chapter_files:
            ch_num = int(fname.replace("chapter_", "").replace(".txt", ""))
            with open(os.path.join(chapters_dir, fname), 'r', encoding='utf-8') as f:
                text = f.read()
            content += f"第 {ch_num} 章\n\n{text}\n\n"
        ext = "txt"

    # 保存导出文件
    export_dir = os.path.join(book_dir, "exports")
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, f"{book_title}.{ext}")

    with open(export_path, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info(f"[Exporter] 已导出: {export_path} ({len(chapter_files)} 章)")
    return export_path, f"已导出 {len(chapter_files)} 章到 {export_path}"
