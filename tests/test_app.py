"""UI flow tests driven by Streamlit's AppTest (the browser-side typing engine is covered by tests/js)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from typemaster import config
from typemaster.database import Database
from typemaster.services import process_submission

APP = str(Path(__file__).resolve().parent.parent / "app.py")
TEXT = "the quick brown fox jumps over the lazy dog " * 20


def fresh() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def sign_in(at: AppTest, name="Ritesh") -> AppTest:
    at.text_input[0].set_value(name)
    at.button[0].click()
    return at.run()


def goto(at: AppTest, page: str) -> AppTest:
    at.radio(key="nav").set_value(page)
    return at.run()


def press(at: AppTest, key: str) -> AppTest:
    return next(b for b in at.button if b.key == key).click().run()


def html(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


def test_welcome_screen_and_validation():
    at = fresh()
    assert not at.exception and "Ritesh Kumar Singh" in html(at) and "Founder" in html(at)
    sign_in(at, "x")
    assert at.error and "at least" in at.error[0].value
    sign_in(at, "<b>")
    assert at.error and at.session_state["player"] is None


def test_home_page_after_sign_in():
    at = sign_in(fresh())
    assert not at.exception and at.session_state["player"].name == "Ritesh"
    assert [o for o in at.radio(key="nav").options] == list(config.PAGES)
    text = html(at)
    assert "Community pulse" in text and "Key Doctor" in text and "Daily Challenge" in text
    assert "Ritesh Kumar Singh" in text and "Founder" in text
    assert "⚡" not in text
    for rail in ("Top typists", "Streak goal", "From the founder", "Typing tip of the day"):
        assert rail in text, rail                      # side rails are filled


def test_home_cta_navigates():
    at = sign_in(fresh())
    at = press(at, "home_daily")
    assert at.radio(key="nav").value == "Daily" and "Today&#x27;s setup" in html(at)


def test_practice_start_restart_new_cancel_flow():
    at = goto(sign_in(fresh()), "Practice")
    at.radio(key="cfg_duration_widget").set_value(30)
    at.radio(key="cfg_difficulty_widget").set_value("Hard")
    at = press(at, "start_btn")
    assert not at.exception
    test = at.session_state["test"]
    assert at.session_state["phase"] == "running" and test["duration"] == 30 and test["difficulty"] == "Hard"
    assert len(test["text"]) >= config.TARGET_CHARS[30] and test["mode"] == "standard"
    at = press(at, "restart_btn")
    again = at.session_state["test"]
    assert again["text"] == test["text"] and again["id"] != test["id"]
    at = press(at, "new_btn")
    assert at.session_state["test"]["text"] != test["text"]
    at = press(at, "cancel_btn")
    assert at.session_state["phase"] == "idle" and not at.exception


def test_leaving_the_page_cancels_a_running_test():
    at = goto(sign_in(fresh()), "Practice")
    at = press(at, "start_btn")
    assert at.session_state["phase"] == "running"
    at = goto(at, "Leaderboard")
    assert at.session_state["phase"] == "idle" and not at.exception


def test_daily_challenge_starts_same_text_for_everyone():
    at = goto(sign_in(fresh()), "Daily")
    at = press(at, "daily_start_btn")
    t = at.session_state["test"]
    assert t["mode"] == "daily" and t["duration"] == config.DAILY_DURATION and t["challenge_date"]
    from datetime import date
    from typemaster.passages import daily_challenge
    assert t["text"] == daily_challenge(date.today()).text


def test_empty_states_on_every_page_for_a_new_player():
    at = sign_in(fresh(), "Fresh Player Zed")
    for page, expected in [("Key Doctor", "No keystroke data yet"), ("Progress", "Your journey starts here"),
                           ("Rewards", "Your first certificate is waiting"), ("Analytics", "No data to chart yet")]:
        at = goto(at, page)
        assert not at.exception and expected in html(at), page
    at = goto(at, "Leaderboard")
    assert not at.exception and "No scores on the board" in html(at)


def test_pages_with_data_and_result_screen():
    at = sign_in(fresh(), "Data Dana")
    db, player = Database(config.DB_PATH), at.session_state["player"]
    res = None
    for i, (n, dur, diff, mode) in enumerate([(200, 60, "Easy", "standard"), (350, 60, "Medium", "standard"),
                                              (150, 30, "Hard", "standard"), (300, 60, "Medium", "drill")]):
        test = {"id": f"seed{i}", "text": TEXT, "duration": dur, "difficulty": diff, "mode": mode}
        res = process_submission(db, player.id, test, {
            "test_id": test["id"], "typed": TEXT[:n - 3] + "XYZ", "elapsed_ms": dur * 1000,
            "series": [30 + j for j in range(dur)], "ever_wrong": [1, 2]})
        assert res.saved
    for page, expected in [("Home", "Your day"), ("Progress", "Test history"), ("Rewards", "Featured challenge"),
                           ("Analytics", "Personal bests"), ("Key Doctor", "Your weakest keys"),
                           ("Leaderboard", "Data Dana")]:
        at = goto(at, page)
        assert not at.exception and expected in html(at) + " ".join(str(d.value) for d in at.dataframe), page
    at = goto(at, "Practice")
    at.session_state["test"] = {"id": "seed1", "text": TEXT, "duration": 60, "difficulty": "Medium", "mode": "standard",
                                "challenge_date": None, "pb": None}
    at.session_state["test_page"] = "Practice"
    at.session_state["result"] = res
    at.session_state["phase"] = "finished"
    at.run()
    assert not at.exception and "tm-bigwpm" in html(at) and any(b.key == "again_btn" for b in at.button)


def test_key_doctor_drill_starts():
    at = sign_in(fresh(), "Doc Dee")
    db, player = Database(config.DB_PATH), at.session_state["player"]
    test = {"id": "kd1", "text": TEXT, "duration": 60, "difficulty": "Easy", "mode": "standard"}
    process_submission(db, player.id, test, {"test_id": "kd1", "typed": TEXT[:300], "elapsed_ms": 60000,
                                             "ever_wrong": list(range(0, 300, 7))})
    at = goto(at, "Key Doctor")
    at = press(at, "drill_start_btn")
    t = at.session_state["test"]
    assert not at.exception and t["mode"] == "drill" and len(t["text"]) >= config.TARGET_CHARS[30]


def test_running_test_hides_side_rails_but_idle_shows_them():
    at = goto(sign_in(fresh()), "Practice")
    assert "From the founder" in html(at)
    at = press(at, "start_btn")
    assert at.session_state["phase"] == "running" and "From the founder" not in html(at) and not at.exception
    at = press(at, "cancel_btn")
    assert "From the founder" in html(at)


def test_first_test_result_offers_welcome_certificate():
    at = sign_in(fresh(), "Cert Carl")
    db, player = Database(config.DB_PATH), at.session_state["player"]
    test = {"id": "c1", "text": TEXT, "duration": 60, "difficulty": "Easy", "mode": "standard", "challenge_date": None, "pb": None}
    res = process_submission(db, player.id, test, {"test_id": "c1", "typed": TEXT[:200], "elapsed_ms": 60000})
    assert "first" in res.new_badge_ids
    at = goto(at, "Practice")
    at.session_state["test"], at.session_state["test_page"] = test, "Practice"
    at.session_state["result"], at.session_state["phase"] = res, "finished"
    at.run()
    assert not at.exception and "Certificate of Participation unlocked" in html(at)
    assert "Ritesh Kumar Singh" in html(at)
    at = goto(at, "Rewards")
    text = html(at)
    assert not at.exception and "UNLOCKED" in text and "Certificate of Participation" in text and "Verify" in " ".join(e.label for e in at.expander)


def test_rewards_verify_box_accepts_real_code():
    from typemaster import rewards as rw
    from typemaster.progress import earned_dates
    at = sign_in(fresh(), "Verify Vic")
    db, player = Database(config.DB_PATH), at.session_state["player"]
    test = {"id": "v1", "text": TEXT, "duration": 60, "difficulty": "Easy", "mode": "standard"}
    process_submission(db, player.id, test, {"test_id": "v1", "typed": TEXT[:200], "elapsed_ms": 60000})
    code = rw.certificate_code(player.id, "first", earned_dates(db.history(player.id))["first"])
    at = goto(at, "Rewards")
    at.text_input(key="verify_code").set_value(code)
    at = press(at, "verify_btn")
    assert at.success and "Genuine" in at.success[0].value
    at.text_input(key="verify_code").set_value(code[:-1] + ("0" if code[-1] != "0" else "1"))
    at = press(at, "verify_btn")
    assert at.error and "could not be verified" in at.error[0].value
