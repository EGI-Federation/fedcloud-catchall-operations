FROM python:3 AS build

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3008
RUN curl -s https://dist.eugridpma.info/distribution/igtf/current/GPG-KEY-EUGridPMA-RPM-3 \
	| apt-key add - \
    && echo "deb https://repository.egi.eu/sw/production/cas/1/current egi-igtf core" > /etc/apt/sources.list.d/igtf.list \
    && apt-get update \
    && apt-get install -y ca-policy-egi-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /cloud-info

RUN python -m venv /cloud-info/venv
ENV PATH="/cloud-info/venv/bin:$PATH"

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && cat /etc/grid-security/certificates/*.pem >> "$(python -m requests.certs)"

COPY . .

RUN pip install --no-cache-dir .

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
