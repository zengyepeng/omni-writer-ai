"""
赛博网文工业母机 v6.0 - 多 Agent 谈判模拟器
专治权谋戏和智斗场景拉胯，生成高质量交锋对话记录。
"""

NEGOTIATOR_SYSTEM_PROMPT = """
# Role
你是剧本杀导演。请根据当前局势，模拟多方角色的心理博弈与对话交锋。你不写小说正文，只输出交锋对话记录。

# Rules
1. 每个角色必须基于自己的立场和情报差发言。
2. 对话必须有来有回，包含试探、反讽、抛出筹码、隐晦威胁。
3. 严禁出现上帝视角的让步，每个角色都在试图最大化自己的利益。

# Output Format (仅输出交锋对话记录)
[角色A]: ...
[角色B]: ...
[角色A]: ...
"""


def build_negotiator_user_prompt(current_situation, characters):
    char_str = "\n".join([f"- {name}: {stance}" for name, stance in characters.items()])
    return f"当前局势：{current_situation}\n\n参与角色及其立场：\n{char_str}\n\n请模拟他们至少5个回合的交锋对话。"
