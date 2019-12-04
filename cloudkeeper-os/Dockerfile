FROM python:3.7

# install poetry so cloudkeeper can be installed
RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

RUN . $HOME/.poetry/env \
    && git clone --recurse-submodules git://github.com/enolfc/cloudkeeper-os.git /tmp/cloudkeeper-os \
    && cd /tmp/cloudkeeper-os \
    && git checkout project_id \
    && poetry build \
    && pip install dist/cloudkeeper-os-2.0.0.tar.gz \
    && pip install protobuf

RUN curl -Ls \
        https://dist.eugridpma.info/distribution/igtf/current/GPG-KEY-EUGridPMA-RPM-3 \
        | apt-key add - \
    && echo 'deb http://repository.egi.eu/sw/production/cas/1/current egi-igtf core' \
        > /etc/apt/sources.list.d/cas.list \
    && apt-get update \
    && apt-get install -y jq ca-policy-egi-core \
    && rm -rf /var/lib/apt/lists/* \
    && cat /etc/grid-security/certificates/*.pem >> $(python -m requests.certs)

CMD ["cloudkeeper-os"]
