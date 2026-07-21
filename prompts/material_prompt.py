"""
Omni-Writer AI - 素材结构化与打标入库器
"""

MATERIAL_SYSTEM_PROMPT = """
你是一个素材整理大师。请将用户提供的原始素材文本，提炼为一段结构清晰、带有具体设定的说明文字，方便小说写作时参考。
不要超过 200 字，保留最核心的设定、画面感或知识点。
"""


def build_material_user_prompt(raw_text):
    return f"请整理以下素材：\n\n{raw_text}"
