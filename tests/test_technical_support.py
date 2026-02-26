"""Tests for technical support detection and redirect."""

import unittest

from coach import CoachAgent
from coach.detection.detectors import detect_technical_support_request
from coach.inference import TECHNICAL_SUPPORT_RESPONSE


class DetectTechnicalSupportTests(unittest.TestCase):

    # --- Should trigger ---

    def test_fitbit_not_connecting(self):
        self.assertTrue(detect_technical_support_request("my fitbit is not connecting"))

    def test_fitbit_wont_sync(self):
        self.assertTrue(detect_technical_support_request("my fitbit won't sync"))

    def test_apple_watch_not_pairing(self):
        self.assertTrue(detect_technical_support_request("my apple watch is not pairing with the app"))

    def test_app_keeps_crashing(self):
        self.assertTrue(detect_technical_support_request("my app keeps crashing"))

    def test_app_wont_open(self):
        self.assertTrue(detect_technical_support_request("the app won't open"))

    def test_app_not_working(self):
        self.assertTrue(detect_technical_support_request("the app is not working"))

    def test_cant_log_in(self):
        self.assertTrue(detect_technical_support_request("I can't log in"))

    def test_cant_login_variant(self):
        self.assertTrue(detect_technical_support_request("can't login to the app"))

    def test_forgot_password(self):
        self.assertTrue(detect_technical_support_request("I forgot my password"))

    def test_reset_password(self):
        self.assertTrue(detect_technical_support_request("how do I reset my password"))

    def test_locked_out(self):
        self.assertTrue(detect_technical_support_request("I'm locked out"))

    def test_error_message(self):
        self.assertTrue(detect_technical_support_request("I keep seeing an error message"))

    def test_getting_an_error(self):
        self.assertTrue(detect_technical_support_request("I'm getting an error when I open it"))

    def test_technical_issue(self):
        self.assertTrue(detect_technical_support_request("I'm having a technical issue"))

    def test_how_do_i_use_feature(self):
        self.assertTrue(detect_technical_support_request("how do I use the notification feature"))

    def test_how_do_i_use_dashboard(self):
        self.assertTrue(detect_technical_support_request("how do I use the dashboard"))

    # --- Should NOT trigger ---

    def test_normal_coaching_question(self):
        self.assertFalse(detect_technical_support_request("how do I stay motivated to walk?"))

    def test_lesson_question(self):
        self.assertFalse(detect_technical_support_request("what is lesson 3 about?"))

    def test_fitbit_positive_context(self):
        self.assertFalse(detect_technical_support_request("I went for a walk with my fitbit and felt great"))

    def test_activity_question(self):
        self.assertFalse(detect_technical_support_request("what exercises can I do at home?"))

    def test_barrier_question(self):
        self.assertFalse(detect_technical_support_request("I can't find time to exercise"))


class TechnicalSupportAgentTests(unittest.TestCase):

    def _make_agent(self):
        stub_client = type("C", (), {
            "calls": [],
            "chat": type("Ch", (), {
                "completions": type("Cp", (), {
                    "create": lambda self, **kw: (_ for _ in ()).throw(AssertionError("OpenAI should not be called"))
                })()
            })()
        })()
        return CoachAgent(client=stub_client, model="fake-model")

    def test_tech_support_returns_redirect_without_calling_openai(self):
        agent = self._make_agent()
        reply = agent.generate_response("my app keeps crashing")
        self.assertIn("support@pathverse.ca", reply)
        self.assertIn("screenshots", reply)

    def test_tech_support_response_matches_constant(self):
        agent = self._make_agent()
        reply = agent.generate_response("I can't log in")
        self.assertEqual(reply, TECHNICAL_SUPPORT_RESPONSE)

    def test_fitbit_connectivity_redirects(self):
        agent = self._make_agent()
        reply = agent.generate_response("my fitbit won't sync")
        self.assertIn("support@pathverse.ca", reply)


if __name__ == "__main__":
    unittest.main()
