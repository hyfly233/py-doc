import os

import fitz
from dotenv import load_dotenv

load_dotenv()


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
        color_map = {
            "高": fitz.utils.getColor("red"),
            "中": fitz.utils.getColor("orange"),
            "低": fitz.utils.getColor("yellow")
        }
        color = color_map.get(severity, fitz.utils.getColor("yellow"))

        # 在文档中查找并高亮文本
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


if __name__ == '__main__':
    pdf_path: str = os.getenv('PDF_PATH')
    text_blocks, doc = parse_document(pdf_path)
    # print("text_blocks:", text_blocks)
    print("doc:", doc)

    new_doc = highlight_issues_in_document(doc, text_blocks, [{
        "content": "Because the database is in an inconsistent state, the usual tools to disassociate the IP no longer work",
        "severity": "高",
        "issue_type": "IP地址关联问题",
        "suggestion": "请检查数据库状态并手动解除IP关联",
        "reasoning": "数据库状态不一致导致无法正常解除IP关联"
    }])

    new_doc.save("output/highlighted_document.pdf")
