"""
Omni-Writer AI - 多源素材库与 RAG 检索引擎
使用 ChromaDB 实现本地向量存储与语义检索，打破 AI 信息茧房。
"""
import chromadb
from openai import OpenAI
import yaml


class KnowledgeBase:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 初始化 Embedding 客户端
        self.embedding_client = OpenAI(
            api_key=self.config['llm_config']['embedding_api_key'],
            base_url=self.config['llm_config']['embedding_base_url']
        )

        # 初始化 ChromaDB 本地持久化客户端
        self.db_path = "data/chroma_db"
        self.client = chromadb.PersistentClient(path=self.db_path)
        # 获取或创建一个名为 "novel_materials" 的集合
        self.collection = self.client.get_or_create_collection(name="novel_materials")

        print(f"[KnowledgeBase] 初始化完成，当前素材库共有 {self.collection.count()} 条素材。")

    def _get_embedding(self, text):
        """调用 API 获取文本的向量"""
        response = self.embedding_client.embeddings.create(
            input=text,
            model=self.config['llm_config']['embedding_model']
        )
        return response.data[0].embedding

    def add_material(self, text, source="未知来源"):
        """将一段素材文本入库"""
        if not text.strip():
            return

        embedding = self._get_embedding(text)
        # 使用文本的 hash 值作为唯一 ID，防止重复插入
        doc_id = str(hash(text))

        self.collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[{"source": source}],
            ids=[doc_id]
        )
        print(f"[KnowledgeBase] 成功添加素材: {text[:30]}...")

    def retrieve_materials(self, query, top_k=3):
        """根据查询文本，检索最相关的 top_k 条素材"""
        if self.collection.count() == 0:
            return "素材库为空。"

        query_embedding = self._get_embedding(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        # 提取检索到的文档内容
        retrieved_docs = results.get('documents', [[]])[0]
        if not retrieved_docs:
            return "未检索到相关素材。"

        # 格式化输出
        formatted_results = []
        for i, doc in enumerate(retrieved_docs):
            formatted_results.append(f"[参考素材{i+1}] {doc}")

        return "\n".join(formatted_results)
