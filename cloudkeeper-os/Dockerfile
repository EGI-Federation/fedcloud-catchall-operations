FROM centos:7

RUN yum install -y centos-release-openstack-stein vim
# moved to different location as repos are not fully functional
RUN curl http://appdb.egi.eu:9009/api/repofiles/index.php?id=1141 > /etc/yum.repos.d/cloudkeeper.repo
RUN yum install -y cloudkeeper-os

RUN mkdir -p /etc/cloudkeeper-os/ \
             /var/spool/cloudkeeper/images

COPY cloudkeeper-os.conf /etc/cloudkeeper-os/cloudkeeper-os.conf
COPY mapping.json /etc/cloudkeeper-os/mapping.json

# Patch the cloudkeeper-os
COPY openstack_client.py /usr/lib/python2.7/site-packages/cloudkeeper_os/openstack_client.py
RUN python -m compileall  /usr/lib/python2.7/site-packages/cloudkeeper_os/openstack_client.py

EXPOSE 50051

CMD ["cloudkeeper-os"]
