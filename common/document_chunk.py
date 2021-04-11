import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv

load_dotenv()

@dataclass
class DocumentChunkPosition:
    """文档分块位置信息"""
    char_start: int = 0  # 内容实际起始位置
    char_end: int = 0  # 内容实际结束位置
    line_start: int = 1  # 起始行号
    line_end: int = 1  # 结束行号

    # 重叠信息
    overlap_start: int = 0  # 与前一个分块的重叠字符数
    overlap_end: int = 0  # 与后一个分块的重叠字符数

    # 实际内容边界（不包含重叠）
    content_start: int = 0  # 实际内容起始位置
    content_end: int = 0  # 实际内容结束位置

    page_start: Optional[int] = None  # 起始页码（如果适用）
    page_end: Optional[int] = None  # 结束页码（如果适用）

    def __post_init__(self):
        if self.char_start > self.char_end:
            raise ValueError("起始位置不能大于结束位置")

        # 计算实际内容边界
        if self.content_start == 0:
            self.content_start = self.char_start + self.overlap_start
        if self.content_end == 0:
            self.content_end = self.char_end - self.overlap_end

    @property
    def total_length(self) -> int:
        """总长度（包含重叠）"""
        return self.char_end - self.char_start

    @property
    def content_length(self) -> int:
        """实际内容长度（不包含重叠）"""
        return self.content_end - self.content_start

    @property
    def total_overlap(self) -> int:
        """总重叠长度"""
        return self.overlap_start + self.overlap_end


@dataclass
class DocumentChunk:
    """文档分块类"""
    chunk_id: str  # 分块唯一标识
    chunk_index: int  # 分块序号（从0开始）
    content: str  # 完整内容（包含重叠部分）
    position: DocumentChunkPosition  # 位置信息
    doc_id: str  # 所属文档ID

    # 分块配置信息
    target_chunk_size: int = 0  # 目标分块大小
    actual_chunk_size: int = 0  # 实际分块大小

    # 可选元数据
    content_hash: Optional[str] = None  # 内容哈希
    tokens_count: Optional[int] = None  # token数量
    created_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

        if self.content_hash is None:
            self.content_hash = hashlib.md5(self.content.encode()).hexdigest()

        if self.actual_chunk_size == 0:
            self.actual_chunk_size = len(self.content)

        if self.metadata is None:
            self.metadata = {}

    @property
    def content_without_overlap(self) -> str:
        """获取不包含重叠的内容"""
        start_offset = self.position.overlap_start
        end_offset = len(self.content) - self.position.overlap_end
        return self.content[start_offset:end_offset]

    @property
    def overlap_with_previous(self) -> str:
        """获取与前一个分块的重叠内容"""
        if self.position.overlap_start == 0:
            return ""
        return self.content[:self.position.overlap_start]

    @property
    def overlap_with_next(self) -> str:
        """获取与后一个分块的重叠内容"""
        if self.position.overlap_end == 0:
            return ""
        return self.content[-self.position.overlap_end:]

    def get_absolute_position(self, relative_pos: int) -> int:
        """将相对位置转换为文档中的绝对位置"""
        return self.position.char_start + relative_pos

    def get_relative_position(self, absolute_pos: int) -> int:
        """将绝对位置转换为分块中的相对位置"""
        return absolute_pos - self.position.char_start


@dataclass
class BaseDocument:
    """文档类"""
    doc_id: str  # 文档唯一标识
    file_name: str  # 文件名
    file_path: str  # 文件路径
    file_checksum: str  # 文件校验和
    file_extension_name: str  # 文件扩展名
    total_size: Optional[int] = None  # 文件总大小

    # 分块配置
    chunk_size: int = 2000  # 分块大小
    chunk_overlap: int = 200  # 分块重叠

    # 文档信息
    content: Optional[str] = None  # 原始内容
    chunks: Optional[List[DocumentChunk]] = None  # 分块列表
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

    def add_chunk(self, chunk: DocumentChunk):
        """添加分块"""
        if chunk.doc_id != self.doc_id:
            raise ValueError("分块不属于当前文档")
        self.chunks.append(chunk)
        self.updated_at = datetime.now()

    def get_chunk_by_position(self, char_position: int) -> Optional[DocumentChunk]:
        """根据字符位置获取分块"""
        for chunk in self.chunks:
            if (chunk.position.char_start <= char_position <=
                    chunk.position.char_end):
                return chunk
        return None
