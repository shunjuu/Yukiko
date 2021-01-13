#FROM nikolaik/python-nodejs:latest
FROM python:3.8-slim

LABEL maintainer="Kyrielight"

ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update -y && \
    apt-get install -y git unzip curl aria2 && \
    curl 'https://rclone.org/install.sh' | bash

#RUN npm install webtorrent-cli -g

COPY requirements.txt /opt/requirements.txt
RUN pip3 install -r /opt/requirements.txt && rm /opt/requirements.txt

COPY *.py /izumi/

ENTRYPOINT ["python3", "/izumi/bittorrent.py"]
