import os

from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableStructureOptions, TableFormerMode,
)
from dotenv import load_dotenv

load_dotenv()


def main():
    pdf_path: str = os.getenv('PDF_PATH')
    pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]

    # docling 识别表格并获取 bbox
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options = TableStructureOptions(
        do_cell_matching=False,  # 启用单元格匹配
        mode=TableFormerMode.FAST
    )



if __name__ == '__main__':
    main()