FROM ghcr.io/nesquena/hermes-webui:latest

USER root

ENV PATH="/root/.local/bin:/usr/local/bin:${PATH}"

RUN curl -fsSL https://astral.sh/uv/install.sh | sh \
    && curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash \
    && curl -fsSL https://get-hermes.ai/install.sh | bash

COPY scripts/cf-proxy.py /opt/hermes/cf-proxy.py
RUN chmod 0755 /opt/hermes/cf-proxy.py

WORKDIR /workspace
