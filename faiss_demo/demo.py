import os
import pickle
import time

import faiss
import numpy as np
import requests
from docx import Document
from dotenv import load_dotenv

load_dotenv()


class DocxFaissSearchOllama:
    def __init__(self, base_url="http://localhost:11434", model_name="bge-m3"):
        """
        初始化 FAISS 文档搜索系统 (使用 Ollama BGE-M3)

        Args:
            base_url: Ollama 服务器的 URL
            model_name: 模型名称
        """
        self.base_url = base_url
        self.model_name = model_name
        self.embeddings_url = f"{base_url}/api/embeddings"

        # BGE-M3 的向量维度是 1024
        self.dimension = 1024

        self.index = faiss.IndexFlatIP(self.dimension)
        self.documents = []
        self.chunks = []

        # 测试连接
        self._test_connection()

    def _test_connection(self):
        """测试与 Ollama 的连接"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model['name'] for model in models]
                if self.model_name in model_names or f"{self.model_name}:latest" in model_names:
                    print(f"成功连接到 Ollama，模型 {self.model_name} 可用")
                else:
                    print(f"模型 {self.model_name} 未找到")
                    print(f"可用模型: {model_names}")
            else:
                print(f"Ollama 连接失败: HTTP {response.status_code}")
        except Exception as e:
            print(f"无法连接到 Ollama: {e}")

    def get_embedding(self, text, retries=3, delay=1):
        """
        获取文本的 embedding 向量

        Args:
            text: 输入文本
            retries: 重试次数
            delay: 重试延迟（秒）

        Returns:
            embedding 向量
        """
        for attempt in range(retries):
            try:
                payload = {
                    "model": self.model_name,
                    "prompt": text
                }

                response = requests.post(
                    self.embeddings_url,
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    embedding = np.array(result['embedding'], dtype=np.float32)

                    # 验证维度
                    if len(embedding) != self.dimension:
                        print(f"警告: 向量维度不匹配，期望 {self.dimension}，实际 {len(embedding)}")
                        # 调整维度
                        if len(embedding) > self.dimension:
                            embedding = embedding[:self.dimension]
                        else:
                            # 填充零值
                            padded = np.zeros(self.dimension, dtype=np.float32)
                            padded[:len(embedding)] = embedding
                            embedding = padded

                    return embedding
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

            except Exception as e:
                print(f"Embedding API error (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(delay * (2 ** attempt))
                else:
                    raise e

    def get_embeddings_batch(self, texts, batch_size=10):
        """
        批量获取文本的 embedding 向量

        Args:
            texts: 文本列表
            batch_size: 批处理大小（Ollama 建议较小的批次）

        Returns:
            embedding 向量数组
        """
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(texts) + batch_size - 1) // batch_size

            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} texts)")

            # Ollama 的 embedding API 通常一次处理一个文本
            batch_embeddings = []
            for text in batch:
                try:
                    embedding = self.get_embedding(text)
                    batch_embeddings.append(embedding)
                    time.sleep(0.1)  # 避免过于频繁的请求
                except Exception as e:
                    print(f"处理文本失败: {e}")
                    # 使用零向量作为后备
                    batch_embeddings.append(np.zeros(self.dimension, dtype=np.float32))

            embeddings.extend(batch_embeddings)

        return np.array(embeddings)

    def extract_text_from_docx(self, file_path):
        """
        从 docx 文件中提取文本

        Args:
            file_path: docx 文件路径

        Returns:
            提取的文本内容
        """
        try:
            doc = Document(file_path)
            text_content = []

            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text.strip())

            return '\n'.join(text_content)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return ""

    def split_text_into_chunks(self, text, chunk_size=512, overlap=50):
        """
        将文本分割成小块

        Args:
            text: 输入文本
            chunk_size: 块大小
            overlap: 重叠字符数

        Returns:
            文本块列表
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            if chunk.strip():
                chunks.append(chunk.strip())

            if end >= len(text):
                break

            start = end - overlap

        return chunks

    def add_docx_file(self, file_path):
        """
        添加一个 docx 文件到索引中

        Args:
            file_path: docx 文件路径
        """
        print(f"Processing: {file_path}")

        # 提取文本
        text = self.extract_text_from_docx(file_path)
        if not text:
            print(f"No text extracted from {file_path}")
            return

        # 分割文本
        chunks = self.split_text_into_chunks(text)
        print(f"Split into {len(chunks)} chunks")

        # 批量生成嵌入向量
        embeddings = self.get_embeddings_batch(chunks)

        # 标准化向量（用于内积相似度）
        faiss.normalize_L2(embeddings)

        # 添加到索引
        self.index.add(embeddings.astype('float32'))

        # 存储文档信息
        for i, chunk in enumerate(chunks):
            self.documents.append({
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'chunk_index': i,
                'text': chunk
            })
            self.chunks.append(chunk)

        print(f"Added {len(chunks)} chunks from {file_path}")

    def add_docx_directory(self, directory_path):
        """
        添加目录中的所有 docx 文件

        Args:
            directory_path: 目录路径
        """
        docx_files = [f for f in os.listdir(directory_path)
                      if f.lower().endswith('.docx') and not f.startswith('~')]

        print(f"Found {len(docx_files)} docx files")

        for filename in docx_files:
            file_path = os.path.join(directory_path, filename)
            self.add_docx_file(file_path)

    def search(self, query, top_k=5):
        """
        搜索相关文档

        Args:
            query: 查询文本
            top_k: 返回前 k 个结果

        Returns:
            搜索结果列表
        """
        if self.index.ntotal == 0:
            return []

        print(f"正在搜索: '{query}'")

        # 生成查询向量
        query_embedding = self.get_embedding(query)
        query_embedding = query_embedding.reshape(1, -1)
        faiss.normalize_L2(query_embedding)

        # 搜索
        scores, indices = self.index.search(query_embedding.astype('float32'), top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:  # 有效索引
                doc_info = self.documents[idx]
                results.append({
                    'score': float(score),
                    'file_name': doc_info['file_name'],
                    'file_path': doc_info['file_path'],
                    'chunk_index': doc_info['chunk_index'],
                    'text': doc_info['text']
                })

        return results

    def save_index(self, index_path='faiss_index_ollama.bin', metadata_path='metadata_ollama.pkl'):
        """
        保存索引和元数据

        Args:
            index_path: FAISS 索引文件路径
            metadata_path: 元数据文件路径
        """
        # 保存 FAISS 索引
        faiss.write_index(self.index, index_path)

        # 保存元数据
        metadata = {
            'documents': self.documents,
            'chunks': self.chunks,
            'dimension': self.dimension,
            'model_name': self.model_name
        }

        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)

        print(f"Index saved to {index_path}")
        print(f"Metadata saved to {metadata_path}")

    def load_index(self, index_path='faiss_index_ollama.bin', metadata_path='metadata_ollama.pkl'):
        """
        加载索引和元数据

        Args:
            index_path: FAISS 索引文件路径
            metadata_path: 元数据文件路径
        """
        # 加载 FAISS 索引
        self.index = faiss.read_index(index_path)

        # 加载元数据
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)

        self.documents = metadata['documents']
        self.chunks = metadata['chunks']
        self.dimension = metadata['dimension']
        self.model_name = metadata.get('model_name', self.model_name)

        print(f"Index loaded from {index_path}")
        print(f"Total documents: {len(self.documents)}")
        print(f"Model: {self.model_name}")


