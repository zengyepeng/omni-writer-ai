"""
Omni-Writer AI - 大纲管理器
负责生成整书大纲、持久化存储、按章节序号逐章调度。
"""
import json
import os


class OutlineManager:
    def __init__(self, outline_file="data/outline.json"):
        self.outline_file = outline_file
        self.outline_data = self.load_outline()

    def load_outline(self):
        if os.path.exists(self.outline_file):
            with open(self.outline_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def save_outline(self, outline_json_str):
        try:
            clean_str = outline_json_str.replace("```json", "").replace("```", "").strip()
            self.outline_data = json.loads(clean_str)
            os.makedirs(os.path.dirname(self.outline_file), exist_ok=True)
            with open(self.outline_file, 'w', encoding='utf-8') as f:
                json.dump(self.outline_data, f, ensure_ascii=False, indent=4)
            print(f"[OutlineManager] 大纲已生成并保存：{self.outline_data.get('book_title', '未知书名')}")
            return True
        except Exception as e:
            print(f"[OutlineManager] 大纲解析失败: {e}")
            return False

    def get_next_chapter_info(self, current_chapter_num):
        """根据当前章节号，推算下一章的大纲节点和场景类型"""
        if not self.outline_data:
            return {"outline": "大纲为空，自由发挥。", "scene_type": "normal"}

        chapter_index = current_chapter_num - 1
        cumulative_chapters = 0

        for volume in self.outline_data.get('volumes', []):
            vol_chapters = volume.get('chapter_outlines', [])
            if cumulative_chapters + len(vol_chapters) > chapter_index:
                idx_in_vol = chapter_index - cumulative_chapters
                ch_info = vol_chapters[idx_in_vol]
                # 兼容旧版纯字符串大纲和新版字典大纲
                if isinstance(ch_info, str):
                    return {"outline": ch_info, "scene_type": "normal"}
                return {
                    "outline": ch_info.get("outline", ""),
                    "scene_type": ch_info.get("scene_type", "normal")
                }
            cumulative_chapters += len(vol_chapters)

        return {"outline": "大纲已规划完毕，请根据前文伏笔自由推进剧情。", "scene_type": "normal"}

    def print_outline_summary(self):
        if not self.outline_data:
            print("暂无大纲。")
            return

        print(f"\n📚 书名：{self.outline_data.get('book_title')}")
        print(f"📝 简介：{self.outline_data.get('synopsis')}")
        cumulative_chapters = 0
        for vol in self.outline_data.get('volumes', []):
            vol_chapters = vol.get('chapter_outlines', [])
            print(f"\n  卷{vol['volume_number']}：{vol['volume_title']} (冲突: {vol['core_conflict']})")
            for i, ch in enumerate(vol_chapters):
                ch_text = ch if isinstance(ch, str) else ch.get('outline', '')
                print(f"    - 第{cumulative_chapters + i + 1}章: {ch_text}")
            cumulative_chapters += len(vol_chapters)
