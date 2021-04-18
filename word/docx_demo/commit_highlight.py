import os
from dataclasses import dataclass
from typing import Optional, Tuple

from docx import Document
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
    highlight_color: str = "yellow"  # 高亮颜色名称

    emphasize: bool = False  # 是否突出显示 (添加括号)
    emphasize_symbols: Tuple[str, str] = ("「", "」")  # 突出显示符号

    font_color: Optional[str] = None  # 字体颜色名称


def annotate_words_with_configs(file_path: str, word_configs: dict[str, AnnotationConfig]):
    """
    在文档中标注多个词语（为每个词语使用不同配置）

    Args:
        file_path: 源文档路径
        word_configs: 词语和配置的字典 {词语: 配置}
    """
    if not file_path.endswith('.docx'):
        print("只支持 .docx 格式文件")
        return

    # 生成新文件名
    base_name = os.path.splitext(file_path)[0]
    new_file_path = f"{base_name}_标注版本.docx"

    doc = Document(file_path)
    target_words = list(word_configs.keys())

    for i, paragraph in enumerate(doc.paragraphs):
        p_text = paragraph.text
        # 检查段落是否包含任何目标词语
        if any(word in p_text for word in target_words):
            print(f"处理段落 {i}: {p_text}")

            # 按词语长度排序，先处理长词语避免被短词语影响
            sorted_words = sorted(target_words, key=len, reverse=True)

            # 处理每个目标词语
            for word in sorted_words:
                # 重复处理直到该词语不再出现
                word_found = True
                while word_found:
                    word_found = False
                    # 从后往前处理，避免索引变化问题
                    for j in range(len(paragraph.runs) - 1, -1, -1):
                        if j >= len(paragraph.runs):  # 防止索引越界
                            continue

                        run = paragraph.runs[j]
                        run_text = run.text

                        # 检查当前run是否包含目标词语
                        if word in run_text:
                            _process_single_word_in_run(paragraph, j, run, word, word_configs[word], doc)
                            word_found = True
                            break  # 处理完一个run后跳出，重新开始

    # 保存新文档
    doc.save(new_file_path)
    print(f"标注完成，新文件已保存为: {new_file_path}")


def _process_single_word_in_run(paragraph, run_index, run, target_word, config, doc):
    """处理run中的单个目标词语（只处理第一个匹配的词语）"""
    original_font = run.font
    run_element = run._element
    parent = run_element.getparent()
    run_text = run.text

    # 如果不包含目标词语，直接返回
    if target_word not in run_text:
        return

    # 找到第一个目标词的位置
    index = run_text.find(target_word)
    if index == -1:
        return

    # 分成三部分：前缀、目标词、后缀
    prefix = run_text[:index]
    suffix = run_text[index + len(target_word):]

    # 移除原run
    parent.remove(run_element)

    # 在原位置插入新的runs
    insert_position = run_index

    # 插入前缀（如果存在）
    if prefix:
        prefix_run = paragraph.add_run(prefix)
        _copy_font_formatting(original_font, prefix_run.font)

        prefix_element = prefix_run._element
        parent.remove(prefix_element)
        parent.insert(insert_position, prefix_element)
        insert_position += 1

    # 插入标注的目标词
    annotated_word = target_word
    if config.emphasize:
        annotated_word = f"{config.emphasize_symbols[0]}{target_word}{config.emphasize_symbols[1]}"

    target_run = paragraph.add_run(annotated_word)
    _copy_font_formatting(original_font, target_run.font)

    # 应用字体颜色
    if config.font_color:
        _apply_font_color(target_run, config.font_color)

    # 应用高亮
    if config.highlight:
        _apply_highlight_color(target_run, config.highlight_color)

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

    # 插入后缀（如果存在）
    if suffix:
        suffix_run = paragraph.add_run(suffix)
        _copy_font_formatting(original_font, suffix_run.font)

        suffix_element = suffix_run._element
        parent.remove(suffix_element)
        parent.insert(insert_position, suffix_element)


