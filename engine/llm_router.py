"""
Omni-Writer AI - 多模型混合路由调度器
根据任务类型自动切换模型，支持环境变量覆盖配置，内置指数退避重试。
"""
import os
import time
import yaml
from openai import OpenAI


def retry_on_failure(max_retries=3, base_delay=1.0):
    """指数退避重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"[Router] 请求失败 ({e})，{delay:.1f}s 后重试 "
                              f"({attempt + 1}/{max_retries})...")
                        time.sleep(delay)
                    else:
                        print(f"[Router] 重试 {max_retries} 次后仍失败: {e}")
            raise last_exception
        return wrapper
    return decorator


class LLMRouter:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        llm_cfg = self.config['llm_config']

        # 环境变量优先于配置文件
        api_key = os.environ.get('OMNI_WRITER_API_KEY') or llm_cfg['api_key']
        base_url = os.environ.get('OMNI_WRITER_BASE_URL') or llm_cfg['base_url']

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.router_config = self.config['model_router']

    @retry_on_failure(max_retries=3, base_delay=1.0)
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
