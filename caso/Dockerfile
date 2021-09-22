FROM python:3

ARG CASO_VERSION=2.1.1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN mkdir -p /var/spool/caso && \
    mkdir -p /etc/caso/

COPY caso.conf /etc/caso/caso.conf
COPY voms.json /etc/caso/voms.json

RUN pip install --no-cache-dir git+https://github.com/IFCA/caso.git@$CASO_VERSION

# CA certificates: install and add to python
# hadolint ignore=DL3015, DL3008
RUN curl -Ls \
        https://dist.eugridpma.info/distribution/igtf/current/GPG-KEY-EUGridPMA-RPM-3 \
        | apt-key add - \
    && echo 'deb http://repository.egi.eu/sw/production/cas/1/current egi-igtf core' \
        > /etc/apt/sources.list.d/cas.list \
    && apt-get update \
    && apt-get install -y jq ca-policy-egi-core \
    && rm -rf /var/lib/apt/lists/* \
    && cat /etc/grid-security/certificates/*.pem >> "$(python -m requests.certs)"



CMD ["/usr/local/bin/caso-extract"]
