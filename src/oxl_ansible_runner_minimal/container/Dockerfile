FROM python:3.14-alpine AS aw

ARG AR_UID=1000
ARG AW_USER=ar

RUN apk add --update --no-cache git git-lfs openssh-client sshpass && \
    pip install --no-cache-dir --upgrade pip 2>/dev/null && \
    pip install ansible-core && \
    adduser --uid ${AR_UID} --home /home/ansible-runner --shell /usr/sbin/nologin --disabled-password ${AR_USER} ${AR_USER} && \
    chown -R ${AR_USER}:${AR_USER} /play

ENV PYTHONUNBUFFERED=1

USER ${AR_USER}
