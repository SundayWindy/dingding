FROM dcr.ruicore.io/public/python:3.9-bullseye as builder

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN python -m venv /opt/venv
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

# ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

COPY requirements.txt .
COPY ./requirements requirements

RUN pip install -U pip wheel --index-url $PIP_INDEX_URL; \
    pip install -r requirements.txt --index-url $PIP_INDEX_URL

FROM dcr.ruicore.io/public/python:3.9-slim-bullseye


ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY --from=builder /opt/venv /opt/venv
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

COPY . /app
WORKDIR /app

COPY ./scripts /scripts
RUN chmod +x /scripts \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo 'Asia/Shanghai' >/etc/timezone

CMD ["/scripts/entrypoint" ,"/scripts/start"]
