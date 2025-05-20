FROM python:3 AS build

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /image-sync

RUN python -m venv /image-sync/venv
ENV PATH="/image-sync/venv/bin:$PATH"

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN pip install --no-cache-dir .

# The actual image
FROM python:3-slim

LABEL org.opencontainers.image.source=https://github.com/EGI-Federation/fedcloud-catchall-operations

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3015, DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gnupg2 qemu-utils curl \
    && curl -s https://dist.eugridpma.info/distribution/igtf/current/GPG-KEY-EUGridPMA-RPM-4 \
	| apt-key add - \
    && echo "deb https://repository.egi.eu/sw/production/cas/1/current egi-igtf core" > /etc/apt/sources.list.d/igtf.list \
    && apt-get update \
    && apt-get install -y ca-policy-egi-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /image-sync

RUN groupadd -g 1999 python \
    && useradd -r -u 1999 -g python python

COPY --chown=python:python --from=build /image-sync/venv ./venv

RUN cat /etc/grid-security/certificates/*.pem >> "$(/image-sync/venv/bin/python -m requests.certs)"

USER 1999

ENV PATH="/image-sync/venv/bin:$PATH"
CMD ["image-sync"]
