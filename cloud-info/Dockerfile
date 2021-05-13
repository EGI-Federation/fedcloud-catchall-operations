FROM python:3

ARG CLOUD_INFO_VERSION=0e205683d144437d47f0e962ee453211b6768020

# hadolint ignore=DL3013
RUN pip install --no-cache-dir \
        "git+https://github.com/EGI-Federation/cloud-info-provider.git@$CLOUD_INFO_VERSION" \
        python-glanceclient python-novaclient python-keystoneclient keystoneauth1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

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

COPY ams-wrapper.sh /usr/local/bin/ams-wrapper.sh
COPY publisher.sh /usr/local/bin/publisher.sh

CMD ["publisher.sh"]
