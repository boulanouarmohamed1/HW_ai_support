from unittest.mock import Mock, patch

from frappe.tests import UnitTestCase

from hw_ai_support.llm import LLMError, ask


class TestLLM(UnitTestCase):
	@patch("hw_ai_support.llm._key", return_value="test-key")
	@patch("hw_ai_support.llm.requests.post")
	def test_success(self, post, key):
		response = Mock(status_code=200)
		response.json.return_value = {"candidates": [{"content": {"parts": [{"text": "Hello"}]}}]}
		post.return_value = response
		self.assertEqual(ask("system", [{"role": "user", "content": "hello"}]), "Hello")
		self.assertEqual(post.call_args.kwargs["headers"]["x-goog-api-key"], "test-key")

	@patch("hw_ai_support.llm.time.sleep")
	@patch("hw_ai_support.llm._key", return_value="test-key")
	@patch("hw_ai_support.llm.requests.post")
	def test_retries_429(self, post, key, sleep):
		limited = Mock(status_code=429)
		good = Mock(status_code=200)
		good.json.return_value = {"candidates": [{"content": {"parts": [{"text": "Recovered"}]}}]}
		post.side_effect = [limited, good]
		self.assertEqual(ask("system", [{"role": "user", "content": "hello"}]), "Recovered")
		self.assertEqual(post.call_count, 2)

	@patch("hw_ai_support.llm._key", return_value="test-key")
	@patch("hw_ai_support.llm.requests.post")
	def test_empty_or_blocked_response(self, post, key):
		response = Mock(status_code=200)
		response.json.return_value = {"promptFeedback": {"blockReason": "SAFETY"}, "candidates": []}
		post.return_value = response
		with self.assertRaises(LLMError):
			ask("system", [{"role": "user", "content": "hello"}])

	@patch("hw_ai_support.llm._key", return_value=None)
	def test_no_key_configured(self, key):
		with self.assertRaises(LLMError):
			ask("system", [{"role": "user", "content": "hello"}])
