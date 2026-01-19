##################################################
# Stage 1 - Build python venv
##################################################
FROM python:3 AS build

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3015, DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gnupg2 curl git \
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

WORKDIR /fedcloud_catchall

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock /fedcloud_catchall/

RUN uv pip compile pyproject.toml -o requirements.txt

RUN python -m venv /fedcloud_catchall/venv  \
    && /fedcloud_catchall/venv/bin/pip install --no-cache-dir -r requirements.txt \
    && cat /etc/grid-security/certificates/*.pem >> "$(/fedcloud_catchall/venv/bin/python -m requests.certs)"

COPY . /fedcloud_catchall
RUN /fedcloud_catchall/venv/bin/pip install --no-cache-dir .

##################################################
# Stage 2 - take venv and install needed packages
##################################################
FROM python:3-slim

LABEL org.opencontainers.image.source=https://github.com/EGI-Federation/fedcloud-catchall-operations

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3015, DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       jq rclone qemu-utils \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /fedcloud_catchall \
    && groupadd -g 1999 python \
    && useradd -m -r -u 1999 -g python python \
    && chown -R python:python /fedcloud_catchall

WORKDIR /fedcloud_catchall

# All the python code from the build image above
COPY --chown=python:python --from=build /fedcloud_catchall/venv ./venv
COPY --chown=python:python --from=build /fedcloud /fedcloud

# Add the script that call the cloud-info-provider as needed for the site
# these create the configuration for the site by discovering the available
# projects for the credentials and will upload the output to S3
COPY publisher.sh /usr/local/bin/publisher.sh

ENV PATH="/fedcloud_catchall/venv/bin:$PATH"

USER 1999
