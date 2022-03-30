# -*- coding: utf-8 -*-

# Copyright 2017 CNRS and University of Strasbourg
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Keystone helper
"""

import glanceclient.v2.client as glanceclient
from keystoneauth1 import exceptions
from keystoneauth1.identity import v3
from keystoneauth1 import session
from oslo_config import cfg
from oslo_log import log
import webob.exc

CONF = cfg.CONF
LOG = log.getLogger(__name__)

CFG_GROUP = "keystone_authtoken"


def get_session(project_name, domain_name):
    """Get an auth session.
    """
    try:
        # attempt with project_id
        auth_params = dict(CONF[CFG_GROUP])
        auth_params.update(dict(project_id=project_name))
        auth = v3.Password(**auth_params)
        sess = session.Session(auth=auth, verify=False)
        sess.get_token()
    except exceptions.Unauthorized:
        # attempt with project_name
        auth_params = dict(CONF[CFG_GROUP])
        auth_params.update(dict(project_name=project_name,
                                domain_name=domain_name))
        auth = v3.Password(**auth_params)
        sess = session.Session(auth=auth, verify=False)
    return sess


def get_glance_client(project_name, domain_name):
    """Get a glance client
    """
    LOG.debug("Get a glance client for the project: '%s'" % project_name)

    endpoint_type = CONF.endpoint_type
    try:
        sess = get_session(project_name=project_name, domain_name=domain_name)
        if endpoint_type:
            LOG.debug("Glance client is accessing Glance through the "
                      "following endpoint type: %s" % endpoint_type)
            glance_client = glanceclient.Client(
                session=sess, interface=endpoint_type
            )
        else:
            glance_client = glanceclient.Client(session=sess)
    except webob.exc.HTTPForbidden as err:
        LOG.error("Connection to Glance failed.")
        LOG.exception(err)
        return None
    return glance_client
