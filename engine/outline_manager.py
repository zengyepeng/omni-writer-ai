"""
Omni-Writer AI - 大纲管理器
负责生成整书大纲、持久化存储、按章节序号逐章调度、续写下一卷。
支持多本书隔离存储。
"""
import json
import os
import logging

logger = logging.getLogger(__name__)


class OutlineManager:
    def __init__(self, book_name="default"):
        self.book_name = book_name
        self.book_dir = os.path.join("data", "books", book_name)
        self.outline_file = os.path.join(self.book_dir, "outline.json")
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
            logger.info(f"[OutlineManager] 大纲已生成并保存：{self.outline_data.get('book_title', '未知书名')}")
            return True
        except Exception as e:
            logger.error(f"[OutlineManager] 大纲解析失败: {e}")
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
                if isinstance(ch_info, str):
                    return {"outline": ch_info, "scene_type": "normal"}
                return {
                    "outline": ch_info.get("outline", ""),
                    "scene_type": ch_info.get("scene_type", "normal")
                }
            cumulative_chapters += len(vol_chapters)

        return {"outline": "大纲已规划完毕，请根据前文伏笔自由推进剧情。", "scene_type": "normal"}

    def get_total_chapters(self):
        """获取已规划的总章节数"""
        if not self.outline_data:
            return 0
        total = 0
        for vol in self.outline_data.get('volumes', []):
            total += len(vol.get('chapter_outlines', []))
        return total

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

    # ========== 大纲续写 ==========

    def extend_outline(self, new_volume_json_str):
        """将新生成的卷追加到大纲末尾"""
        try:
            clean_str = new_volume_json_str.replace("```json", "").replace("```", "").strip()
            new_volume = json.loads(clean_str)

            if not self.outline_data:
                logger.error("[OutlineManager] 无基础大纲，无法续写")
                return False

            volumes = self.outline_data.get('volumes', [])
            if not volumes:
                logger.error("[OutlineManager] 基础大纲无卷，无法续写")
                return False

            # 确保 volume_number 正确
            new_volume['volume_number'] = volumes[-1]['volume_number'] + 1
            volumes.append(new_volume)

            with open(self.outline_file, 'w', encoding='utf-8') as f:
                json.dump(self.outline_data, f, ensure_ascii=False, indent=4)

            logger.info(f"[OutlineManager] 已续写第 {new_volume['volume_number']} 卷：{new_volume.get('volume_title')}")
            return True
        except Exception as e:
            logger.error(f"[OutlineManager] 大纲续写失败: {e}")
            return False
