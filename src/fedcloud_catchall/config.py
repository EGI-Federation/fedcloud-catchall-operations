"""
Configuration for the tools
"""

from oslo_config import cfg

# Configuration
CONF = cfg.CONF
CONF.register_opts(
    [
        cfg.StrOpt("site_config_dir", default="."),
        cfg.StrOpt("fedcloud_info_system_url", default="https://is.cloud.egi.eu"),
    ],
    group="discovery",
)

CONF.register_opts(
    [
        cfg.StrOpt("client_id"),
        cfg.StrOpt("client_secret"),
        cfg.StrOpt(
            "scopes", default="openid profile eduperson_entitlement entitlements email"
        ),
        cfg.StrOpt(
            "discovery_endpoint",
            default="https://aai.egi.eu/auth/realms/egi/.well-known/openid-configuration",
        ),
        cfg.IntOpt("access_token_ttl", default=20 * 60),
    ],
    group="checkin",
)


# Registry configuration
CONF.register_opts(
    [
        cfg.StrOpt("registry_base_url", default="https://registry.egi.eu"),
        cfg.StrOpt("registry_host", default="registry.egi.eu"),
        cfg.StrOpt("registry_project", default="egi_vm_images"),
        cfg.ListOpt("formats", default=[]),
        cfg.StrOpt("registry_user"),
        cfg.StrOpt("registry_password"),
    ],
    group="sync",
)


# Accounting configuration
CONF.register_opts(
    [
        cfg.StrOpt("spool_dir", default="/var/spool/egi"),
        cfg.BoolOpt("force_run", default=False),
    ],
    group="accounting",
)
