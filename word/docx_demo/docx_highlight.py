import os

from docx import Document
from docx.shared import RGBColor
from dotenv import load_dotenv

load_dotenv()


def add_comment(file_path, word):
    if file_path.endswith('.docx'):
        doc = Document(file_path)
        paragraph = doc.add_paragraph("这是一个新的段落。")

        for run in paragraph.runs:
            run_text = run.text
            print(f"Run text: {run_text}")

            if word in run_text:
                # 直接修改run的文本，用特殊格式标记目标词语
                highlighted_text = run_text.replace(word, f"【{word}】")
                run.text = highlighted_text

                # 为整个run添加注释（如果支持的话）
                try:
                    doc.add_comment(
                        runs=[run],
                        text=f"这是对词语'{word}'的评论。",
                        author="作者名",
                        initials="作者"
                    )
                    print(f"已为词语'{word}'添加注释")
                except Exception as e:
                    print(f"添加注释失败: {e}")
                    # 使用颜色标记作为备选方案
                    run.font.color.rgb = RGBColor(255, 0, 0)

                break

        doc.save(file_path)


if __name__ == '__main__':
    word_path: str = os.getenv('WORD_PATH')
    add_comment(word_path, "一个")
