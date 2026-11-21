"""UI flows with Google login switched on (st.login is simulated by patching the auth adapter)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from typemaster import auth, config
from typemaster.database import Database
from typemaster.metrics import compute_metrics

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture()
def login(monkeypatch):
    """Switch login mode on; ``who['user']`` is whatever Google says the visitor is (None = signed out)."""
    who = {"user": None, "logged_out": 0}
    monkeypatch.setattr(auth, "is_configured", lambda: True)
    monkeypatch.setattr(auth, "current_user", lambda: who["user"])
    monkeypatch.setattr(auth, "logout", lambda: who.update(user=None, logged_out=who["logged_out"] + 1))
    who["as_"] = lambda email, name="Google Person", verified=True: who.update(user=auth.AuthUser(email, name, verified))
    return who


def run() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def html(at):
    return " ".join(m.value for m in at.markdown)


def btn(at, label=None, key=None):
    return next(b for b in at.button if (key and b.key == key) or (label and b.label == label))


def field(at, label_start):
    return next(t for t in at.text_input if t.label.startswith(label_start))


def test_signed_out_visitor_sees_only_the_login_screen(login):
    at = run()
    assert not at.exception and at.session_state["player"] is None
    assert any(b.key == "login_btn" and "Google" in b.label for b in at.button)
    assert "Ritesh Kumar Singh" in html(at)
    assert not at.text_input                      # no name box: names are not identities any more
    assert "Community pulse" not in html(at)


def test_unverified_email_is_rejected(login):
    login["as_"]("unverified@example.com", verified=False)
    at = run()
    assert "not verified" in html(at) and at.session_state["player"] is None


def test_new_google_user_creates_account_and_is_remembered(login):
    login["as_"]("fresh1@example.com", "Fresh One")
    at = run()
    assert "Welcome, Fresh One" in html(at) and at.session_state["player"] is None
    at = btn(at, "Create my account").click().run()
    assert not at.exception and at.session_state["player"].email == "fresh1@example.com"
    assert "Community pulse" in html(at)
    # a brand-new browser session for the same Google account goes straight in: no sign-up again
    again = run()
    assert again.session_state["player"].email == "fresh1@example.com" and "Welcome, Fresh One" not in html(again)


def test_two_people_can_use_the_same_display_name(login):
    login["as_"]("twin1@example.com", "Ritesh")
    a = btn(run(), "Create my account").click().run().session_state["player"]
    login["as_"]("twin2@example.com", "Ritesh")
    b = btn(run(), "Create my account").click().run().session_state["player"]
    assert a.name == b.name == "Ritesh" and a.id != b.id and a.email != b.email


def test_claim_old_name_only_profile_keeps_scores(login):
    db = Database(config.DB_PATH)
    old = db.get_or_create_player("Old Timer Zed")
    db.save_result(old.id, "claim-t1", 60, "Easy", compute_metrics("a" * 300, "a" * 300, 60), [])
    login["as_"]("claimer@example.com", "Someone")
    at = run()
    field(at, "Your old player name").set_value("old timer zed")
    at = btn(at, "Find my old profile").click().run()
    assert "1 tests, best 60 WPM" in " ".join(str(e.value) for e in at.markdown)
    at = btn(at, key=f"claim_{old.id}").click().run()
    player = at.session_state["player"]
    assert player.id == old.id and player.email == "claimer@example.com"
    assert len(db.history(old.id)) == 1
    # nobody else can claim it afterwards
    login["as_"]("thief@example.com", "Thief")
    at = run()
    field(at, "Your old player name").set_value("Old Timer Zed")
    at = btn(at, "Find my old profile").click().run()
    assert any("No unclaimed profile" in i.value for i in at.info)


def test_switching_google_account_never_leaks_the_previous_player(login):
    login["as_"]("swa@example.com", "Swa")
    at = btn(run(), "Create my account").click().run()
    first = at.session_state["player"]
    login["as_"]("swb@example.com", "Swb")        # different Google account in the same browser session
    at.run()
    assert at.session_state["player"] is None and "Welcome, Swb" in html(at) and "Community pulse" not in html(at)
    at = btn(at, "Create my account").click().run()
    second = at.session_state["player"]
    assert second.email == "swb@example.com" and second.id != first.id
    login["as_"]("swa@example.com", "Swa")        # and back again: Swa's own data returns
    at.run()
    assert at.session_state["player"].id == first.id


def test_rename_sign_out_and_delete_account(login):
    login["as_"]("manage@example.com", "Manager")
    at = btn(run(), "Create my account").click().run()
    pid = at.session_state["player"].id
    db = Database(config.DB_PATH)

    field(at, "Display name").set_value("Better Name")
    at = btn(at, "Save name").click().run()
    assert db.get_player(pid).name == "Better Name" and not at.exception
    field(at, "Display name").set_value("<bad>")
    at = btn(at, "Save name").click().run()
    assert at.error and db.get_player(pid).name == "Better Name"

    at.checkbox(key="delete_account_confirm").check()
    at.run()                                                  # ticking the box reruns the page and enables the button
    at = btn(at, key="delete_account_btn").click().run()
    assert db.get_player(pid) is None and login["logged_out"] >= 1


def test_sign_out_button_logs_out(login):
    login["as_"]("bye@example.com", "Bye")
    at = btn(run(), "Create my account").click().run()
    at = btn(at, key="signout_btn").click().run()
    assert login["logged_out"] == 1 and at.session_state["player"] is None
    assert any(b.key == "login_btn" for b in at.button)


def test_real_streamlit_auth_objects_with_secrets_configured(monkeypatch):
    """No patching of the adapter: a configured [auth] section + nobody logged in => login screen."""
    monkeypatch.delenv("TYPEMASTER_AUTH", raising=False)
    at = AppTest.from_file(APP, default_timeout=30)
    at.secrets["auth"] = {"redirect_uri": "http://localhost:8501/oauth2callback", "cookie_secret": "x" * 32,
                          "client_id": "id.apps.googleusercontent.com", "client_secret": "s",
                          "server_metadata_url": "https://accounts.google.com/.well-known/openid-configuration"}
    at.run()
    assert not at.exception, at.exception
    assert any(b.key == "login_btn" for b in at.button) and not at.text_input


def test_without_secrets_the_app_runs_in_local_mode(monkeypatch):
    monkeypatch.delenv("TYPEMASTER_AUTH", raising=False)
    assert auth.is_configured() is False
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception and at.text_input and "Local mode" in " ".join(c.value for c in at.caption)
