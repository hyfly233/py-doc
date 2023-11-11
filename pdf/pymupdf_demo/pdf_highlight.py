import os
from typing import List

import fitz
from dotenv import load_dotenv

load_dotenv()

COLOR_MAP = {
    "high": fitz.utils.getColor("red"),
    "middle": fitz.utils.getColor("orange"),
    "low": fitz.utils.getColor("yellow"),
}


class BaseAuditReport:
    def __init__(
        self,
        content: str,
        issue_type: str = None,
        severity: str = None,
        suggestion: str = None,
        reasoning: str = None,
    ):
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

    def __init__(
        self,
        content: str,
        issue_type: str = None,
        severity: str = None,
        suggestion: str = None,
        reasoning: str = None,
        page: int = -1,
    ):
        """
        初始化实例
        :param page: 问题所在的页码
        """
        super().__init__(content, issue_type, severity, suggestion, reasoning)
        self.page = page


def add_highlight_to_pdf(pdf_path: str, issues: List[PdfAuditReport]) -> fitz.Document:
    # doc = fitz.open(stream=pdf_path, filetype="pdf")
    doc = fitz.open(pdf_path)

    for issue in issues:
        for page_num in range(doc.page_count):
            page = doc[page_num]

            # 搜索文本位置
            text_instances = page.search_for(issue.content)

            for inst in text_instances:
                # 添加高亮注释
                highlight = page.add_highlight_annot(inst)
                highlight.set_colors(
                    stroke=COLOR_MAP.get(issue.severity, COLOR_MAP.get("low"))
                )
                highlight.set_info(
                    title=f"审核问题 - {issue.severity}严重程度",
                    content=f"问题类型: {issue.issue_type}\n"
                    f"严重程度: {issue.severity}\n"
                    f"建议: {issue.suggestion}\n"
                    f"说明: {issue.reasoning}",
                )
                highlight.update()

                if issue.severity == "high":
                    # 如果是高严重度问题，添加红色边框
                    border_rect = page.add_rect_annot(inst)
                    border_rect.set_colors(stroke=COLOR_MAP["high"])
                    border_rect.set_border(width=2)
                    border_rect.update()

    # doc.save("output/highlighted_document.pdf")
    # doc.close()
    return doc


if __name__ == "__main__":
    pdf_path: str = os.getenv("PDF_PATH")

    highlighted_doc = add_highlight_to_pdf(
        pdf_path,
        [
            PdfAuditReport(
                content="Look for the vnet NIC",
                issue_type="条款不明确",
                severity="high",
                suggestion="请修改为明确的条款",
                reasoning="测试内容",
                page=1,
            ),
            PdfAuditReport(
                content="Sending discover",
                issue_type="条款不明确",
                severity="low",
                suggestion="测试有多个匹配项",
                reasoning="此条款可能导致法律风险",
                page=10,
            ),
        ],
    )

    highlighted_doc.save("output/highlighted_document.pdf")
    highlighted_doc.close()
