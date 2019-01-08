import json
import logging
import multiprocessing
import os
import time
from pathlib import Path
from typing import List

import torch.cuda
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    ApiVlmOptions,
    ResponseFormat,
    PdfPipelineOptions,
    TableStructureOptions,
    OcrMacOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.types import DoclingDocument
from docling_core.types.doc import TableItem, ProvenanceItem
from dotenv import load_dotenv

# from docling.pipeline.vlm_pipeline import VlmPipeline

# 加载 .env 文件
load_dotenv()

SOURCE = os.getenv('SOURCE')


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)
_log = logging.getLogger(__name__)


def ollama_vlm_options(model: str, prompt: str):
    options = ApiVlmOptions(
        url="http://localhost:11434/v1/chat/completions",  # the default Ollama endpoint
        params=dict(
            model=model,
        ),
        prompt=prompt,
        timeout=3600,
        scale=1.0,
        response_format=ResponseFormat.MARKDOWN,
    )
    return options

def main():
    # 获取CPU核心数
    cpu_cores = multiprocessing.cpu_count()
    _log.info(f"CPU核心数: {cpu_cores} --------")

    # # 配置 PdfPipelineOptions ----------------------
    pdf_pipeline_options = PdfPipelineOptions()
    pdf_pipeline_options.do_ocr = True  # 启用OCR
    ## 表格处理
    pdf_pipeline_options.do_table_structure = True  # 启用表结构提取
    pdf_pipeline_options.table_structure_options = TableStructureOptions(
        do_cell_matching=True,  # 启用单元格匹配
    )
    ## 代码块处理
    pdf_pipeline_options.do_code_enrichment = True  # 启用代码块提取
    ## 公式处理
    pdf_pipeline_options.do_formula_enrichment = True  # 启用公式提取
    ## 图片处理
    pdf_pipeline_options.do_picture_classification = True  # 启用对文档中的图片进行分类
    pdf_pipeline_options.do_picture_description = True  # 启用运行描述文档中的图片
    # pdf_pipeline_options.picture_description_options = PictureDescriptionVlmOptions(
    #     repo_id="",
    #     prompt="Describe the image in three sentences. Be consise and accurate.",
    # )
    pdf_pipeline_options.images_scale = 2.0
    pdf_pipeline_options.generate_picture_images = True

    ## 加速配置
    if torch.cuda.is_available():
        ## ocr配置
        pdf_pipeline_options.ocr_options.use_gpu = True
        pdf_pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=cpu_cores,
            device=AcceleratorDevice.CUDA,
            cuda_use_flash_attention2=True,
        )
    elif torch.mps.is_available():
        pdf_pipeline_options.ocr_options = OcrMacOptions()
        # pdf_pipeline_options.ocr_options = EasyOcrOptions()
        pdf_pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=cpu_cores,
            device=AcceleratorDevice.MPS,
        )
    else:
        pdf_pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=cpu_cores,
            device=AcceleratorDevice.AUTO,
        )

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pdf_pipeline_options
            ),
            InputFormat.DOCX: WordFormatOption(
                pipeline_options=pdf_pipeline_options
            )
        }
    )

    # # 配置 VlmPipelineOptions ----------------------
    # vlm_pipeline_options = VlmPipelineOptions(
    #     enable_remote_services=True  # <-- this is required!
    # )
    #
    # vlm_pipeline_options.vlm_options = ollama_vlm_options(
    #     # model="granite3.2-vision:2b",
    #     model="granite3.2-vision:2b-fp16",
    #     prompt="OCR the full page to markdown.",
    # )
    #
    # converter = DocumentConverter(
    #     format_options={
    #         InputFormat.PDF: PdfFormatOption(
    #             pipeline_options=vlm_pipeline_options,
    #             pipeline_cls=VlmPipeline,
    #         )
    #     }
    # )

    # # ----------------------------

    _log.info(f"转换器配置完成 ..........")

    try:
        start_time = time.time()
        # 格式化时间
        _log.info(
            f"开始转换文档，开始时间 [{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))}] ..........")

        # 转换文档
        input_doc_path = Path(SOURCE)
        conv_result = converter.convert(input_doc_path)

        end_time = time.time()
        _log.info(f"转换文档结束，完成时间 [{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time))}] ..........")
        _log.info(f"转换文档状态 {conv_result.status} 耗时 [{end_time - start_time}] s ..........")

        # 导出
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        doc_filename = conv_result.input.file.stem

        _log.info(f"###########################")

        _log.info(f"文档的页数 {len(conv_result.pages)} ---- ")
        for i, page in enumerate(conv_result.pages):
            _log.info(f"第 {i + 1} 页 - "
                      f"pageNo {page.page_no} - "
                      f"高度: {page.size.height} 宽度: {page.size.width} - "
                      )

        document: DoclingDocument = conv_result.document

        # 获取 table 的数量、位置
        tables: List[TableItem] = document.tables
        _log.info(f"文档的表格数量 {len(tables)} ---- ")
        for i, table in enumerate(tables):
            # 单独导出表格
            with (output_dir / f"{doc_filename}_{i}.md").open("w", encoding="utf-8") as fp:
                fp.write(conv_result.document.export_to_markdown())

            # ？？？
            location_tokens = table.get_location_tokens(doc=document)

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
                    f"表格位置: left {bbox.l} top {bbox.t} right {bbox.r} bottom {bbox.b} - "
                )

            _log.info(f"第 {i + 1} 个表格 - "
                      f"location_tokens：{location_tokens} - \n"
                      f"位置详情 {location} - "
                      )

        _log.info(f"###########################")



        # 将结果输出到 json 文件
        with (output_dir / f"{doc_filename}.json").open("w", encoding="utf-8") as file:
            json.dump(conv_result.document.export_to_dict(), file, indent=4)  # indent参数使输出的JSON格式化，更易读

        _log.info("开始导出结果到 Markdown ..........")

        # 导出到 markdown
        with (output_dir / f"{doc_filename}.md").open("w", encoding="utf-8") as fp:
            fp.write(conv_result.document.export_to_markdown())

        with (output_dir / f"{doc_filename}.html").open("w", encoding="utf-8") as fp:
            fp.write(conv_result.document.export_to_html())

        _log.info("导出结果到 Markdown 完成 ..........")

        # -----------------

        _log.info("开始分块 ..........")
        doc = conv_result.document

        # 配置分块
        chunker = HybridChunker()
        chunk_iter = chunker.chunk(dl_doc=doc)

        for i, chunk in enumerate(chunk_iter):
            print(f"=== {i} ===")
            print(f"chunk.text:\n{f'{chunk.text[:300]}…'!r}")

            enriched_text = chunker.contextualize(chunk=chunk)
            print(f"chunker.contextualize(chunk):\n{f'{enriched_text[:300]}…'!r}")

            print()

    finally:
        # 清理其他可能的资源...
        pass


if __name__ == '__main__':
    main()
