import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple, List

from docx import Document
from dotenv import load_dotenv

from word.docx_demo.common import copy_font_format

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

    if not target_words:
        print("没有提供任何词语进行标注")
        return

    # 按词语长度降序排序，优先处理长词，避免短词干扰长词的匹配
    sorted_words = sorted(target_words, key=len, reverse=True)

    for i, paragraph in enumerate(doc.paragraphs):
        full_text = paragraph.text

        # 检查是否包含任何目标词语
        has_target_words = any(word in full_text for word in sorted_words)
        if not has_target_words:
            continue

        print(f"index: {i}, original text: {full_text}")

        # 创建字符到格式的映射
        char_formats = []
        char_index = 0

        for run in paragraph.runs:
            run_text = run.text
            for char in run_text:
                char_formats.append(run.font)
                char_index += 1

        # 构建正则表达式，匹配所有目标词语，如：喵喵公司|公司|喵
        pattern = '|'.join(re.escape(word) for word in sorted_words)

        # 分割文本，保留分隔符
        parts = re.split(f'({pattern})', full_text)

        # 清空段落的所有runs
        for run in paragraph.runs:
            run.clear()

        # 移除所有runs
        while len(paragraph.runs) > 0:
            paragraph._element.remove(paragraph.runs[0]._element)

        # 重新构建段落内容
        current_pos = 0
        for part in parts:
            if not part:  # 跳过空字符串
                continue

            if part in sorted_words:
                config = word_configs[part]

                # 构建标注文本
                annotated_word = part
                if config.emphasize:
                    annotated_word = f"{config.emphasize_symbols[0]}{part}{config.emphasize_symbols[1]}"

                # 添加标注的目标词
                target_run = paragraph.add_run(annotated_word)

                # 继承原文字的格式（除了颜色）
                if current_pos < len(char_formats):
                    source_font = char_formats[current_pos]
                    copy_font_format(source_font, target_run.font)

                # 应用字体颜色
                if config.font_color:
                    _apply_font_color(target_run, config.font_color)

                # 应用高亮
                if config.highlight:
                    _apply_highlight_color(target_run, config.highlight_color)

                # 添加注释
                if config.add_comment:
                    try:
                        comment_text = config.comment_text or f"标注词语: {part}"
                        doc.add_comment(
                            runs=[target_run],
                            text=comment_text,
                            author=config.comment_author,
                            initials=config.comment_initials
                        )
                    except Exception as e:
                        print(f"添加注释失败: {e}")
            else:
                # 对于普通文本，按字符重建，保持原有格式
                start_pos = current_pos
                for char_idx, char in enumerate(part):
                    format_idx = start_pos + char_idx
                    if format_idx < len(char_formats):
                        # 为每个字符创建单独的run（如果格式不同）
                        if char_idx == 0 or (
                                format_idx > 0 and char_formats[format_idx] != char_formats[format_idx - 1]):
                            # 创建新的run
                            char_run = paragraph.add_run(char)
                            copy_font_format(char_formats[format_idx], char_run.font)
                            # 保持原有颜色
                            if char_formats[format_idx].color.rgb:
                                char_run.font.color.rgb = char_formats[format_idx].color.rgb
                        else:
                            # 添加到最后一个run
                            if paragraph.runs:
                                paragraph.runs[-1].text += char
                    else:
                        # 如果超出了格式范围，使用最后一个可用格式
                        if char_idx == 0:
                            char_run = paragraph.add_run(char)
                            if char_formats:
                                copy_font_format(char_formats[-1], char_run.font)
                                if char_formats[-1].color.rgb:
                                    char_run.font.color.rgb = char_formats[-1].color.rgb
                        else:
                            if paragraph.runs:
                                paragraph.runs[-1].text += char

            current_pos += len(part)

        print(f"index: {i}, processed text: {paragraph.text}")

    # 保存新文档
    doc.save(new_file_path)
    print(f"标注完成，新文件已保存为: {new_file_path}")


def annotate_multiple_words_same_config(file_path: str, target_words: List[str], config: AnnotationConfig):
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
        "公司": create_highlight_config(color="yellow"),  # 黄色高亮
        "喵": create_emphasize_config(symbols=("「", "」"), color="red"),  # 红色突出显示
        "卖方": create_full_annotation_config(
            comment_text="对卖方的评论",
            author="评论员1",
            highlight_color="green",  # 绿色高亮
            font_color="blue",  # 蓝色字体
            symbols=("【", "】")  # 方括号
        ),
        "喵喵公司": create_full_annotation_config(
            comment_text="对喵喵公司的评论",
            author="评论员2",
            highlight_color="red",
            font_color="lime",
            symbols=("[", "]")
        ),
    }
    annotate_words_with_configs(word_path, word_configs)

    # 方案2: 多个词语使用相同配置
    # same_config = create_emphasize_config(color="red")
    # annotate_multiple_words_same_config(word_path, ["甲方", "乙方"], same_config)