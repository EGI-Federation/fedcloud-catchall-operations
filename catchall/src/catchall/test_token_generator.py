"""Tests for the config generator"""

import unittest
from unittest.mock import call, patch

import catchall.token_generator as tg
import httpx
import jwt
import respx


class TokenGeneratorTest(unittest.TestCase):
    OIDC_CONFIG = {
        "jwks_uri": "https://example.com",
        "token_endpoint": "https://example.com",
    }

    @respx.mock
    def test_get_access_token(self):
        token_url = "https://example.com"
        scopes = "a b c"
        secret = {"client_id": "id", "client_secret": "secret"}

        route = respx.post(token_url).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "foo"},
            )
        )

        token = tg.get_access_token(token_url, scopes, secret)

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
    @patch("catchall.token_generator.get_access_token")
    def test_generate_tokens(self, m_get_access, m_valid_token):
        tokens = {"foo": {"access_token": "abc"}, "bar": {"access_token": "def"}}
        secrets = {
            "foo": {"client_id": "foo", "client_secret": "secfoo"},
            "bar": {"client_id": "bar", "client_secret": "secbar"},
        }
        m_valid_token.side_effect = [True, False]
        m_get_access.return_value = "xyz"
        tg.generate_tokens(self.OIDC_CONFIG, "abc", tokens, 8, secrets)
        m_valid_token.assert_has_calls(
            [call("abc", self.OIDC_CONFIG, 8), call("def", self.OIDC_CONFIG, 8)]
        )
        m_get_access.assert_called_with("https://example.com", "abc", secrets["bar"])


if __name__ == "__main__":
    unittest.main()
