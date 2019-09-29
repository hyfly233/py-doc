import os
import faiss
import numpy as np
from docx import Document
import pickle
import json
from openai import OpenAI
import time


class DocxFaissSearchOpenAI:
    def __init__(self, api_key=None, model_name='text-embedding-3-small'):
        """
        初始化 FAISS 文档搜索系统 (使用 OpenAI)

        Args:
            api_key: OpenAI API 密钥
            model_name: OpenAI embedding 模型名称
        """
        # 初始化 OpenAI 客户端
        self.client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
        self.model_name = model_name

        # 根据模型设置维度
        model_dimensions = {
            'text-embedding-3-small': 1536,
            'text-embedding-3-large': 3072,
            'text-embedding-ada-002': 1536
        }
        self.dimension = model_dimensions.get(model_name, 1536)

        self.index = faiss.IndexFlatIP(self.dimension)  # 使用内积相似度
        self.documents = []  # 存储文档信息
        self.chunks = []  # 存储文本块

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
                    time.sleep(delay * (2 ** attempt))  # 指数退避
                else:
                    raise e

    def get_embeddings_batch(self, texts, batch_size=100):
        """
        批量获取文本的 embedding 向量

        Args:
            texts: 文本列表
            batch_size: 批处理大小

        Returns:
            embedding 向量数组
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

                # 添加延迟以避免速率限制
                time.sleep(0.1)

            except Exception as e:
                print(f"Batch embedding error: {e}")
                # 如果批处理失败，逐个处理
                for text in batch:
                    embedding = self.get_embedding(text)
                    embeddings.append(embedding)
                    time.sleep(0.1)

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

    def split_text_into_chunks(self, text, chunk_size=1000, overlap=100):
        """
        将文本分割成小块

        Args:
            text: 输入文本
            chunk_size: 块大小（建议 OpenAI embedding 使用较大块）
            overlap: 重叠字符数

        Returns:
            文本块列表
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # 确保块不为空
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

    def save_index(self, index_path='faiss_index_openai.bin', metadata_path='metadata_openai.pkl'):
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

    def load_index(self, index_path='faiss_index_openai.bin', metadata_path='metadata_openai.pkl'):
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
    # 设置 OpenAI API 密钥
    # 方法1: 直接传入
    # api_key = "your-openai-api-key-here"
    # search_system = DocxFaissSearchOpenAI(api_key=api_key)

    # 方法2: 使用环境变量 (推荐)
    # export OPENAI_API_KEY="your-openai-api-key-here"
    search_system = DocxFaissSearchOpenAI()

    # 示例：添加 docx 文件
    docx_files = [
        # "path/to/your/document1.docx",
        # "path/to/your/document2.docx",
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

        print("正在搜索...")
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