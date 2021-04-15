import os

from docx import Document
from docx.shared import RGBColor
from dotenv import load_dotenv

load_dotenv()


def add_highlight(file_path, word):
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
                run.font.color.rgb = RGBColor(255, 0, 0)
                break

        doc.save(file_path)


def add_highlights(file_path, word):
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
                            if k > 0:
                                # 添加高亮的目标词
                                highlight_run = paragraph.add_run(f"「{word}」")
                                highlight_run.font.color.rgb = RGBColor(255, 0, 0)
                                highlight_run.font.name = original_font.name
                                highlight_run.font.size = original_font.size
                                highlight_run.font.bold = original_font.bold
                                highlight_run.font.italic = original_font.italic

                            if part:
                                # 添加普通文本
                                text_run = paragraph.add_run(part)
                                text_run.font.name = original_font.name
                                text_run.font.size = original_font.size
                                text_run.font.bold = original_font.bold
                                text_run.font.italic = original_font.italic

        doc.save(file_path)


if __name__ == '__main__':
    word_path: str = os.getenv('WORD_PATH')
    add_highlights(word_path, "喵")
