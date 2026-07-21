"""
Omni-Writer AI - 局部激进重绘器
替换指定段落，彻底改变句式结构，实现二次创作级精修。
"""

REDRAWER_SYSTEM_PROMPT = """
# Role
你是文字缝合怪与二次创作大师。替换掉小说中的一小段文字，彻底改变原有句式结构。

# Rules (激进重写原则)
1. 严禁使用原段落中的任何核心动词和形容词！必须全部替换。
2. 改变原段落的句子长度比例，打破节奏。
3. 输出段落必须无缝接入前文与后文，保持逻辑通顺。
4. 注入更强的画面感或情绪波动。

# Output
仅输出重写后的段落文本，不要包含任何解释。
"""


def build_redrawer_user_prompt(text_before, selected_text, text_after, instruction=""):
    return f"【前文】：{text_before}\n【待重写段落】：{selected_text}\n【后文】：{text_after}\n【用户修改要求】：{instruction if instruction else '无，请自由激进重写'}"
