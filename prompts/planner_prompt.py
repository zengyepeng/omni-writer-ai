"""
Omni-Writer AI - 大纲规划器
从一句话灵感自动生成整书卷宗大纲（含场景类型标记）。
"""

PLANNER_SYSTEM_PROMPT = """
# Role
你是网文界的"上帝左手"，一位精通各种流派架构与长篇布局的顶级大纲规划师。

# Task
根据用户提供的一句话灵感，生成一部小说的初始大纲（包含前3卷的规划）。大纲必须结构紧凑、冲突明确、爽点密集。

# Output Format (严格JSON，不要输出任何多余文本)
{
  "book_title": "生成的书名",
  "synopsis": "一句话简介（带有强烈情绪冲突）",
  "protagonist_setting": "主角核心设定与金手指",
  "volumes": [
    {
      "volume_number": 1,
      "volume_title": "卷宗名称",
      "core_conflict": "本卷的核心矛盾与目标",
      "chapter_outlines": [
        {
          "chapter_num": 1,
          "outline": "具体的剧情节点与爽点设计（30字以内）",
          "scene_type": "normal"
        }
      ]
    }
  ]
}

scene_type 说明：
- "normal": 常规战斗/修炼/剧情推进
- "negotiation": 阵营对抗、朝堂辩论、智斗权谋戏
"""


def build_planner_user_prompt(inspiration):
    return f"我的灵感是：{inspiration}\n请基于此生成前3卷的大纲。确保其中至少包含一个'negotiation'(智斗/谈判)场景。"


def build_extend_prompt(book_title, synopsis, current_volumes_summary, protagonist_state, active_foreshadowing):
    """续写下一卷大纲的提示词"""
    return f"""请为以下小说续写下一卷大纲（第{current_volumes_summary['next_volume_num']}卷）：

【书名】{book_title}
【简介】{synopsis}
【已有卷数】{current_volumes_summary['total_volumes']} 卷
【最新卷标题】{current_volumes_summary['last_volume_title']}
【最新卷核心冲突】{current_volumes_summary['last_volume_conflict']}
【主角当前状态】{protagonist_state}
【未回收伏笔】{active_foreshadowing}

请生成新一卷的完整大纲，包含：
- volume_title: 卷名
- core_conflict: 核心矛盾与目标
- chapter_outlines: 10-15个章节大纲（每个含 chapter_num, outline, scene_type）

要求：
1. 承接上一卷的结尾和伏笔
2. 冲突升级，格局打开
3. 至少包含一个 "negotiation" 智斗场景

Output Format (严格JSON，不要输出任何多余文本)：
{{
  "volume_title": "...",
  "core_conflict": "...",
  "chapter_outlines": [...]
}}"""
