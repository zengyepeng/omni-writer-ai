"""
Omni-Writer AI - 多源素材库与 RAG 检索引擎
使用 ChromaDB 实现本地向量存储与语义检索，打破 AI 信息茧房。
Embedding 优先使用外部 API，不可用时自动降级为 ChromaDB 内置本地模型。
"""
import chromadb
from openai import OpenAI
import yaml
import hashlib
import time
import logging

logger = logging.getLogger(__name__)


def _retry_embedding(max_retries=3, base_delay=1.0):
    """Embedding 请求重试装饰器"""
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
                        logger.warning(
                            f"[KnowledgeBase] Embedding 请求失败，{delay:.1f}s 后重试 "
                            f"({attempt + 1}/{max_retries})..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"[KnowledgeBase] Embedding 重试 {max_retries} 次后仍失败: {e}")
            raise last_exception
        return wrapper
    return decorator


class KnowledgeBase:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self._use_external_embedding = True
        self._init_embedding_client()

        # 初始化 ChromaDB 本地持久化客户端
        self.db_path = "data/chroma_db"
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.client.get_or_create_collection(
            name="novel_materials"
        )

        logger.info(f"[KnowledgeBase] 初始化完成，当前素材库共有 {self.collection.count()} 条素材。"
                    f"Embedding 模式: {'外部 API' if self._use_external_embedding else '本地内置'}")

    def _init_embedding_client(self):
        """初始化 Embedding 客户端，失败则降级为本地模式"""
        try:
            self.embedding_client = OpenAI(
                api_key=self.config['llm_config']['embedding_api_key'],
                base_url=self.config['llm_config']['embedding_base_url']
            )
            # 测试一次调用
            self._get_embedding("测试")
        except Exception as e:
            logger.warning(f"[KnowledgeBase] 外部 Embedding 不可用 ({e})，降级为本地内置模型")
            self._use_external_embedding = False

    @_retry_embedding(max_retries=3, base_delay=1.0)
    def _get_embedding(self, text):
        """调用外部 API 获取文本向量"""
        response = self.embedding_client.embeddings.create(
            input=text,
            model=self.config['llm_config']['embedding_model']
        )
        return response.data[0].embedding

    @staticmethod
    def _make_doc_id(text):
        """使用 SHA256 哈希作为确定性文档 ID"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]

    def add_material(self, text, source="未知来源"):
        """将一段素材文本入库（upsert，重复插入安全）"""
        if not text.strip():
            return

        doc_id = self._make_doc_id(text)

        if self._use_external_embedding:
            embedding = self._get_embedding(text)
            self.collection.upsert(
                embeddings=[embedding],
                documents=[text],
                metadatas=[{"source": source}],
                ids=[doc_id]
            )
        else:
            # ChromaDB 内置 embedding，直接传文本
            self.collection.upsert(
                documents=[text],
                metadatas=[{"source": source}],
                ids=[doc_id]
            )
        logger.info(f"[KnowledgeBase] 成功添加素材: {text[:30]}...")

    def retrieve_materials(self, query, top_k=3):
        """根据查询文本，检索最相关的 top_k 条素材"""
        if self.collection.count() == 0:
            return "素材库为空。"

        if self._use_external_embedding:
            query_embedding = self._get_embedding(query)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
        else:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )

        retrieved_docs = results.get('documents', [[]])[0]
        if not retrieved_docs:
            return "未检索到相关素材。"

        formatted_results = []
        for i, doc in enumerate(retrieved_docs):
            formatted_results.append(f"[参考素材{i+1}] {doc}")

        return "\n".join(formatted_results)
