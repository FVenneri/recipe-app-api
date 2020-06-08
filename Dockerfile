FROM python:3.7-alpine
# FROM python:3.7-buster
MAINTAINER FVenneri

ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /requirements.txt
RUN apk add --update --no-cache postgresql-client
RUN apk add --update --no-cache --virtual .tmp-build-depl \
        gcc libc-dev linux-headers postgresql-dev
RUN pip install -r /requirements.txt
RUN apk del .tmp-build-depl

RUN mkdir /app
WORKDIR /app
COPY ./app /app

RUN adduser -D user
USER user

