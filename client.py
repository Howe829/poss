import asyncio
import time

import fitz
import websockets
from loguru import logger


async def ocr_pdf_page_by_page():
    uri = "ws://localhost:8765"
    file_path = "your-pdf.pdf"

    async with websockets.connect(uri) as websocket:
        start_time = time.perf_counter()
        doc = fitz.open(file_path)

        for page_num in range(doc.page_count):
            tmp_doc = fitz.open()
            tmp_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

            await websocket.send(tmp_doc.tobytes())
            logger.info("Page: %s sent", page_num)
            text = await websocket.recv()
            logger.info("Page <%s> content: \n %s", page_num, text)

        await websocket.close()
        end_time = time.perf_counter()
        logger.info("Elapsed: %s\n", end_time - start_time)


if __name__ == "__main__":
    asyncio.run(ocr_pdf_page_by_page())
