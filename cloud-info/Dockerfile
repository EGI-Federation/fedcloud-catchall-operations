FROM python:3

LABEL org.opencontainers.image.source=https://github.com/EGI-Federation/fedcloud-catchall-operations

ARG CLOUD_INFO_VERSION=f6f6a2e265cc9608d791f31a8ef2903302ca33f6

# hadolint ignore=DL3013
RUN pip install --no-cache-dir \
        "git+https://github.com/EGI-Federation/cloud-info-provider.git@$CLOUD_INFO_VERSION" \
        "git+https://github.com/ARGOeu/argo-ams-library@devel" \
        python-glanceclient python-novaclient python-keystoneclient keystoneauth1 yq \
	fedcloudclient


SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# CA certificates: install and add to python
# hadolint ignore=DL3015, DL3008
RUN curl -Ls \
        https://dist.eugridpma.info/distribution/igtf/current/GPG-KEY-EUGridPMA-RPM-3 \
        | apt-key add - \
    && echo 'deb https://egi-igtf.ndpf.info/distribution/egi-1.120-1b/current egi-igtf core' \
        > /etc/apt/sources.list.d/cas.list \
    && apt-get update \
    && apt-get install -y jq \
    && apt-get install -y ca-policy-egi-core \
    && rm -rf /var/lib/apt/lists/* \
    && cat /etc/grid-security/certificates/*.pem >> "$(python -m requests.certs)"

COPY ams-wrapper.sh /usr/local/bin/ams-wrapper.sh
COPY publisher.sh /usr/local/bin/publisher.sh
COPY openstack.rc /etc/cloud-info-provider/openstack.rc
COPY openstack.yaml /etc/cloud-info-provider/openstack.yaml
COPY config_generator.py /usr/local/bin/config_generator.py

CMD ["publisher.sh"]
