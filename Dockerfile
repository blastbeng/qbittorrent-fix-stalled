FROM python:3.9-slim-bullseye

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
         locales \
         git \
         build-essential \
         gcc

RUN sed -i '/it_IT.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen
ENV LANG it_IT.UTF-8  
ENV LANGUAGE it_IT:it  
ENV LC_ALL it_IT.UTF-8

RUN pip3 install --no-cache --upgrade pip setuptools

COPY requirements.txt .

RUN pip3 install -r requirements.txt

WORKDIR /app

COPY main.py .
COPY utils.py .
COPY config.py .
COPY entrypoint.sh .
COPY custom_autoremove_logger.py /usr/local/lib/python3.9/site-packages/autoremovetorrents/logger.py
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
