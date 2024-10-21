from minio import Minio
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MINIO_ACCESS_KEY: str
    MINIO_BUCKET: str
    MINIO_SECRET_KEY: str
    MINIO_ENDPOINT: str
    MINIO_SECURE: bool
    SERVER_PORT: int
    SERVER_IP: str
    XOSCAR_ACTORS: int
    XOSCAR_ADDRESS: str

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

    @property
    def minio_endpoint_url(self):
        url_prefix = "http://"
        if self.MINIO_SECURE is True:
            url_prefix = "https://"
        return f"{url_prefix}{self.MINIO_ENDPOINT}"



settings = Settings()

minio_client = Minio(
    endpoint=settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE
)
