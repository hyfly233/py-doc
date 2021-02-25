import hashlib
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv

load_dotenv()


# 验证分块是否正确覆盖了原文
def verify_chunk_coverage(chunks):
    for i in range(len(chunks) - 1):
        current = chunks[i]
        next_chunk = chunks[i + 1]

        # 检查重叠是否正确
        overlap_start = current.position.char_end - current.overlap_end
        expected_next_start = next_chunk.position.char_start

        if overlap_start != expected_next_start:
            raise ValueError(f"分块{i}和{i + 1}之间重叠不正确")


@dataclass
class DocChunkPosition:
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
class DocChunk:
    """文档分块类"""
    chunk_id: str  # 分块唯一标识
    chunk_index: int  # 分块序号（从0开始）
    content: str  # 完整内容（包含重叠部分）
    position: DocChunkPosition  # 位置信息
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


class DocumentProcessor:
    """文档处理器"""

    def __init__(self, chunk_size: int = 2000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_document(self, doc: Document) -> Document:
        """处理文档，生成分块"""
        if not doc.content:
            raise ValueError("文档内容为空")

        chunks = self._create_chunks(doc)

        for chunk in chunks:
            doc.add_chunk(chunk)

        return doc

    def _create_chunks(self, doc: Document) -> List[DocChunk]:
        """创建带重叠信息的文档分块"""
        content = doc.content
        chunks = []

        start = 0
        chunk_index = 0

        while start < len(content):
            # 计算当前分块的结束位置
            end = min(start + self.chunk_size, len(content))

            # 尝试在合适的边界分割
            if end < len(content):
                end = self._find_split_boundary(content, end)

            # 计算重叠信息
            overlap_start = 0
            overlap_end = 0

            if chunk_index > 0:  # 不是第一个分块
                overlap_start = min(self.chunk_overlap, start)
                # 调整起始位置以包含重叠
                actual_start = start - overlap_start
            else:
                actual_start = start

            if end < len(content):  # 不是最后一个分块
                overlap_end = min(self.chunk_overlap, len(content) - end)
                # 调整结束位置以包含重叠
                actual_end = min(end + overlap_end, len(content))
            else:
                actual_end = end

            # 提取分块内容
            chunk_content = content[actual_start:actual_end]

            # 计算位置信息
            position = DocChunkPosition(
                char_start=actual_start,
                char_end=actual_end,
                line_start=self._get_line_number(content, actual_start),
                line_end=self._get_line_number(content, actual_end),
                overlap_start=overlap_start,
                overlap_end=overlap_end,
                content_start=start,
                content_end=end
            )

            # 创建分块
            chunk = DocChunk(
                chunk_id=f"{doc.doc_id}_chunk_{chunk_index:04d}",
                chunk_index=chunk_index,
                content=chunk_content,
                position=position,
                doc_id=doc.doc_id,
                target_chunk_size=self.chunk_size,
                tokens_count=self._count_tokens(chunk_content)
            )

            chunks.append(chunk)

            # 移动到下一个分块
            start = end
            chunk_index += 1

        return chunks

    def _find_split_boundary(self, content: str, position: int) -> int:
        """寻找合适的分割边界"""
        # 在合同文档中，优先在句号、分号、换行符处分割
        boundary_chars = ['。', '；', '\n', '，', ':', '：']
        search_range = min(100, len(content) - position)

        # 向后搜索边界字符
        for i in range(search_range):
            if content[position + i] in boundary_chars:
                return position + i + 1

        # 向前搜索边界字符
        for i in range(min(100, position)):
            if content[position - i] in boundary_chars:
                return position - i + 1

        return position

    def _get_line_number(self, content: str, position: int) -> int:
        """获取指定位置的行号"""
        return content[:position].count('\n') + 1

    def _count_tokens(self, text: str) -> int:
        """简单的token计数（可以替换为更精确的方法）"""
        return len(text.split())

    def _calculate_position(self, content: str, start: int, end: int) -> DocChunkPosition:
        """计算位置信息"""
        # 计算起始行号
        lines_before_start = content[:start].count('\n')
        lines_before_end = content[:end].count('\n')

        return DocChunkPosition(
            char_start=start,
            char_end=end,
            line_start=lines_before_start + 1,
            line_end=lines_before_end + 1
        )

class ChunkVerifier:
    """分块验证工具"""

    @staticmethod
    def verify_chunk_integrity(chunks: List[DocChunk], original_content: str) -> Dict:
        """验证分块完整性"""
        results = {
            "coverage_complete": True,
            "overlaps_correct": True,
            "content_matches": True,
            "issues": []
        }

        # 1. 验证覆盖完整性
        if chunks:
            first_chunk = chunks[0]
            last_chunk = chunks[-1]

            if first_chunk.position.content_start != 0:
                results["coverage_complete"] = False
                results["issues"].append("第一个分块没有从文档开头开始")

            if last_chunk.position.content_end != len(original_content):
                results["coverage_complete"] = False
                results["issues"].append("最后一个分块没有到达文档末尾")

        # 2. 验证相邻分块的连接
        for i in range(len(chunks) - 1):
            current = chunks[i]
            next_chunk = chunks[i + 1]

            # 检查内容连接
            if current.position.content_end != next_chunk.position.content_start:
                results["coverage_complete"] = False
                results["issues"].append(f"分块{i}和{i + 1}之间有内容缺失或重复")

            # 检查重叠正确性
            if current.position.overlap_end > 0:
                overlap_in_current = current.overlap_with_next
                overlap_in_next = next_chunk.overlap_with_previous

                if overlap_in_current != overlap_in_next:
                    results["overlaps_correct"] = False
                    results["issues"].append(f"分块{i}和{i + 1}的重叠内容不匹配")

        # 3. 验证内容一致性
        reconstructed = ChunkVerifier.reconstruct_content(chunks)
        if reconstructed != original_content:
            results["content_matches"] = False
            results["issues"].append("重构内容与原始内容不匹配")

        return results

    @staticmethod
    def reconstruct_content(chunks: List[DocChunk]) -> str:
        """从分块重构原始内容"""
        if not chunks:
            return ""

        content_parts = []

        for chunk in chunks:
            content_parts.append(chunk.content_without_overlap)

        return "".join(content_parts)

    @staticmethod
    def analyze_overlap_efficiency(chunks: List[DocChunk]) -> Dict:
        """分析重叠效率"""
        total_content = sum(chunk.position.content_length for chunk in chunks)
        total_overlap = sum(chunk.position.total_overlap for chunk in chunks)
        total_stored = sum(len(chunk.content) for chunk in chunks)

        return {
            "content_length": total_content,
            "total_overlap": total_overlap,
            "total_stored": total_stored,
            "overlap_ratio": total_overlap / total_stored if total_stored > 0 else 0,
            "efficiency": total_content / total_stored if total_stored > 0 else 0
        }


def create_sample_document():
    doc_id = str(uuid.uuid4())
    file_path = os.getenv("TXT_PATH")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    doc = Document(
        doc_id=doc_id,
        file_name=os.path.basename(file_path),
        file_path=file_path,
        file_checksum=hashlib.md5(content.encode()).hexdigest(),
        total_size=len(content),
        content=content,
        chunk_size=2000,
        chunk_overlap=200,
        metadata={
            "document_type": "contract",
            "language": "zh-CN"
        }
    )

    return doc


# 使用示例
def example_with_overlap_tracking():
    """带重叠跟踪的使用示例"""

    # 处理文档
    processor = DocumentProcessor(chunk_size=1000, chunk_overlap=100)
    doc = create_sample_document()
    processed_doc = processor.process_document(doc)

    # 验证分块
    verifier = ChunkVerifier()
    integrity_result = verifier.verify_chunk_integrity(
        processed_doc.chunks,
        processed_doc.content
    )

    print("分块完整性验证:")
    print(f"覆盖完整: {integrity_result['coverage_complete']}")
    print(f"重叠正确: {integrity_result['overlaps_correct']}")
    print(f"内容匹配: {integrity_result['content_matches']}")

    if integrity_result['issues']:
        print("发现问题:")
        for issue in integrity_result['issues']:
            print(f"  - {issue}")

    # 分析重叠效率
    efficiency = verifier.analyze_overlap_efficiency(processed_doc.chunks)
    print(f"\n重叠分析:")
    print(f"内容长度: {efficiency['content_length']}")
    print(f"重叠长度: {efficiency['total_overlap']}")
    print(f"存储效率: {efficiency['efficiency']:.2%}")

    # 展示分块详情
    for chunk in processed_doc.chunks[:3]:  # 只显示前3个
        print(f"\n分块 {chunk.chunk_index}:")
        print(f"  总长度: {len(chunk.content)}")
        print(f"  内容长度: {chunk.position.content_length}")
        print(f"  前重叠: {chunk.position.overlap_start}")
        print(f"  后重叠: {chunk.position.overlap_end}")
        print(f"  位置: {chunk.position.char_start}-{chunk.position.char_end}")


if __name__ == '__main__':
    example_with_overlap_tracking()
