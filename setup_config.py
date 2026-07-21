#!/usr/bin/env python3
"""
Omni-Writer AI - 配置生成器
根据用户输入的 API Key 自动生成 config.yaml
支持 DeepSeek 一家搞定（LLM + Embedding 用同一 Key）
"""
import sys
import os


def generate_config(api_key):
    """生成简化配置：DeepSeek 一个 Key 走天下"""
    config = f"""# Omni-Writer AI - 全局配置
# 由安装向导自动生成，可手动修改

llm_config:
  # 主 LLM（DeepSeek）
  api_key: "{api_key}"
  base_url: "https://api.deepseek.com/v1"

  # Embedding（DeepSeek 兼容接口）
  embedding_api_key: "{api_key}"
  embedding_base_url: "https://api.deepseek.com/v1"
  embedding_model: "deepseek-embedding"

model_router:
  planner:
    model: "deepseek-chat"
    temperature: 0.7
  writer:
    model: "deepseek-chat"
    temperature: 0.85
  sanitizer:
    model: "deepseek-chat"
    temperature: 0.6
"""
    with open("config.yaml", "w", encoding="utf-8") as f:
        f.write(config)
    print("✅ config.yaml 已生成")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python setup_config.py <api_key>")
        sys.exit(1)
    generate_config(sys.argv[1])
