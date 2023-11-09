import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from dotenv import load_dotenv

from word.docx_demo.t_tables import table_to_markdown

load_dotenv()


class LocationType(Enum):
    PARAGRAPH = "paragraph"
    TABLE = "table"


@dataclass
class DocxContent:
    index: int
    type: str
    content: str


@dataclass
class DocxContentExtraction:
    paragraph_count: int = 0
    paragraphs: Optional[List[DocxContent]] = None
    tables: Optional[List[DocxContent]] = None


def content_extraction(file_path: str) -> List[DocxContent]:
    """从 Word 文档中提取内容"""
    if not file_path.endswith('.docx'):
        raise ValueError("仅支持 .docx 格式的文件")

    try:
        doc = Document(file_path)
    except Exception as e:
        raise ValueError(f"无法打开Word文档，文件可能已损坏或格式不正确: {str(e)}")
    dcl: List[DocxContent] = []
    table_index = 0
    para_index = 0
    for i, iter in enumerate(doc.iter_inner_content()):
        if isinstance(iter, Paragraph):
            para_index += 1
            if iter.text.strip():
                dc = DocxContent(index=para_index, type="paragraph", content=iter.text)
                dcl.append(dc)
        elif isinstance(iter, Table):
            table_index += 1
            dc = DocxContent(
                index=table_index, type="table", content=table_to_markdown(iter)
            )
            dcl.append(dc)
    return dcl


if __name__ == '__main__':
    word_path: str = os.getenv('WORD_PATH')

    try:
        ce = content_extraction(word_path)

        for _ce in ce:
            if _ce.type == "paragraph":
                print(f"\n段落内容 {_ce.index}:")
                print(f"{_ce.content}")

            if _ce.type == "table":
                print(f"\n表格内容 {_ce.index}:")
                print(f"{_ce.content}")

    except Exception as e:
        print(f"处理文件时发生错误: {e}")
