FROM python:3.8

RUN apt-get update \
    && apt-get -qy install --fix-missing curl \
    && curl -L http://repository.egi.eu/sw/production/cas/1/current/repo-files/egi-trustanchors.list > /etc/apt/sources.list.d/egi-trustanchors.list \
    && curl https://dl.igtf.net/distribution/igtf/current/GPG-KEY-EUGridPMA-RPM-3 | apt-key add - \
    && apt-get update \
    && apt-get -qy install --fix-missing \
       ca-policy-egi-core \
       fetch-crl \
    && apt-get clean autoclean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/*.deb

RUN fetch-crl -p 2 -T 30 || exit 0

RUN cd /usr/local/share/ca-certificates \
    && for f in /etc/grid-security/certificates/*.pem ; do ln -s $f $(basename $f .pem).crt; done \
    && update-ca-certificates

# CMD packages for 1.4.3 are missing, so going for pip instead
# Using version 2.1.1
ARG CASO_VERSION=2.1.1

RUN pip install git+https://github.com/IFCA/caso.git@$CASO_VERSION

RUN mkdir -p /var/spool/caso
COPY caso.conf /etc/caso/caso.conf
COPY voms.json /etc/caso/voms.json

CMD ["/usr/local/bin/caso-extract"]
