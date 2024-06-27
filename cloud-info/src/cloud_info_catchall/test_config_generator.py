""" Tests for the config generator """

import unittest
from collections import defaultdict
from unittest.mock import patch

import cloud_info_catchall.config_generator as cg


class ConfigGeneratorTest(unittest.TestCase):
    @patch("cloud_info_catchall.config_generator.generate_shares")
    def test_generate_shares_config(self, m_gen):
        config = {"site_name": "SITE"}
        secrets = {}
        r = cg.generate_shares_config(config, secrets)
        m_gen.assert_called_with(config, secrets)
        self.assertEqual(
            r, {"site": {"name": "SITE"}, "compute": {"shares": m_gen.return_value}}
        )

    def test_generate_empty_shares(self):
        with self.assertRaises(Exception):
            cg.generate_shares({}, {})

    @patch("cloud_info_catchall.share_discovery.ShareDiscovery.get_token_shares")
    def test_generate_shares(self, m_token_shares):
        refresh_secret = {
            "foo": {
                "client_id": "id",
                "client_secret": "secret",
                "refresh_token": "refresh",
            }
        }
        token_secret = {"bar": {"access_token": "token"}}
        secrets = {}
        secrets.update(refresh_secret)
        secrets.update(token_secret)
        m_token_shares.return_value = {"one": "two"}
        r = cg.generate_shares(defaultdict(lambda: ""), secrets)
        m_token_shares.assert_called_with()
        self.assertEqual(r, {"one": "two"})


if __name__ == "__main__":
    unittest.main()
