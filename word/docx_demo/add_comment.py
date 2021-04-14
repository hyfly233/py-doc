import os

from docx import Document
from dotenv import load_dotenv

load_dotenv()


def add_comment(file_path, word):
    if file_path.endswith('.docx'):
        doc = Document(file_path)
        paragraph = doc.add_paragraph("这是一个新的段落。")

        # 需要重新构建段落以便正确分割run
        full_text = paragraph.text
        if word in full_text:
            # 清空段落
            paragraph.clear()

            # 分割文本
            parts = full_text.split(word)

            for i, part in enumerate(parts):
                if part:
                    paragraph.add_run(part)

                if i < len(parts) - 1:  # 不是最后一部分
                    # 为目标词语创建单独的run
                    target_run = paragraph.add_run(word)

                    # 添加注释
                    doc.add_comment(
                        runs=[target_run],
                        text=f"这是对词语'{word}'的评论。",
                        author="作者名",
                        initials="作者"
                    )

                    print(f"已为词语'{word}'添加注释")

        doc.save(file_path)


def add_comments(file_path, word):
    if file_path.endswith('.docx'):
        doc = Document(file_path)

        for i, paragraph in enumerate(doc.paragraphs):
            p_text = paragraph.text
            if word in p_text:
                print(f"index: {i}, text: {p_text}")

                # 从后往前处理，避免索引变化问题
                for j in range(len(paragraph.runs) - 1, -1, -1):
                    run = paragraph.runs[j]
                    run_text = run.text
                    if word in run_text:
                        # 保存原run的格式
                        original_font = run.font

                        # 按目标词拆分文本
                        parts = run_text.split(word)

                        # 先清空当前run
                        run.clear()

                        # 重新构建内容
                        for k, part in enumerate(parts):
                            if part:
                                paragraph.add_run(part)

                            if k < len(parts) - 1:  # 不是最后一部分
                                # 为目标词语创建单独的run
                                target_run = paragraph.add_run(word)
                                target_run.font.color.rgb = original_font.color.rgb
                                target_run.font.name = original_font.name
                                target_run.font.size = original_font.size
                                target_run.font.bold = original_font.bold

                                # 添加注释
                                doc.add_comment(
                                    runs=[target_run],
                                    text=f"这是对词语'{word}'的评论。",
                                    author="作者名(测试)",
                                    initials="作者(测试)"
                                )

        doc.save(file_path)


if __name__ == '__main__':
    word_path: str = os.getenv('WORD_PATH')
    add_comment(word_path, "一个")
