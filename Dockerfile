ARG PYTHON_VERSION=3.12.4
FROM docker-proxy.kontur.host/python:${PYTHON_VERSION}-slim AS base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY /src src

COPY requirements.txt .

COPY alembic.ini .

RUN apt-get update && apt-get install -y locales

RUN dpkg-reconfigure locales && locale-gen C.UTF-8 && /usr/sbin/update-locale LANG=C.UTF-8

RUN echo 'ru_RU.UTF-8 UTF-8' >> /etc/locale.gen && locale-gen

ENV LC_ALL ru_RU.UTF-8

RUN python -m pip install -r requirements.txt

EXPOSE 8080

CMD python -m alembic upgrade head && cd src && python -m main
