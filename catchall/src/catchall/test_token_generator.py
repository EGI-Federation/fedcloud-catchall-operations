"""Tests for the config generator"""

import unittest
from unittest.mock import mock_open, patch

import catchall.token_generator as tg
import httpx
import jwt
import respx
import testtools
from oslo_config import fixture


class TokenGeneratorTest(testtools.TestCase):
    OIDC_CONFIG = {
        "jwks_uri": "https://example.com",
        "token_endpoint": "https://example.com",
    }

    def setUp(self):
        super().setUp()
        self.conf = self.useFixture(fixture.Config()).conf

    @respx.mock
    def test_get_access_token(self):
        self.conf.set_override("scopes", "a b c", group="checkin")
        self.conf.set_override("client_id", "id", group="checkin")
        self.conf.set_override("client_secret", "secret", group="checkin")
        route = respx.post(self.OIDC_CONFIG["token_endpoint"]).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "foo"},
            )
        )
        token = tg.generate_token(self.OIDC_CONFIG)
        self.assertEqual(token, "foo")
        self.assertTrue(route.called)
        request = route.calls[0].request
        self.assertEqual(
            request.content.decode(),
            "grant_type=client_credentials"
            "&client_id=id"
            "&client_secret=secret"
            "&scope=a+b+c",
        )

    def test_valid_token_no_token(self):
        self.assertEqual(tg.valid_token(None, None, None), False)

    @respx.mock
    def _inner_test_valid_token(self, ttl, result):
        respx.get("https://example.com").mock(
            return_value=httpx.Response(
                200,
                json={"keys": [{"kid": "123"}]},
            )
        )

        self.assertEqual(tg.valid_token("foo", self.OIDC_CONFIG, ttl), result)

    def _setup_valid_token_test(self, m_header, m_decode, m_calendar):
        m_header.return_value = {"kid": "123", "alg": "bar"}
        m_decode.return_value = {"exp": 10}
        m_calendar.return_value = 8

    def _assert_valid_token_test(self, m_header, m_decode, m_alg):
        m_header.assert_called_with("foo")
        m_alg.assert_called_with('{"kid": "123"}')
        m_decode.assert_called_with("foo", key=m_alg.return_value, algorithms=["bar"])

    @patch("jwt.algorithms.RSAAlgorithm.from_jwk")
    @patch("jwt.get_unverified_header")
    @patch("jwt.decode")
    @patch("calendar.timegm")
    def test_valid_token_within_time(self, m_calendar, m_decode, m_header, m_alg):
        self._setup_valid_token_test(m_header, m_decode, m_calendar)
        self._inner_test_valid_token(1, True)
        self._assert_valid_token_test(m_header, m_decode, m_alg)
        m_calendar.assert_called_once()

    @patch("jwt.algorithms.RSAAlgorithm.from_jwk")
    @patch("jwt.get_unverified_header")
    @patch("jwt.decode")
    @patch("calendar.timegm")
    def test_valid_token_not_within_time(self, m_calendar, m_decode, m_header, m_alg):
        self._setup_valid_token_test(m_header, m_decode, m_calendar)
        self._inner_test_valid_token(5, False)
        self._assert_valid_token_test(m_header, m_decode, m_alg)
        m_calendar.assert_called_once()

    @patch("jwt.algorithms.RSAAlgorithm.from_jwk")
    @patch("jwt.get_unverified_header")
    @patch("jwt.decode")
    @patch("calendar.timegm")
    def test_valid_token_decode_exception(self, m_calendar, m_decode, m_header, m_alg):
        self._setup_valid_token_test(m_header, m_decode, m_calendar)
        m_decode.side_effect = jwt.DecodeError()
        self._inner_test_valid_token(1, False)
        self._assert_valid_token_test(m_header, m_decode, m_alg)
        m_calendar.assert_not_called()

    @patch("jwt.algorithms.RSAAlgorithm.from_jwk")
    @patch("jwt.get_unverified_header")
    @patch("jwt.decode")
    @patch("calendar.timegm")
    def test_valid_token_expired_exception(self, m_calendar, m_decode, m_header, m_alg):
        self._setup_valid_token_test(m_header, m_decode, m_calendar)
        m_decode.side_effect = jwt.ExpiredSignatureError()
        self._inner_test_valid_token(1, False)
        self._assert_valid_token_test(m_header, m_decode, m_alg)
        m_calendar.assert_not_called()

    @patch("catchall.token_generator.valid_token")
    @patch("os.path.exists")
    def test_check_token(self, m_exists, m_valid_token):
        m_valid_token.return_value = True
        m_exists.return_value = True
        with patch("builtins.open", mock_open(read_data="data")):
            tg.check_token("foo", self.OIDC_CONFIG, 23)
            m_valid_token.assert_called_with("data", self.OIDC_CONFIG, 23)
            m_exists.assert_called_with("foo")


if __name__ == "__main__":
    unittest.main()
