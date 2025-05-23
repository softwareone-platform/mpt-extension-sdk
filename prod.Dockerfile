FROM python:3.12.2-slim-bookworm
ENV PYTHONUNBUFFERED=1 POETRY_VERSION=1.7.0

RUN pip3 install poetry==$POETRY_VERSION

WORKDIR /extension_sdk

ADD . /extension_sdk

RUN poetry update && poetry install

CMD ["swoext"]
