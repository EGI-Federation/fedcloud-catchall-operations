FROM python:3 AS build

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gnupg2 curl \
    && curl -s https://dist.eugridpma.info/distribution/igtf/current/GPG-KEY-EUGridPMA-RPM-4 \
	| gpg --dearmor  -o /etc/apt/keyrings/eugridpma.gpg  \
    && echo "deb [signed-by=/etc/apt/keyrings/eugridpma.gpg] https://repository.egi.eu/sw/production/cas/1/current egi-igtf core" > /etc/apt/sources.list.d/igtf.list \
    && apt-get update \
    && apt-get install -y ca-policy-egi-core \
    && rm -rf /var/lib/apt/lists/*

# Fedcloud client is pinning dependencies strictly so it does not play
# very well with the rest of the available venv. Installing on its own
RUN python -m venv /fedcloud && \
    /fedcloud/bin/pip install --no-cache-dir fedcloudclient

WORKDIR /cloud-info

COPY requirements.txt .

RUN python -m venv /cloud-info/venv
ENV PATH="/cloud-info/venv/bin:$PATH"

RUN pip install --no-cache-dir -r requirements.txt \
    && cat /etc/grid-security/certificates/*.pem >> "$(python -m requests.certs)"

COPY . .

RUN pip install --no-cache-dir .

# A second cloud-info-provider!
RUN python -m venv /cloud-info-json \
    && /cloud-info-json/bin/pip install --no-cache-dir \
         git+https://github.com/EGI-Federation/cloud-info-provider.git@88c3a14d1e11c1adf9a03c85679cdcc8e3a2ede1 \
    && cat /etc/grid-security/certificates/*.pem >> "$(/cloud-info-json/bin/python -m requests.certs)"

# The actual image
FROM python:3

LABEL org.opencontainers.image.source=https://github.com/EGI-Federation/fedcloud-catchall-operations

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3015, DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       jq rclone \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /cloud-info \
    && groupadd -g 1999 python \
    && useradd -r -u 1999 -g python python \
    && chown -R python:python /cloud-info

WORKDIR /cloud-info

# All the python code from the build image above
COPY --chown=python:python --from=build /cloud-info/venv ./venv
COPY --chown=python:python --from=build /fedcloud /fedcloud
COPY --chown=python:python --from=build /cloud-info-json /cloud-info-json

# Add the scripts that call the cloud-info-provider as needed for the site
# these create the configuration for the site by discovering the available
# projects for the credentials and will send the output to the AMS queue and
# upload to S3
COPY ams-wrapper.sh /usr/local/bin/ams-wrapper.sh
COPY publisher.sh /usr/local/bin/publisher.sh
# These are sample configuration files for cloud-info-provider that can be used
# if the container is used outside of the catchall-operations as described in
# https://docs.egi.eu/providers/cloud-compute/openstack/cloud-info/#local-operations
COPY openstack.rc /etc/cloud-info-provider/openstack.rc
COPY openstack.yaml /etc/cloud-info-provider/openstack.yaml

USER 1999

ENV PATH="/cloud-info/venv/bin:$PATH"
CMD ["publisher.sh"]
