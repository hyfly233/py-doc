import os

from docx import Document
from dotenv import load_dotenv

load_dotenv()


def add_comments(file_path, word):
    if not file_path.endswith('.docx'):
        print("只支持 .docx 格式文件")
        return
    doc = Document(file_path)

    # 生成新文件名
    base_name = os.path.splitext(file_path)[0]
    new_file_path = f"{base_name}_comments.docx"

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

    # 保存新文档
    doc.save(new_file_path)
    print(f"标注完成，新文件已保存为: {new_file_path}")



if __name__ == '__main__':
    word_path: str = os.getenv('WORD_PATH')
    add_comments(word_path, ["喵", "公司", "北京"])
