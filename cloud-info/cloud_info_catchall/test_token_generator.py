""" Tests for the config generator """

import unittest

from collections import defaultdict
from unittest.mock import call, patch

import cloud_info_catchall.token_generator as tg
import jwt
import responses
from responses import matchers


class TokenGeneratorTest(unittest.TestCase):
    @responses.activate
    def test_get_access_token(self):
        token_url = "https://example.com"
        scopes = "a b c"
        secret = {"client_id": "id", "client_secret": "secret"}
        responses.post(
            token_url,
            json={"access_token": "foo"},
            match=[
                matchers.urlencoded_params_matcher(
                    {
                        "grant_type": "client_credentials",
                        "client_id": "id",
                        "client_secret": "secret",
                        "scope": "a b c",
                    }
                )
            ],
        )
        self.assertEqual(tg.get_access_token(token_url, scopes, secret), "foo")

    def test_valid_token_no_token(self):
        self.assertEqual(tg.valid_token(None, None, None), False)

    @patch("jwt.algorithms.RSAAlgorithm.from_jwk")
    @patch("jwt.get_unverified_header")
    @patch("jwt.decode")
    @patch("calendar.timegm")
    def test_valid_token_within_time(
        self, m_calendar, m_jwt_decode, m_jwt_header, m_jwt_alg
    ):
        oidc_config = {"jwks_uri": "https://example.com"}
        m_jwt_header.return_value = {"kid": "123", "alg": "bar"}
        m_jwt_decode.return_value = {"exp": 10}
        m_calendar.return_value = 8
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET, "https://example.com", json={"keys": [{"kid": "123"}]}
            )
            self.assertEqual(tg.valid_token("foo", oidc_config, 1), True)
        m_jwt_header.assert_called_with("foo")
        m_calendar.assert_called_once()
        m_jwt_alg.assert_called_with('{"kid": "123"}')
        m_jwt_decode.assert_called_with(
            "foo", key=m_jwt_alg.return_value, algorithms=["bar"]
        )

    @patch("jwt.algorithms.RSAAlgorithm.from_jwk")
    @patch("jwt.get_unverified_header")
    @patch("jwt.decode")
    @patch("calendar.timegm")
    def test_valid_token_not_within_time(
        self, m_calendar, m_jwt_decode, m_jwt_header, m_jwt_alg
    ):
        oidc_config = {"jwks_uri": "https://example.com"}
        m_jwt_header.return_value = {"kid": "123", "alg": "bar"}
        m_jwt_decode.return_value = {"exp": 10}
        m_calendar.return_value = 8
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET, "https://example.com", json={"keys": [{"kid": "123"}]}
            )
            self.assertEqual(tg.valid_token("foo", oidc_config, 5), False)
        m_jwt_header.assert_called_with("foo")
        m_calendar.assert_called_once()
        m_jwt_alg.assert_called_with('{"kid": "123"}')
        m_jwt_decode.assert_called_with(
            "foo", key=m_jwt_alg.return_value, algorithms=["bar"]
        )

    @patch("jwt.algorithms.RSAAlgorithm.from_jwk")
    @patch("jwt.get_unverified_header")
    @patch("jwt.decode")
    @patch("calendar.timegm")
    def test_valid_token_decode_exception(
        self, m_calendar, m_jwt_decode, m_jwt_header, m_jwt_alg
    ):
        oidc_config = {"jwks_uri": "https://example.com"}
        m_jwt_header.return_value = {"kid": "123", "alg": "bar"}
        m_jwt_decode.return_value = {"exp": 10}
        m_jwt_decode.side_effect = jwt.DecodeError()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET, "https://example.com", json={"keys": [{"kid": "123"}]}
            )
            self.assertEqual(tg.valid_token("foo", oidc_config, 5), False)
        m_jwt_header.assert_called_with("foo")
        m_calendar.assert_not_called()
        m_jwt_alg.assert_called_with('{"kid": "123"}')
        m_jwt_decode.assert_called_with(
            "foo", key=m_jwt_alg.return_value, algorithms=["bar"]
        )

    @patch("jwt.algorithms.RSAAlgorithm.from_jwk")
    @patch("jwt.get_unverified_header")
    @patch("jwt.decode")
    @patch("calendar.timegm")
    def test_valid_token_expired_exception(
        self, m_calendar, m_jwt_decode, m_jwt_header, m_jwt_alg
    ):
        oidc_config = {"jwks_uri": "https://example.com"}
        m_jwt_header.return_value = {"kid": "123", "alg": "bar"}
        m_jwt_decode.return_value = {"exp": 10}
        m_jwt_decode.side_effect = jwt.ExpiredSignatureError()
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET, "https://example.com", json={"keys": [{"kid": "123"}]}
            )
            self.assertEqual(tg.valid_token("foo", oidc_config, 5), False)
        m_jwt_header.assert_called_with("foo")
        m_calendar.assert_not_called()
        m_jwt_alg.assert_called_with('{"kid": "123"}')
        m_jwt_decode.assert_called_with(
            "foo", key=m_jwt_alg.return_value, algorithms=["bar"]
        )

    @patch("cloud_info_catchall.token_generator.valid_token")
    @patch("cloud_info_catchall.token_generator.get_access_token")
    def test_generate_tokens(self, m_get_access, m_valid_token):
        tokens = {"foo": {"access_token": "abc"}, "bar": {"access_token": "def"}}
        secrets = {"foo": {}, "bar": {}}
        m_valid_token.side_effect = [True, False]
        m_get_access.return_value = "xyz"
        config = {"token_endpoint": "https://example.com"}
        tg.generate_tokens(config, "abc", tokens, 8, secrets)
        m_valid_token.assert_has_calls([call("abc", config, 8), call("def", config, 8)])
        m_get_access.assert_called_with("https://example.com", "abc", {})


if __name__ == "__main__":
    unittest.main()
