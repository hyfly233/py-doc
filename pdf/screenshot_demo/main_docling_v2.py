import logging
import os
import time
from pathlib import Path
from typing import List

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    PdfPipelineOptions,
    TableStructureOptions,
    TableFormerMode,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types import DoclingDocument
from docling_core.types.doc import TableItem, ProvenanceItem
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
)
_log = logging.getLogger(__name__)


class TableLocation:
    def __init__(
        self, page_no: int, name: str, rect: tuple[float, float, float, float]
    ):
        self.page_no = page_no
        self.name = name
        self.rect = rect


def main():
    pdf_path: str = os.getenv("PDF_PATH")
    pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]

    # docling 识别表格并获取 bbox
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options = TableStructureOptions(
        do_cell_matching=False,  # 启用单元格匹配
        mode=TableFormerMode.FAST,
    )
    pipeline_options.images_scale = 3.0
    pipeline_options.generate_page_images = True

    pipeline_options.accelerator_options = AcceleratorOptions(
        num_threads=10,
        device=AcceleratorDevice.AUTO,
    )

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )

    start_time = time.time()
    # 格式化时间
    _log.info(
        f"开始转换文档，开始时间 [{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}] .........."
    )

    input_doc_path = Path(pdf_path)
    conv_result = converter.convert(input_doc_path)

    end_time = time.time()
    _log.info(
        f"转换文档结束，完成时间 [{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}] .........."
    )
    _log.info(
        f"转换文档状态 {conv_result.status} 耗时 [{end_time - start_time}] s .........."
    )

    _log.info(f"###########################")

    document: DoclingDocument = conv_result.document
    # 获取 table 的数量、位置
    tables: List[TableItem] = document.tables
    _log.info(f"文档的表格数量 {len(tables)} ---- ")

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, table in enumerate(tables):
        prov: List[ProvenanceItem] = table.prov
        location: str = ""
        for e in prov:
            page_no = e.page_no
            bbox = e.bbox

            t_height = bbox.height
            t_width = bbox.width

            location += (
                f"第 {page_no} 页 - "
                f"表格高度: {t_height} 宽度: {t_width} - "
                f"表格位置: left {bbox.l} top {bbox.t} right {bbox.r} bottom {bbox.b} - \n"
            )

            # 导入表格图片
            with (output_dir / f"p{page_no}_t{i}.png").open("wb") as fp:
                table.get_image(conv_result.document).save(fp, "PNG")

        _log.info(f"表格 {i} 的位置: {location} ---- ")


if __name__ == "__main__":
    main()
