# syntax=docker/dockerfile:1

# FROM python:3.8-slim-buster
FROM public.ecr.aws/lambda/python:3.8

# WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# COPY spotify_35/ spot_tokens.json .
COPY spotify_35/ .

# CMD ["python3", "lambda.py"]
CMD ["lambda.handler"]