def annotate_multiple_words_same_config(file_path: str, target_words: list[str], config: AnnotationConfig):
    """
    在文档中标注多个词语（使用相同配置）

    Args:
        file_path: 源文档路径
        target_words: 要标注的词语列表
        config: 标注配置
    """
    # 创建相同配置的字典
    word_configs = {word: config for word in target_words}
    annotate_words_with_configs(file_path, word_configs)


def _copy_font_formatting(source_font, target_font):
    """复制字体格式"""
    target_font.name = source_font.name
    target_font.size = source_font.size
    target_font.bold = source_font.bold
    target_font.italic = source_font.italic
    target_font.underline = source_font.underline


def _apply_highlight_color(run, color_name: str):
    """应用高亮颜色（使用颜色名称）"""
    from docx.enum.text import WD_COLOR_INDEX

    color_map = {
        "yellow": WD_COLOR_INDEX.YELLOW,
        "red": WD_COLOR_INDEX.RED,
        "green": WD_COLOR_INDEX.BRIGHT_GREEN,
        "blue": WD_COLOR_INDEX.BLUE,
        "pink": WD_COLOR_INDEX.PINK,
        "cyan": WD_COLOR_INDEX.TURQUOISE,
        "gray": WD_COLOR_INDEX.GRAY_25,
        "purple": WD_COLOR_INDEX.VIOLET,
        "lime": WD_COLOR_INDEX.BRIGHT_GREEN,
    }

    run.font.highlight_color = color_map.get(color_name.lower(), WD_COLOR_INDEX.YELLOW)


def _apply_font_color(run, color_name: str):
    """应用字体颜色（使用颜色名称）"""
    from docx.shared import RGBColor

    color_map = {
        "red": RGBColor(255, 0, 0),
        "blue": RGBColor(0, 0, 255),
        "green": RGBColor(0, 128, 0),
        "purple": RGBColor(128, 0, 128),
        "brown": RGBColor(165, 42, 42),
        "black": RGBColor(0, 0, 0),
        "gray": RGBColor(128, 128, 128),
        "pink": RGBColor(255, 192, 203),
        "yellow": RGBColor(255, 255, 0),
    }

    run.font.color.rgb = color_map.get(color_name.lower(), RGBColor(0, 0, 0))


# 预设配置
def create_highlight_config(color: str = "yellow") -> AnnotationConfig:
    """创建高亮配置"""
    return AnnotationConfig(highlight=True, highlight_color=color)


def create_comment_config(comment_text: str = "", author: str = "标注者") -> AnnotationConfig:
    """创建注释配置"""
    return AnnotationConfig(add_comment=True, comment_text=comment_text, comment_author=author)


def create_emphasize_config(symbols: Tuple[str, str] = ("「", "」"),
                            color: str = "red") -> AnnotationConfig:
    """创建突出显示配置"""
    return AnnotationConfig(emphasize=True, emphasize_symbols=symbols, font_color=color)


def create_full_annotation_config(comment_text: str = "",
                                  author: str = "标注者",
                                  highlight_color: str = "yellow",
                                  font_color: str = "red",
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

    # 方案1: 多个词语使用不同配置
    word_configs = {
        # "公司": create_highlight_config(color="yellow"),  # 黄色高亮
        "喵": create_emphasize_config(symbols=("「", "」"), color="red"),  # 红色突出显示
        # "合同": create_comment_config(comment_text="法律文件", author="法务"),  # 只添加注释
        # "卖方": create_full_annotation_config(
        #     comment_text="重要角色标识",
        #     author="审核员",
        #     highlight_color = "green",  # 绿色高亮
        #     font_color = "blue"  # 蓝色字体
        #     symbols=("【", "】")  # 方括号
        # ),
    }
    annotate_words_with_configs(word_path, word_configs)

    # 方案2: 多个词语使用相同配置
    # same_config = create_emphasize_config(color=(255, 0, 0))
    # annotate_multiple_words_same_config(word_path, ["甲方", "乙方"], same_config)
