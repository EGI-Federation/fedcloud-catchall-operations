FROM python:3

LABEL org.opencontainers.image.source=https://github.com/EGI-Federation/fedcloud-catchall-operations

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# We do need install recommends for the CAs
# hadolint ignore=DL3015, DL3008
RUN apt-get update \
    && apt-get -qy install --fix-missing --no-install-recommends curl \
    && curl https://dl.igtf.net/distribution/igtf/current/GPG-KEY-EUGridPMA-RPM-3 | apt-key add - \
    && echo 'deb http://repository.egi.eu/sw/production/cas/1/current egi-igtf core' \
             > /etc/apt/sources.list.d/cas.list \
    && apt-get update \
    && apt-get -qy install --fix-missing fetch-crl \
    && apt-get -qy install --fix-missing ca-policy-egi-core \
    && apt-get clean autoclean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/*.deb

RUN fetch-crl -p 2 -T 30 || exit 0

RUN for f in /etc/grid-security/certificates/*.pem ; do \
	ln -s "$f" "/usr/local/share/ca-certificates/$(basename "$f" .pem).crt"; \
    done \
    && update-ca-certificates


# New CMD packages are missing, so going for pip instead
# Version 3.0.0 is broken in the dates management
ARG CASO_VERSION=4.2.0

# Pydantic v2 will fail
RUN pip install --no-cache-dir git+https://github.com/IFCA/caso.git@$CASO_VERSION \
	pydantic~=1.10

COPY caso.conf /etc/caso/caso.conf
COPY voms.json /etc/caso/voms.json

RUN mkdir -p /var/spool/caso

CMD ["/usr/local/bin/caso-extract"]
