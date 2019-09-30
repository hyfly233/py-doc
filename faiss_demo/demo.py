import os
import pickle
import time

import faiss
import numpy as np
from docx import Document
from openai import OpenAI


class DocxFaissSearchVLLM:
    def __init__(self, base_url="http://localhost:8000/v1", api_key="dummy", model_name="custom-embedding-model"):
        """
        初始化 FAISS 文档搜索系统 (使用 vLLM)

        Args:
            base_url: vLLM 服务器的 URL
            api_key: API 密钥（vLLM 可以使用任意值）
            model_name: 模型名称
        """
        # 初始化 OpenAI 客户端，指向 vLLM 服务器
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key  # vLLM 通常不需要真实的 API key
        )
        self.model_name = model_name

        # 你需要根据实际模型设置维度
        # 可以通过模型信息或测试一个样本来获取
        self.dimension = self._get_embedding_dimension()

        self.index = faiss.IndexFlatIP(self.dimension)
        self.documents = []
        self.chunks = []

    def _get_embedding_dimension(self):
        """
        获取模型的 embedding 维度
        """
        try:
            # 测试一个简单文本来获取维度
            test_response = self.client.embeddings.create(
                input="test",
                model=self.model_name
            )
            return len(test_response.data[0].embedding)
        except Exception as e:
            print(f"无法自动获取维度: {e}")
            print("请手动设置 dimension")
            return 768  # 默认维度，需要根据实际模型调整

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
                response = self.client.embeddings.create(
                    input=text,
                    model=self.model_name
                )
                return np.array(response.data[0].embedding)
            except Exception as e:
                print(f"Embedding API error (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(delay * (2 ** attempt))
                else:
                    raise e

    def get_embeddings_batch(self, texts, batch_size=32):
        """
        批量获取文本的 embedding 向量
        """
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            print(f"Processing batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}")

            try:
                response = self.client.embeddings.create(
                    input=batch,
                    model=self.model_name
                )

                batch_embeddings = [np.array(data.embedding) for data in response.data]
                embeddings.extend(batch_embeddings)

                # 本地模型通常不需要延迟，但可以保留以防万一
                time.sleep(0.01)

            except Exception as e:
                print(f"Batch embedding error: {e}")
                # 如果批处理失败，逐个处理
                for text in batch:
                    embedding = self.get_embedding(text)
                    embeddings.append(embedding)

        return np.array(embeddings)

    def extract_text_from_docx(self, file_path):
        """从 docx 文件中提取文本"""
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
        """将文本分割成小块"""
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
        """添加一个 docx 文件到索引中"""
        print(f"Processing: {file_path}")

        text = self.extract_text_from_docx(file_path)
        if not text:
            print(f"No text extracted from {file_path}")
            return

        chunks = self.split_text_into_chunks(text)
        print(f"Split into {len(chunks)} chunks")

        embeddings = self.get_embeddings_batch(chunks)
        faiss.normalize_L2(embeddings)

        self.index.add(embeddings.astype('float32'))

        for i, chunk in enumerate(chunks):
            self.documents.append({
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'chunk_index': i,
                'text': chunk
            })
            self.chunks.append(chunk)

        print(f"Added {len(chunks)} chunks from {file_path}")

    def search(self, query, top_k=5):
        """搜索相关文档"""
        if self.index.ntotal == 0:
            return []

        query_embedding = self.get_embedding(query)
        query_embedding = query_embedding.reshape(1, -1)
        faiss.normalize_L2(query_embedding)

        scores, indices = self.index.search(query_embedding.astype('float32'), top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                doc_info = self.documents[idx]
                results.append({
                    'score': float(score),
                    'file_name': doc_info['file_name'],
                    'file_path': doc_info['file_path'],
                    'chunk_index': doc_info['chunk_index'],
                    'text': doc_info['text']
                })

        return results

    def save_index(self, index_path='faiss_index_vllm.bin', metadata_path='metadata_vllm.pkl'):
        """保存索引和元数据"""
        faiss.write_index(self.index, index_path)

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


def main():
    # 创建搜索系统，指向本地 vLLM 服务
    search_system = DocxFaissSearchVLLM(
        base_url=os.getenv("VLLM_BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name=os.getenv("MODEL_NAME")
    )

    # 测试连接
    try:
        test_embedding = search_system.get_embedding("测试连接")
        print(f"成功连接到 vLLM，embedding 维度: {len(test_embedding)}")
    except Exception as e:
        print(f"连接 vLLM 失败: {e}")
        return

    # 添加文档
    docx_files = [
        # "path/to/your/document1.docx",
        os.getenv("WORD_PATH")
    ]

    for file_path in docx_files:
        if os.path.exists(file_path):
            search_system.add_docx_file(file_path)

    # 保存索引
    if search_system.index.ntotal > 0:
        search_system.save_index()

    # 搜索循环
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
        else:
            print("未找到相关结果")


if __name__ == "__main__":
    main()