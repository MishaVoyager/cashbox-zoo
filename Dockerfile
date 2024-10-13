ARG PYTHON_VERSION=3.12.4
FROM docker-proxy.kontur.host/python:${PYTHON_VERSION}-slim as base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY /src src

COPY requirements.txt .

COPY alembic.ini .

RUN python -m pip install -r requirements.txt

EXPOSE 8080

CMD python -m alembic upgrade head && cd src && python -m main
