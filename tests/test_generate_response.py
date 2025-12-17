"""Tests for CoachAgent.generate_response with a stubbed client: It fakes the API so we can confirm the agent sends the correct messages and saves both sides of the conversation, without hitting the real OpenAI service."""

import unittest

from main import CoachAgent


class StubCompletion:
    def __init__(self, text: str) -> None:
        message = type("Msg", (), {"content": text})
        choice = type("Choice", (), {"message": message()})
        self.choices = [choice()]


class StubChatCompletions:
    def __init__(self, client: "StubClient") -> None:
        self._client = client

    def create(self, **kwargs):
        self._client.calls.append(kwargs)
        return StubCompletion("Stub reply")


class StubChat:
    def __init__(self, client: "StubClient") -> None:
        self.completions = StubChatCompletions(client)


class StubClient:
    def __init__(self) -> None:
        self.calls = []
        self.chat = StubChat(self)


class GenerateResponseTests(unittest.TestCase):
    def test_generate_response_appends_history_and_calls_client(self) -> None:
        stub_client = StubClient()
        agent = CoachAgent(client=stub_client, model="fake-model")

        reply = agent.generate_response("Hello coach")

        self.assertEqual(reply, "Stub reply")
        self.assertEqual(len(agent.history), 2)
        self.assertEqual(agent.history[0]["role"], "user")
        self.assertEqual(agent.history[0]["content"], "Hello coach")
        self.assertEqual(agent.history[1]["role"], "assistant")
        self.assertEqual(agent.history[1]["content"], "Stub reply")

        self.assertEqual(len(stub_client.calls), 1)
        recorded = stub_client.calls[0]
        self.assertEqual(recorded["model"], "fake-model")
        self.assertEqual(recorded["messages"][-1]["content"], "Hello coach")
        self.assertEqual(recorded["messages"][0]["role"], "system")


if __name__ == "__main__":
    unittest.main()
