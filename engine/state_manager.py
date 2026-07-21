"""
Omni-Writer AI - 千万字状态机管理器
负责维护短/中/长期记忆、伏笔回收、主角状态追踪与章节落盘。
"""
import json
import os
import re


class StateManager:
    def __init__(self, state_file="data/global_state.json"):
        self.state_file = state_file
        self.chapters_dir = "data/chapters"
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
            # 清理可能的 markdown 包裹
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
            print("[StateManager] 未检测到 <state_update_json>，状态未更新")
            return False

        try:
            state_update = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"[StateManager] JSON 解析失败: {e}")
            return False

        # 更新章节号
        self.state['current_chapter'] = state_update.get(
            'chapter_number', self.state['current_chapter'] + 1
        )

        # 更新长期伏笔池
        if 'long_term_memory_update' in state_update:
            new_fs = state_update['long_term_memory_update'].get(
                'new_foreshadowing', []
            )
            if new_fs:
                self.state['long_term_memory']['foreshadowing'].extend(new_fs)
                self.state['active_foreshadowing'].extend(new_fs)

        # 回收伏笔
        if 'resolved_foreshadowing' in state_update:
            resolved = state_update['resolved_foreshadowing']
            self.state['active_foreshadowing'] = [
                fs for fs in self.state['active_foreshadowing']
                if fs not in resolved
            ]

        # 更新主角状态
        if 'character_state_change' in state_update:
            self.state['character_current_state'] = \
                state_update['character_state_change']

        self.save_state()
        print("[StateManager] 状态机已更新并持久化")
        return True

    def save_chapter(self, chapter_num, text):
        """将生成的章节正文存档到 data/chapters/"""
        os.makedirs(self.chapters_dir, exist_ok=True)
        filepath = os.path.join(
            self.chapters_dir, f"chapter_{chapter_num:04d}.txt"
        )
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"[StateManager] 章节已存档: {filepath}")
        return filepath

    def get_latest_chapter_text(self):
        """读取最近一章的正文（供重绘使用）"""
        if not os.path.exists(self.chapters_dir):
            return None
        files = sorted(
            f for f in os.listdir(self.chapters_dir) if f.endswith('.txt')
        )
        if not files:
            return None
        with open(os.path.join(self.chapters_dir, files[-1]), 'r', encoding='utf-8') as f:
            return f.read()
