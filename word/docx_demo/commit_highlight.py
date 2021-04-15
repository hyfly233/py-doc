import os
from dataclasses import dataclass
from typing import Optional, Tuple

from docx import Document
from docx.shared import RGBColor
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AnnotationConfig:
    """标注配置类"""
    add_comment: bool = False  # 是否添加注释
    comment_text: str = ""  # 注释内容
    comment_author: str = "标注者"  # 注释作者
    comment_initials: str = "标"  # 作者简称

    highlight: bool = False  # 是否高亮
    highlight_color: Tuple[int, int, int] = (255, 255, 0)  # 高亮颜色 (黄色)

    emphasize: bool = False  # 是否突出显示 (添加括号)
    emphasize_symbols: Tuple[str, str] = ("「", "」")  # 突出显示符号

    font_color: Optional[Tuple[int, int, int]] = None  # 字体颜色


def annotate_word_in_document(file_path: str, target_word: str, config: AnnotationConfig):
    """
    在文档中标注指定词语

    Args:
        file_path: 源文档路径
        target_word: 要标注的词语
        config: 标注配置
    """
    if not file_path.endswith('.docx'):
        print("只支持 .docx 格式文件")
        return

    # 生成新文件名
    base_name = os.path.splitext(file_path)[0]
    new_file_path = f"{base_name}_标注版本.docx"

    doc = Document(file_path)

    for i, paragraph in enumerate(doc.paragraphs):
        p_text = paragraph.text
        if target_word in p_text:
            print(f"处理段落 {i}: {p_text}")

            # 从后往前处理，避免索引变化问题
            for j in range(len(paragraph.runs) - 1, -1, -1):
                run = paragraph.runs[j]
                run_text = run.text
                if target_word in run_text:
                    # 保存原run的格式和位置
                    original_font = run.font
                    run_element = run._element
                    parent = run_element.getparent()

                    # 按目标词拆分文本
                    parts = run_text.split(target_word)

                    # 移除原run
                    parent.remove(run_element)

                    # 在原位置插入新的runs
                    insert_position = j
                    for k, part in enumerate(parts):
                        if part:
                            # 创建普通文本run
                            new_run = paragraph.add_run(part)
                            _copy_font_formatting(original_font, new_run.font)

                            # 移动到正确位置
                            new_element = new_run._element
                            parent.remove(new_element)
                            parent.insert(insert_position, new_element)
                            insert_position += 1

                        # 在非最后部分后插入标注的目标词
                        if k < len(parts) - 1:
                            # 构建标注文本
                            annotated_word = target_word
                            if config.emphasize:
                                annotated_word = f"{config.emphasize_symbols[0]}{target_word}{config.emphasize_symbols[1]}"

                            # 创建标注run
                            target_run = paragraph.add_run(annotated_word)
                            _copy_font_formatting(original_font, target_run.font)

                            # 应用字体颜色
                            if config.font_color:
                                target_run.font.color.rgb = RGBColor(*config.font_color)

                            # 应用高亮
                            if config.highlight:
                                target_run.font.highlight_color = _rgb_to_highlight_color(config.highlight_color)

                            # 添加注释
                            if config.add_comment:
                                comment_text = config.comment_text or f"标注词语: {target_word}"
                                doc.add_comment(
                                    runs=[target_run],
                                    text=comment_text,
                                    author=config.comment_author,
                                    initials=config.comment_initials
                                )

                            # 移动到正确位置
                            target_element = target_run._element
                            parent.remove(target_element)
                            parent.insert(insert_position, target_element)
                            insert_position += 1

    # 保存新文档
    doc.save(new_file_path)
    print(f"标注完成，新文件已保存为: {new_file_path}")


def _copy_font_formatting(source_font, target_font):
    """复制字体格式"""
    target_font.name = source_font.name
    target_font.size = source_font.size
    target_font.bold = source_font.bold
    target_font.italic = source_font.italic
    target_font.underline = source_font.underline


def _rgb_to_highlight_color(rgb: Tuple[int, int, int]):
    """将RGB颜色转换为Word高亮颜色（简化版本）"""
    from docx.enum.text import WD_COLOR_INDEX

    # 简单的颜色映射
    color_map = {
        (255, 255, 0): WD_COLOR_INDEX.YELLOW,  # 黄色
        (255, 0, 0): WD_COLOR_INDEX.RED,  # 红色
        (0, 255, 0): WD_COLOR_INDEX.BRIGHT_GREEN,  # 绿色
        (0, 0, 255): WD_COLOR_INDEX.BLUE,  # 蓝色
        (255, 0, 255): WD_COLOR_INDEX.PINK,  # 粉色
        (0, 255, 255): WD_COLOR_INDEX.TURQUOISE,  # 青色
    }

    return color_map.get(rgb, WD_COLOR_INDEX.YELLOW)


# 预设配置
def create_highlight_config(color: Tuple[int, int, int] = (255, 255, 0)) -> AnnotationConfig:
    """创建高亮配置"""
    return AnnotationConfig(highlight=True, highlight_color=color)


def create_comment_config(comment_text: str = "", author: str = "标注者") -> AnnotationConfig:
    """创建注释配置"""
    return AnnotationConfig(add_comment=True, comment_text=comment_text, comment_author=author)


def create_emphasize_config(symbols: Tuple[str, str] = ("「", "」"),
                            color: Tuple[int, int, int] = (255, 0, 0)) -> AnnotationConfig:
    """创建突出显示配置"""
    return AnnotationConfig(emphasize=True, emphasize_symbols=symbols, font_color=color)


def create_full_annotation_config(comment_text: str = "",
                                  author: str = "标注者",
                                  highlight_color: Tuple[int, int, int] = (255, 255, 0),
                                  font_color: Tuple[int, int, int] = (255, 0, 0),
                                  symbols: Tuple[str, str] = ("「", "」")) -> AnnotationConfig:
    """创建完整标注配置（注释+高亮+突出显示）"""
    return AnnotationConfig(
        add_comment=True,
        comment_text=comment_text,
        comment_author=author,
        highlight=True,
        highlight_color=highlight_color,
        emphasize=True,
        emphasize_symbols=symbols,
        font_color=font_color
    )


if __name__ == '__main__':
    word_path: str = os.getenv('WORD_PATH')

    # 示例1: 只添加红色突出显示
    config1 = create_emphasize_config(color=(255, 0, 0))
    annotate_word_in_document(word_path, "喵", config1)

    # 示例2: 完整标注 (注释+高亮+突出显示)
    # config2 = create_full_annotation_config(
    #     comment_text="这是一个特殊的词语",
    #     author="审核员",
    #     highlight_color=(255, 255, 0),  # 黄色高亮
    #     font_color=(255, 0, 0),         # 红色字体
    #     symbols=("【", "】")            # 方括号
    # )
    # annotate_word_in_document(word_path, "公司", config2)
