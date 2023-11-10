from docx.text.font import Font


def copy_font_format(source_font: Font, target_font: Font):
    """复制字体格式"""
    try:
        if source_font.name:
            target_font.name = source_font.name
        if source_font.size:
            target_font.size = source_font.size
        if source_font.bold is not None:
            target_font.bold = source_font.bold
        if source_font.italic is not None:
            target_font.italic = source_font.italic
        if source_font.underline is not None:
            target_font.underline = source_font.underline
        if source_font.color.rgb:
            # 颜色由调用方决定，这里不复制原颜色
            pass
    except Exception:
        pass
