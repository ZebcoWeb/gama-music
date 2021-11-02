FROM python:3.9.7



ENV TOKEN = unknown
ENV PREFIX = unknown


RUN apt-get update && \
    apt-get install -y -qq libffi-dev libsodium-dev libopus-dev ffmpeg


WORKDIR /music

COPY . .

RUN python -m pip install --upgrade pip && \
    pip install -r req.txt

CMD ["python", "music.py"]