import os
from dataclasses import dataclass
from typing import Optional, List

from docx import Document
from dotenv import load_dotenv

from word.docx_demo.t_tables import table_to_markdown

load_dotenv()


@dataclass
class DocxContent:
    index: int
    content: str


@dataclass
class DocxContentExtraction:
    paragraph_count: int = 0
    paragraphs: Optional[List[DocxContent]] = None
    tables: Optional[List[DocxContent]] = None


def content_extraction(file_path: str) -> DocxContentExtraction:
    """从 Word 文档中提取内容"""
    if not file_path.endswith('.docx'):
        raise ValueError("仅支持 .docx 格式的文件")

    doc = Document(file_path)
    pde: List[DocxContent] = []
    tde: List[DocxContent] = []

    # 提取段落内容
    for i, para in enumerate(doc.paragraphs):
        if para.text.strip():
            dc = DocxContent(
                index=i,
                content=para.text
            )
            pde.append(dc)

    # 提取表格内容
    for i, table in enumerate(doc.tables):
        dc = DocxContent(
            index=i,
            content=table_to_markdown(table)
        )
        tde.append(dc)

    dce = DocxContentExtraction(
        paragraph_count=len(doc.paragraphs),
        paragraphs=pde,
        tables=tde
    )

    return dce


if __name__ == '__main__':
    word_path: str = os.getenv('WORD_PATH')

    try:
        ce = content_extraction(word_path)
        print("提取的内容:")
        print(f"段落总数: {ce.paragraph_count}")
        print(f"段落数量: {len(ce.paragraphs) if ce.paragraphs else 0}")
        print(f"表格数量: {len(ce.tables) if ce.tables else 0}")

        # 可选：打印具体内容
        if ce.paragraphs:
            print("\n段落内容:")
            for para in ce.paragraphs:
                print(f"  [{para.index}]: {para.content}")

        if ce.tables:
            print("\n表格内容:")
            for table in ce.tables:
                print(f"  表格 {table.index}:")
                print(f"    {table.content}")

    except Exception as e:
        print(f"处理文件时发生错误: {e}")
