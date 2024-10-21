# POSS:PDF OCR Stream Server
![img.png](img.png)
POSS is a server designed for efficient, real-time OCR processing of PDF files. By streaming each page, it enables on-the-fly text extraction and processing, making it ideal for applications requiring quick and continuous handling of PDF documents. POSS leverages powerful OCR tools to handle both text and image-based PDFs, providing accurate and structured text outputs, page by page, as the files are processed. Perfect for integration into document workflows, POSS is lightweight, flexible, and built with scalability in mind.

## Install
poss uses poetry to manage the dependencies
```shell
curl -sSL https://install.python-poetry.org | python3 -
```

```shell
poetry insall
poetry run pip install magic-pdf[full] --extra-index-url  https://wheels.myhloli.com
```

## Run server
```shell
python server.py
```

## Use client
Please refer the [client.py](client.py) for how to send pdf files to the server.

## Todo
- [ ] Use docker to deploy
- [ ] LocalImageWriter
- [ ] Interactive web page

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
