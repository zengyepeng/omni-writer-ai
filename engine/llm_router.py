"""
Omni-Writer AI - 多模型混合路由调度器
根据任务类型自动切换模型，实现极致性价比。
"""
import yaml
from openai import OpenAI


class LLMRouter:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.client = OpenAI(
            api_key=self.config['llm_config']['api_key'],
            base_url=self.config['llm_config']['base_url']
        )
        self.router_config = self.config['model_router']

    def chat(self, task_type, system_prompt, user_prompt):
        """统一调用接口：根据任务类型自动选择模型和参数"""
        if task_type not in self.router_config:
            raise ValueError(f"未知的任务类型: {task_type}")

        task_config = self.router_config[task_type]
        model = task_config['model']
        temp = task_config.get('temperature', 0.7)
        print(f"\n[Router] 调用模型: {model} | 任务: {task_type} | Temp: {temp}")

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temp,
            max_tokens=4096
        )
        return response.choices[0].message.content
