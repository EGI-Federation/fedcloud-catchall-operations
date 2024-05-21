FROM python:3

LABEL org.opencontainers.image.source=https://github.com/EGI-Federation/fedcloud-catchall-operations

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN mkdir /cloud-info
COPY requirements.txt /cloud-info/requirements.txt
RUN pip install --no-cache-dir -r /cloud-info/requirements.txt

# CA certificates: install and add to python
# hadolint ignore=DL3015, DL3008
RUN curl -Ls \
        https://dist.eugridpma.info/distribution/igtf/current/GPG-KEY-EUGridPMA-RPM-3 \
        | apt-key add - \
    && echo 'deb https://repository.egi.eu/sw/production/cas/1/current egi-igtf core' \
        > /etc/apt/sources.list.d/cas.list \
    && apt-get update \
    && apt-get install -y jq rclone \
    && apt-get install -y ca-policy-egi-core \
    && rm -rf /var/lib/apt/lists/* \
    && cat /etc/grid-security/certificates/*.pem >> "$(python -m requests.certs)"


COPY . /cloud-info/
RUN pip install --no-cache-dir /cloud-info

COPY ams-wrapper.sh /usr/local/bin/ams-wrapper.sh
COPY publisher.sh /usr/local/bin/publisher.sh
COPY openstack.rc /etc/cloud-info-provider/openstack.rc
COPY openstack.yaml /etc/cloud-info-provider/openstack.yaml

CMD ["publisher.sh"]