def main():
    # 创建搜索系统
    search_system = DocxFaissSearchOllama(
        base_url="http://localhost:11434",
        model_name="bge-m3"
    )

    # 测试 embedding 生成
    try:
        test_embedding = search_system.get_embedding("测试文本")
        print(f"成功生成 embedding，维度: {len(test_embedding)}")
    except Exception as e:
        print(f"Embedding 生成失败: {e}")
        return

    # 示例：添加 docx 文件
    docx_files = [
        # "path/to/your/document1.docx",
        # "path/to/your/document2.docx",
        os.getenv("WORD_PATH")
    ]

    # 或者添加整个目录
    # search_system.add_docx_directory("path/to/your/docx/directory")

    # 添加单个文件（示例）
    for file_path in docx_files:
        if os.path.exists(file_path):
            search_system.add_docx_file(file_path)

    # 保存索引
    if search_system.index.ntotal > 0:
        search_system.save_index()
        print("索引已保存")

    # 搜索示例
    while True:
        query = input("\n请输入搜索查询（输入 'quit' 退出）: ")
        if query.lower() == 'quit':
            break

        results = search_system.search(query, top_k=3)

        if results:
            print(f"\n找到 {len(results)} 个相关结果:")
            for i, result in enumerate(results, 1):
                print(f"\n结果 {i} (相似度: {result['score']:.4f}):")
                print(f"文件: {result['file_name']}")
                print(f"内容片段: {result['text'][:300]}...")
                print("-" * 50)
        else:
            print("未找到相关结果")


if __name__ == "__main__":
    main()