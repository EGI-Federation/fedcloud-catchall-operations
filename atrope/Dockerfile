FROM python:3.11-slim as build

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
               build-essential gcc git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /atrope
RUN python -m venv /atrope/venv
ENV PATH="/atrope/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN pip install --no-cache-dir .

FROM python:3.11-slim

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3015, DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
                curl gnupg2 qemu-utils \
    && curl -s \
    https://dist.eugridpma.info/distribution/igtf/current/GPG-KEY-EUGridPMA-RPM-3 \
    | apt-key add - \
    && echo "deb https://repository.egi.eu/sw/production/cas/1/current egi-igtf core" > /etc/apt/sources.list.d/igtf.list \
    && apt-get update \
    && apt-get install -y ca-policy-egi-core \
    && rm -rf /var/lib/apt/lists/* \
    && cat /etc/grid-security/certificates/*.pem >> "$(python -m requests.certs)"

WORKDIR /atrope

RUN groupadd -g 1999 python && \
    useradd -r -u 1999 -g python python

COPY --chown=python:python --from=build /atrope/venv ./venv

USER 1999

ENV PATH="/atrope/venv/bin:$PATH"
CMD ["sites-sync"]
