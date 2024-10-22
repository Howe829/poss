import asyncio
import os
from contextlib import asynccontextmanager

import fitz
import magic_pdf.model as model_config
import xoscar as xo
from fastapi import FastAPI, WebSocket
from loguru import logger
from magic_pdf.pipe.UNIPipe import UNIPipe
from magic_pdf.rw.DiskReaderWriter import DiskReaderWriter
from magic_pdf.rw.S3ReaderWriter import S3ReaderWriter
from starlette.websockets import WebSocketDisconnect

from settings import StorageType, settings

model_config.__use_inside_model__ = True

ACTORS = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    await xo.create_actor_pool(address=settings.XOSCAR_ADDRESS, n_process=settings.XOSCAR_ACTORS)
    pool_config = await xo.get_pool_config(settings.XOSCAR_ADDRESS)
    pool_addresses = pool_config.get_external_addresses()
    for i, address in enumerate(pool_addresses):
        actor = await xo.create_actor(
            PDFOscarActor,
            address=address,
            uid=str(i),
        )
        ACTORS.append(actor)

    yield

    for actor in ACTORS:
        await xo.destroy_actor(actor)


app = FastAPI(lifespan=lifespan)


class PDFOscarActor(xo.Actor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._available = True

    @classmethod
    def get_image_writer(cls):
        if settings.STORAGE == StorageType.LOCAL:
            return DiskReaderWriter(settings.IMAGE_DIR)
        return S3ReaderWriter(
            settings.MINIO_ACCESS_KEY,
            settings.MINIO_SECRET_KEY,
            settings.minio_endpoint_url,
            parent_path=f"s3://{settings.MINIO_BUCKET}/",
        )

    @classmethod
    def _get_img_parent_path(cls):
        if settings.STORAGE == StorageType.LOCAL:
            return str(os.path.basename(settings.IMAGE_DIR))
        return f"{settings.MINIO_ENDPOINT}"

    @classmethod
    async def convert_pdf_to_md(cls, pdf_bytes):
        jso_useful_key = {"_pdf_type": "", "model_list": []}
        image_writer = cls.get_image_writer()
        pipe = UNIPipe(pdf_bytes, jso_useful_key, image_writer)
        pipe.pipe_classify()
        pipe.pipe_analyze()
        pipe.pipe_parse()
        img_parent_path = cls._get_img_parent_path()
        md_content: str = pipe.pipe_mk_markdown(img_parent_path, drop_mode="none")

        return md_content

    def available(self):
        return self._available

    async def serve(self, websocket: WebSocket):
        self._available = False

        while True:
            try:
                page_data = await websocket.receive_bytes()
                if not page_data:
                    break

                doc = fitz.open("pdf", page_data)
                text = await self.convert_pdf_to_md(doc.tobytes())
                await websocket.send_text(text)

            except WebSocketDisconnect:
                logger.info("Connection <{}:{}> closed", websocket.client.host, websocket.client.port)
                break
            except Exception as e:
                logger.exception("Unknown Error: {}", e)
                break

        self._available = True


@app.websocket("/ws")
async def stage(websocket: WebSocket):
    await websocket.accept()
    while True:
        for actor in ACTORS:
            if await actor.available():
                await actor.serve(websocket)
                return
        await asyncio.sleep(1)
