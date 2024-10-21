import asyncio
from datetime import timedelta

import fitz
import xoscar as xo

import re

from loguru import logger
from fastapi import FastAPI, WebSocket
from contextlib import asynccontextmanager

from magic_pdf.pipe.UNIPipe import UNIPipe
import magic_pdf.model as model_config

from magic_pdf.rw.S3ReaderWriter import S3ReaderWriter
from starlette.websockets import WebSocketDisconnect

from settings import settings, minio_client

model_config.__use_inside_model__ = True
pattern = r'!\[\]\(\/([^\s/]+\.\w+)\)'

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
    async def convert_pdf_to_md(cls, pdf_bytes):

        jso_useful_key = {"_pdf_type": "", "model_list": []}

        image_dir = f's3://{settings.MINIO_BUCKET}/'
        s3image_cli = S3ReaderWriter(
            settings.MINIO_ACCESS_KEY,
            settings.MINIO_SECRET_KEY,
            settings.minio_endpoint_url,
            parent_path=image_dir
        )

        pipe = UNIPipe(pdf_bytes, jso_useful_key, s3image_cli)
        pipe.pipe_classify()
        pipe.pipe_analyze()
        pipe.pipe_parse()
        md_content: str = pipe.pipe_mk_markdown("", drop_mode="none")

        # generate preview url
        matches = re.findall(pattern, md_content)
        for filename in matches:
            signed_url = minio_client.presigned_get_object(settings.MINIO_BUCKET, filename, expires=timedelta(days=1780))
            logger.info("SIGNED URL: {}", signed_url)
            md_content = md_content.replace(filename, signed_url)

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
