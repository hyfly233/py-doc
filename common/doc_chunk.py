import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class DocChunkPosition:
    """文档分块位置信息"""
    char_start: int = 0  # 字符起始位置
    char_end: int = 0  # 字符结束位置
    line_start: int = 1  # 起始行号
    line_end: int = 1  # 结束行号
    page_start: Optional[int] = None  # 起始页码（如果适用）
    page_end: Optional[int] = None  # 结束页码（如果适用）

    def __post_init__(self):
        if self.char_start > self.char_end:
            raise ValueError("起始位置不能大于结束位置")
        if self.line_start > self.line_end:
            raise ValueError("起始行号不能大于结束行号")


@dataclass
class DocChunk:
    """文档分块类"""
    chunk_id: str  # 分块唯一标识
    chunk_index: int  # 分块序号（从0开始）
    content: str  # 分块内容
    position: DocChunkPosition  # 位置信息
    doc_id: str  # 所属文档ID

    # 可选的元数据
    content_hash: Optional[str] = None  # 内容哈希
    tokens_count: Optional[int] = None  # token数量
    created_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

        if self.content_hash is None:
            self.content_hash = hashlib.md5(self.content.encode()).hexdigest()

        if self.metadata is None:
            self.metadata = {}


@dataclass
class Document:
    """文档类"""
    doc_id: str  # 文档唯一标识
    file_name: str  # 文件名
    file_path: str  # 文件路径
    file_checksum: str  # 文件校验和
    total_size: int  # 文件总大小

    # 分块配置
    chunk_size: int = 2000  # 分块大小
    chunk_overlap: int = 200  # 分块重叠

    # 文档信息
    content: Optional[str] = None  # 原始内容
    chunks: Optional[List[DocChunk]] = None  # 分块列表
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

        if self.updated_at is None:
            self.updated_at = self.created_at

        if self.chunks is None:
            self.chunks = []

        if self.metadata is None:
            self.metadata = {}

    @property
    def chunk_count(self) -> int:
        """获取分块数量"""
        return len(self.chunks)

    def add_chunk(self, chunk: DocChunk):
        """添加分块"""
        if chunk.doc_id != self.doc_id:
            raise ValueError("分块不属于当前文档")
        self.chunks.append(chunk)
        self.updated_at = datetime.now()

    def get_chunk_by_position(self, char_position: int) -> Optional[DocChunk]:
        """根据字符位置获取分块"""
        for chunk in self.chunks:
            if (chunk.position.char_start <= char_position <=
                    chunk.position.char_end):
                return chunk
        return None
