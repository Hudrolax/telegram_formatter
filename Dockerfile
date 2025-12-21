#####################################################################
# ---------------- STAGE 1 : builder --------------------------------
#####################################################################
FROM python:3.13.4-alpine3.22 AS builder

ENV PYTHONUNBUFFERED=1

RUN apk add --no-cache --virtual .build-deps \
      build-base \
      linux-headers \
      python3-dev \
      libffi-dev \
      pkgconf

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

WORKDIR /build
COPY pyproject.toml README.md ./
COPY app ./app

ARG DEV=false
RUN pip install --upgrade pip && \
    if [ "$DEV" = "true" ] ; then \
      pip install --no-cache-dir .[dev] ; \
    else \
      pip install --no-cache-dir . ; \
    fi

#####################################################################
# ---------------- STAGE 2 : runtime --------------------------------
#####################################################################
FROM python:3.13.4-alpine3.22

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

COPY --from=builder /venv /venv

COPY app /app
COPY scripts /scripts
RUN chmod -R +x /scripts

WORKDIR /app
ENV PATH="/scripts:/venv/bin:$PATH"
RUN adduser --disabled-password --no-create-home www
USER www

EXPOSE 9000
CMD ["run.sh"]
