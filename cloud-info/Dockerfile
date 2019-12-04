FROM python:2

# Pip install directly does not install the data files in etc?
# TODO: pin the cloud-info-provider version
RUN git clone https://github.com/enolfc/cloud-info-provider.git /tmp/cloud-info-provider && \
    cd /tmp/cloud-info-provider && git checkout ams && \
    pip install -r /tmp/cloud-info-provider/requirements.txt && \
    cd /tmp/cloud-info-provider && python setup.py install && \
    rm -rf /tmp/cloud-info-provider

# OpenStack should be a different cloud-info-provider package...
RUN pip install python-keystoneclient \
                python-novaclient \
                python-glanceclient \
                keystoneauth1

RUN pip install git+https://github.com/enolfc/ams-clipw.git@patch-1

RUN curl -Ls \
        https://dist.eugridpma.info/distribution/igtf/current/GPG-KEY-EUGridPMA-RPM-3 \
        | apt-key add - \
    && echo 'deb http://repository.egi.eu/sw/production/cas/1/current egi-igtf core' \
        > /etc/apt/sources.list.d/cas.list \
    && apt-get update \
    && apt-get install -y jq ca-policy-egi-core \
    && rm -rf /var/lib/apt/lists/*

RUN cat /etc/grid-security/certificates/*.pem >> $(python -m requests.certs)

COPY cloud-info-wrapper.sh /usr/local/bin/cloud-info-wrapper.sh
COPY ams-wrapper.sh /usr/local/bin/ams-wrapper.sh
COPY publisher.sh /usr/local/bin/publisher.sh

CMD ["publisher.sh"]

