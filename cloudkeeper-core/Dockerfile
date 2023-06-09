FROM ruby:2.6

LABEL org.opencontainers.image.source=https://github.com/EGI-Federation/fedcloud-catchall-operations

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# We do need install recommends for the CAs
# hadolint ignore=DL3015, DL3008
RUN apt-get update \
    && apt-get -qy install --fix-missing --no-install-recommends curl qemu-utils \
    && curl https://dl.igtf.net/distribution/igtf/current/GPG-KEY-EUGridPMA-RPM-3 | apt-key add - \
    && echo 'deb https://egi-igtf.ndpf.info/distribution/egi-1.120-1b/current egi-igtf core' \
             > /etc/apt/sources.list.d/cas.list \
    && apt-get update \
    && apt-get -qy install --fix-missing fetch-crl \
    && apt-get -qy install --fix-missing ca-policy-egi-core \
    && apt-get clean autoclean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/*.deb

RUN fetch-crl -p 2 -T 30 || exit 0

RUN gem install cloudkeeper -v 1.7.1

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY image-lists.conf /etc/cloudkeeper/image-lists.conf
COPY cloudkeeper.yml /etc/cloudkeeper/cloudkeeper.yml

RUN mkdir -p /var/log/cloudkeeper \
             /var/lock/cloudkeeper \
             /var/spool/cloudkeeper/images

ENTRYPOINT ["/entrypoint.sh"]
CMD ["cloudkeeper", "sync"]
