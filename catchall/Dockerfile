# The actual image
FROM python:3-slim

LABEL org.opencontainers.image.source=https://github.com/EGI-Federation/fedcloud-catchall-operations

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3015, DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gnupg2 qemu-utils curl git \
    && curl -s https://dist.eugridpma.info/distribution/igtf/current/GPG-KEY-EUGridPMA-RPM-4 \
	| gpg --dearmor  -o /etc/apt/keyrings/eugridpma.gpg  \
    && echo "deb [signed-by=/etc/apt/keyrings/eugridpma.gpg] https://repository.egi.eu/sw/production/cas/1/current egi-igtf core" > /etc/apt/sources.list.d/igtf.list \
    && apt-get update \
    && apt-get install -y ca-policy-egi-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /image-sync

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN groupadd -g 1999 python \
    && useradd -m -r -u 1999 -g python python \
    && chown python:python /image-sync

USER 1999

COPY --chown=python:python . /image-sync

RUN uv sync --locked

RUN cat /etc/grid-security/certificates/*.pem >> "$(uv run python -m requests.certs)"

CMD ["uv", "run", "image-sync"]
