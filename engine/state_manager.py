"""
Omni-Writer AI - 千万字状态机管理器
负责维护短/中/长期记忆、伏笔回收、主角状态追踪、章节落盘与回退。
支持多本书隔离存储：data/books/{book_name}/
"""
import json
import os
import re
import shutil
import logging

logger = logging.getLogger(__name__)


def _get_book_dir(book_name="default"):
    """获取书籍数据目录"""
    return os.path.join("data", "books", book_name)


class StateManager:
    def __init__(self, book_name="default"):
        self.book_name = book_name
        self.book_dir = _get_book_dir(book_name)
        self.state_file = os.path.join(self.book_dir, "global_state.json")
        self.chapters_dir = os.path.join(self.book_dir, "chapters")
        self.snapshots_dir = os.path.join(self.book_dir, "snapshots")
        self.state = self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "current_chapter": 0,
            "short_term_memory": {},
            "mid_term_memory": "",
            "long_term_memory": {"foreshadowing": []},
            "character_current_state": "初始状态",
            "active_foreshadowing": []
        }

    def save_state(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=4)

    @staticmethod
    def extract_state_json(raw_text):
        """从混有正文文本的输出中提取 <state_update_json> 内的 JSON 块"""
        match = re.search(
            r'<state_update_json>(.*?)</state_update_json>',
            raw_text, re.DOTALL
        )
        if match:
            json_str = match.group(1).strip()
            json_str = json_str.replace("```json", "").replace("```", "").strip()
            return json_str
        return None

    @staticmethod
    def extract_chapter_text(raw_text):
        """从混有状态 JSON 的输出中提取纯正文"""
        match = re.search(
            r'<state_update_json>(.*?)</state_update_json>',
            raw_text, re.DOTALL
        )
        if match:
            return raw_text[:match.start()].strip()
        return raw_text.strip()

    def update_state_from_chapter(self, raw_text):
        """解析新章节的 JSON，更新状态机"""
        json_str = self.extract_state_json(raw_text)
        if not json_str:
            logger.warning("[StateManager] 未检测到 <state_update_json>，状态未更新")
            return False

        try:
            state_update = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"[StateManager] JSON 解析失败: {e}")
            return False

        self.state['current_chapter'] = state_update.get(
            'chapter_number', self.state['current_chapter'] + 1
        )

        if 'long_term_memory_update' in state_update:
            new_fs = state_update['long_term_memory_update'].get(
                'new_foreshadowing', []
            )
            if new_fs:
                self.state['long_term_memory']['foreshadowing'].extend(new_fs)
                self.state['active_foreshadowing'].extend(new_fs)

        if 'resolved_foreshadowing' in state_update:
            resolved = state_update['resolved_foreshadowing']
            self.state['active_foreshadowing'] = [
                fs for fs in self.state['active_foreshadowing']
                if fs not in resolved
            ]

        if 'character_state_change' in state_update:
            self.state['character_current_state'] = \
                state_update['character_state_change']

        self.save_state()
        logger.info("[StateManager] 状态机已更新并持久化")
        return True

    # ========== 章节存档与回退 ==========

    def save_chapter(self, chapter_num, text):
        """将生成的章节正文存档"""
        os.makedirs(self.chapters_dir, exist_ok=True)
        filepath = os.path.join(
            self.chapters_dir, f"chapter_{chapter_num:04d}.txt"
        )
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        logger.info(f"[StateManager] 章节已存档: {filepath}")
        return filepath

    def get_latest_chapter_text(self):
        """读取最近一章的正文"""
        if not os.path.exists(self.chapters_dir):
            return None
        files = sorted(
            f for f in os.listdir(self.chapters_dir) if f.endswith('.txt')
        )
        if not files:
            return None
        with open(os.path.join(self.chapters_dir, files[-1]), 'r', encoding='utf-8') as f:
            return f.read()

    def get_chapter_text(self, chapter_num):
        """读取指定章节的正文"""
        filepath = os.path.join(
            self.chapters_dir, f"chapter_{chapter_num:04d}.txt"
        )
        if not os.path.exists(filepath):
            return None
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    def create_snapshot(self):
        """为当前状态创建快照（供回退使用）"""
        current_ch = self.state.get('current_chapter', 0)
        if current_ch == 0:
            return None

        os.makedirs(self.snapshots_dir, exist_ok=True)
        snapshot_file = os.path.join(
            self.snapshots_dir, f"snapshot_ch{current_ch:04d}.json"
        )
        snapshot = {
            "chapter": current_ch,
            "state": self.state.copy()
        }
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=4)
        logger.info(f"[StateManager] 已创建快照: chapter {current_ch}")
        return snapshot_file

    def rollback_to_chapter(self, target_chapter):
        """回退到指定章节：恢复快照，删除多余章节"""
        if target_chapter < 0:
            return False, "目标章节不能小于 0"

        # 找最近的不超过 target 的快照
        snapshot_file = os.path.join(
            self.snapshots_dir, f"snapshot_ch{target_chapter:04d}.json"
        )

        if os.path.exists(snapshot_file):
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                snapshot = json.load(f)
            self.state = snapshot['state']
        else:
            # 没有快照就手动回退
            self.state['current_chapter'] = target_chapter
            # 清除目标章节之后的伏笔（简化处理）
            self.state['active_foreshadowing'] = [
                fs for fs in self.state['active_foreshadowing']
                if not fs.startswith(f"第{target_chapter + 1}章后")
            ]

        # 删除目标章节之后的章节文件
        if os.path.exists(self.chapters_dir):
            for f in os.listdir(self.chapters_dir):
                if f.startswith("chapter_") and f.endswith(".txt"):
                    ch_num = int(f.replace("chapter_", "").replace(".txt", ""))
                    if ch_num > target_chapter:
                        os.remove(os.path.join(self.chapters_dir, f))
                        logger.info(f"[StateManager] 已删除章节: {f}")

        self.save_state()
        logger.info(f"[StateManager] 已回退到第 {target_chapter} 章")
        return True, f"已回退到第 {target_chapter} 章"

    # ========== 旧数据迁移 ==========

    @staticmethod
    def migrate_legacy_data():
        """将旧版 data/ 下的数据迁移到 data/books/default/"""
        old_files = [
            ("data/global_state.json", "data/books/default/global_state.json"),
            ("data/outline.json", "data/books/default/outline.json"),
        ]
        old_chapters = "data/chapters"
        new_chapters = "data/books/default/chapters"

        migrated = False

        for old_path, new_path in old_files:
            if os.path.exists(old_path) and not os.path.exists(new_path):
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                shutil.copy2(old_path, new_path)
                logger.info(f"[StateManager] 迁移: {old_path} -> {new_path}")
                migrated = True

        if os.path.exists(old_chapters) and not os.path.exists(new_chapters):
            shutil.copytree(old_chapters, new_chapters)
            logger.info(f"[StateManager] 迁移: {old_chapters} -> {new_chapters}")
            migrated = True

        return migrated

    @staticmethod
    def list_books():
        """列出所有书籍"""
        books_dir = "data/books"
        if not os.path.exists(books_dir):
            return []
        return [
            d for d in os.listdir(books_dir)
            if os.path.isdir(os.path.join(books_dir, d))
        ]
