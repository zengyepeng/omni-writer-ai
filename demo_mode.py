"""
Omni-Writer AI - Demo 体验模式
无需 API Key，用模拟数据体验完整 Web 界面。
适合首次安装后先看看长什么样。
"""
import gradio as gr

DEMO_CHAPTER = """夜色像一块被墨汁浸透的布，压在临江城的上空。

陈默站在天台上，指尖悬在半空。眼前那道半透明的光幕还在闪——

【天道系统·警告：检测到未授权访问】

他没由来的想笑。修仙三千年，雷劫都劈不死他，结果穿越到这个世界，被一串代码拦在门外。

"未授权？"他低声说，"我修的仙，就是最大的授权。"

指尖落下，光幕碎成星点。远处，整座城市的霓虹突然同时闪烁了一下。

有什么东西，醒了。"""

DEMO_OUTLINE = """📚 书名：《代码修仙：我黑进了天道系统》
📝 简介：渡劫失败的修仙者穿越赛博都市，发现所谓天道竟是一套可以被入侵的系统
👤 主角：陈默——三千年道行的落魄仙尊，如今是最顶级的黑客
📊 规划：3 卷 / 45 章 | 含 2 个智斗场景

✅ 大纲生成完毕，可以开始生成正文了！
（这是 Demo 演示数据，配置 API Key 后即可真实生成）"""

DEMO_LOG = """📋 本章大纲节点：第 1 章 - 陈默穿越醒来，发现天道是系统 (场景: normal)
🔍 正在从知识库检索相关素材...
📝 正在生成正文初稿...
📡 启动原创性雷达，扫描毒点与套路...
🚨 雷达扫描得分: 91 | 发现问题: 0处
🛡️ 正在进行 AI 痕迹脱敏与人类化处理...
✅ 第 1 章生成完毕！雷达得分: 91分

（这是 Demo 演示日志，配置 API Key 后即可真实生成）"""


def fake_generate():
    """模拟章节生成"""
    yield DEMO_LOG, ""
    yield DEMO_LOG, DEMO_CHAPTER


def fake_init(inspiration):
    if not inspiration:
        return "请输入灵感试试（Demo 模式随便填）", gr.update(visible=False)
    return DEMO_OUTLINE, gr.update(visible=True)


with gr.Blocks(title="Omni-Writer AI - Demo", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🚀 Omni-Writer AI — Demo 体验模式
    > ⚠️ 当前为演示模式，所有数据为模拟内容。配置 API Key 后可真实生成。
    """)

    with gr.Tab("✨ 创世引擎"):
        inspiration_input = gr.Textbox(
            label="💡 一句话灵感",
            placeholder="例如：修仙+赛博朋克+黑客流，主角靠代码入侵天道系统",
            lines=2
        )
        init_btn = gr.Button("⚡ 开始创世", variant="primary", size="lg")
        outline_output = gr.Textbox(label="📋 大纲概览", lines=12, interactive=False)
        init_btn.click(fake_init, inputs=[inspiration_input], outputs=[outline_output, gr.Button(visible=False)])

    with gr.Tab("⚙️ 创作流水线"):
        with gr.Row():
            with gr.Column(scale=1):
                gen_btn = gr.Button("⚙️ 生成下一章（演示）", variant="primary", size="lg")
                gr.Markdown("---")
                gr.Markdown("### 🖌️ 局部重绘\n（Demo 模式不可用）")
                gr.Markdown("### ⏪ 章节回退\n（Demo 模式不可用）")
            with gr.Column(scale=2):
                log_output = gr.Textbox(label="📟 工业流水线日志", lines=8, interactive=False)
                chapter_output = gr.Textbox(label="📄 本章正文", lines=22, interactive=True)
        gen_btn.click(fake_generate, outputs=[log_output, chapter_output])

    gr.Markdown("""
    ---
    ### 🔑 如何解锁完整功能？
    1. 打开 https://platform.deepseek.com/api_keys 免费注册（送 500 万 tokens）
    2. 复制你的 API Key
    3. 双击运行 `install.bat` 重新配置，或手动编辑 `config.yaml`
    4. 双击 `start.bat` 选择模式 1 即可开始真实创作
    """)

if __name__ == "__main__":
    print("=" * 50)
    print("  Omni-Writer AI - Demo 体验模式")
    print("  浏览器打开: http://127.0.0.1:7861")
    print("=" * 50)
    demo.launch(server_name="127.0.0.1", server_port=7861)
