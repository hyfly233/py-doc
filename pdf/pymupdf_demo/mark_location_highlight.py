import os
from typing import List

import fitz
from dotenv import load_dotenv

load_dotenv()

COLOR_MAP = {
    "high": fitz.utils.getColor("red"),
    "middle": fitz.utils.getColor("orange"),
    "low": fitz.utils.getColor("yellow")
}


class BaseAuditReport:
    def __init__(self, content: str, issue_type: str = None, severity: str = None, suggestion: str = None,
                 reasoning: str = None):
        """
        初始化实例
        :param content: 有问题的具体文本内容（原文中的确切文字）
        :param issue_type: 问题类型（如：条款不明确、风险条款、缺失信息、法律风险等）
        :param severity: 问题严重程度（如：high、middle、low）
        :param suggestion: 针对问题的建议（如：修改、补充、删除等）
        :param reasoning: 问题的说明或原因（如：法律风险、合规性问题等）
        """
        self.content = content
        self.issue_type = issue_type
        self.severity = severity
        self.suggestion = suggestion
        self.reasoning = reasoning


class PdfAuditReport(BaseAuditReport):
    """Pdf审核报告类，用于存储和处理审核问题"""

    def __init__(self, content: str, issue_type: str = None, severity: str = None, suggestion: str = None,
                 reasoning: str = None, page: int = -1):
        """
        初始化实例
        :param page: 问题所在的页码
        """
        super().__init__(content, issue_type, severity, suggestion, reasoning)
        self.page = page


def parse_document(file_path):
    if file_path.endswith('.pdf'):
        doc = fitz.open(file_path)
        text_blocks = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            blocks = page.get_text("dict")
            for block in blocks["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text_blocks.append({
                                "text": span["text"],
                                "bbox": span["bbox"],  # 位置坐标
                                "page": page_num,
                                "font": span["font"],
                                "size": span["size"]
                            })
        return text_blocks, doc


def highlight_issues_in_document(doc, text_blocks, issues):
    highlighted_doc = doc

    for issue in issues:
        issue_text = issue["content"]
        severity = issue["severity"]

        # 根据严重程度设置颜色

        color = COLOR_MAP.get(severity, fitz.utils.getColor("yellow"))

        # 在文档中查找高亮文本
        for page_num in range(doc.page_count):
            page = highlighted_doc[page_num]

            # 搜索文本位置
            text_instances = page.search_for(issue_text)

            for inst in text_instances:
                # 添加高亮注释
                highlight = page.add_highlight_annot(inst)
                highlight.set_colors(stroke=color)
                highlight.set_info(
                    title=f"审核问题 - {severity}严重程度",
                    content=f"问题类型: {issue['issue_type']}\n"
                            f"建议: {issue['suggestion']}\n"
                            f"说明: {issue['reasoning']}"
                )
                highlight.update()

    return highlighted_doc


def add_highlight_to_pdf(pdf_path: str, issues: List[PdfAuditReport]):
    doc = fitz.open(stream=pdf_path, filetype="pdf")



    pass


if __name__ == '__main__':
    pdf_path: str = os.getenv('PDF_PATH')
    text_blocks, doc = parse_document(pdf_path)
    # print("text_blocks:", text_blocks)
    print("doc:", doc)

    new_doc = highlight_issues_in_document(doc, text_blocks, [{
        "content": "Because the database is in an inconsistent state, the usual tools to disassociate the IP no longer work",
        "severity": "high",
        "issue_type": "IP地址关联问题",
        "suggestion": "请检查数据库状态并手动解除IP关联",
        "reasoning": "数据库状态不一致导致无法正常解除IP关联"
    }])

    new_doc.save("output/highlighted_document.pdf")
