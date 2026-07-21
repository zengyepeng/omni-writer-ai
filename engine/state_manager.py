"""
Omni-Writer AI - 千万字状态机管理器
负责读取、更新、压缩记忆，防止长篇小说人物状态崩溃。
"""
import json
import os


class StateManager:
    def __init__(self, state_file="data/global_state.json"):
        self.state_file = state_file
        self.state = self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        # 初始化空白状态
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

    def update_state_from_chapter(self, state_update_json_str):
        """解析大模型输出的 state_update_json 并更新状态库"""
        try:
            # 清理可能存在的 markdown 标记
            clean_str = state_update_json_str.replace("```json", "").replace("```", "").strip()
            update_data = json.loads(clean_str)

            # 更新章节号
            self.state['current_chapter'] += 1

            # 更新短期记忆（保留最近3章，这里简化处理）
            self.state['short_term_memory'] = {
                "chapter_summary": update_data.get("chapter_summary", ""),
                "location": update_data.get("location_update", ""),
                "power": update_data.get("power_update", "")
            }

            # 更新伏笔
            new_fs = update_data.get("new_foreshadowing", [])
            if new_fs:
                self.state['active_foreshadowing'].extend(new_fs)

            resolved_fs = update_data.get("resolved_foreshadowing", [])
            if resolved_fs:
                self.state['active_foreshadowing'] = [
                    fs for fs in self.state['active_foreshadowing']
                    if fs not in resolved_fs
                ]

            self.save_state()
            print(f"[StateManager] 状态已更新，当前章节: {self.state['current_chapter']}")
            return True
        except Exception as e:
            print(f"[StateManager] 状态解析失败: {e}")
            return False
