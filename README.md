# TypeMaster - Typing Speed Challenge

A complete typing-practice web app built with **Python, Streamlit, SQLite, Plotly and Pandas**.
Real-time WPM, accuracy and mistake tracking, green/red character feedback, three difficulty levels,
persistent history, analytics charts and a leaderboard.

## What makes it different

| Feature | What it does |
|---|---|
| **3-second boot screen** | Branded splash with a progress bar while the database and home data load (set `TYPEMASTER_SPLASH=0` to skip) |
| **Home page** | Product landing with community pulse (tests, players, fastest player), your day, feature tour and Founder & CEO credit |
| **Daily Challenge** | The same text for every player each day, with its own daily leaderboard and rank |
| **Key Doctor** | Maps every key you type (including mistakes you corrected), shows a keyboard heat-map and builds a drill from your weakest keys |
| **Ghost pace** | Each result plots your pace second by second against your previous best run |
| **XP, levels, streaks, 18 badges** | Accuracy-weighted XP, level titles, day streaks (3, 5, 7 and 30 days) and Bronze/Silver/Gold/Platinum badges |
| **Certificates** | A signed Certificate of Participation for every player's first test, plus Consistency (5-day streak), Speed (40/60/80/100 WPM) and Accuracy certificates. Download as PNG or PDF |
| **Founder approval** | Every badge and certificate carries TypeMaster branding, the founder's signature and an Approved seal |
| **Verifiable IDs** | Each certificate has a signed ID. Anyone can paste it under Rewards > Verify a certificate |
| **Side panels** | Left: your level, streak goal, today's challenge, quick start. Right: top typists, latest reward, typing tip, founder note. Hidden on small screens and during a running test |
| **Result cards** | Download a polished SVG score card after every test |
| **Analytics** | Speed trend, speed vs accuracy, difficulty and length breakdowns, activity, personal-best matrix |
| **Core typing** | 30/60/120 s tests, Easy/Medium/Hard, live WPM/accuracy/mistakes, green/red highlighting, SQLite history |

Pages: Home, Practice, Daily, Key Doctor, Progress (level, streaks, history), Rewards (badges, certificates, verify), Analytics, Leaderboard.
Key Doctor drills are practice only: they never count towards records or leaderboards.

## Quick start

Requires **Python 3.10 or newer**.

```bash
# 1. open the project folder in VS Code, then open a terminal (Ctrl+`)
python -m venv .venv

# 2. activate it
#    Windows (PowerShell):  .venv\Scripts\Activate.ps1
#    Windows (cmd):         .venv\Scripts\activate.bat
#    macOS / Linux:         source .venv/bin/activate

# 3. install and run
pip install -r requirements.txt
streamlit run app.py
```

The app opens at <http://localhost:8501>. Enter a player name, pick a length and difficulty, press
**Start challenge**, click the text area and start typing. The timer begins with your first keystroke.

## Project structure

```
typemaster/
├── app.py                      # Streamlit entry point: header, sign-in, tabs
├── requirements.txt
├── README.md
├── .streamlit/config.toml      # dark theme
├── frontend/typing_engine/
│   └── index.html              # real-time typing arena (HTML/CSS/JS component)
├── typemaster/
│   ├── config.py               # all constants (durations, limits, DB path)
│   ├── database.py             # SQLite schema + queries
│   ├── metrics.py              # WPM / accuracy maths (pure functions)
│   ├── validators.py           # player-name and result-payload validation
│   ├── services.py             # validate -> score -> save pipeline, PB / XP / badge logic
│   ├── progress.py             # XP, levels, streaks, achievements, weak-key ranking
│   ├── drills.py               # Key Doctor drill builder
│   ├── cards.py                # downloadable SVG result card
│   ├── rewards.py              # badge/certificate PNG+PDF rendering, signed certificate IDs
│   ├── splash.py               # 3-second boot screen
│   ├── passages.py             # passage bank + random challenge builder
│   ├── analytics.py            # Plotly figure builders
│   ├── typing_widget.py        # Python wrapper for the frontend component
│   ├── state.py                # session-state helpers
│   ├── styles.py               # global CSS
│   ├── ui.py                   # cards, empty/error states, Streamlit compat helpers
│   └── views/                  # home, practice, daily, keydoctor, profile, rewards, rails, dashboard, history, leaderboard, arena
├── tests/                      # pytest suite + jsdom tests for the typing engine
├── assets/                     # favicon + bundled fonts (Poppins, Lora, DejaVu Mono) for certificates
└── data/                       # SQLite database is created here
```

## How it works (design decisions)

**Why a custom component?** Streamlit only reruns the script when a widget commits a value, so a plain
`st.text_area` cannot give live per-keystroke feedback or a ticking timer. The typing arena therefore runs
entirely in the browser (`frontend/typing_engine/index.html`) and talks to Python through Streamlit's
component protocol. It needs no Node build step.

**The timer cannot reset on reruns.** The countdown lives in the browser, and the component only
re-initialises when it receives a *new* `test_id`. Reruns caused by other widgets (for example changing a
leaderboard filter mid-test) re-send the same `test_id` and are ignored.

**Python re-scores everything.** When the test ends, the browser sends the typed text and elapsed time.
The server validates it (test id, length, timing, plausibility) and recomputes all metrics itself. Client-side
numbers are only used for the live display.

**No duplicate submissions.** Three layers: the browser posts one result per test, the app marks a test id as
submitted *before* saving, and the database has a `UNIQUE` constraint on `test_id`.

**Existing database?** It is upgraded automatically (new columns are added in place); your old scores are kept.

**Cheating guard.** Paste, drop and caret-moving keys are blocked in the arena, and any result faster than
350 WPM or with impossible timing is rejected on the server.

### Scoring definitions

- **Correct characters**: typed characters matching the passage at the same position
- **Mistakes**: typed characters that do not match
- **Accuracy**: correct / typed x 100 (measured on the final text, so a corrected mistake no longer counts)
- **XP per test**: correct characters x accuracy squared / 4. Level = floor(sqrt(XP / 100)) + 1
- **Net WPM**: (correct characters / 5) / minutes elapsed
- **Raw WPM**: (typed characters / 5) / minutes elapsed

If you finish the whole passage before time runs out, the test ends early and the real elapsed time is used.

## Testing

```bash
# Python: maths, validation, database + migration, XP/streaks/badges, drills, UI flows (139 tests)
pytest

# Typing engine in a simulated browser (needs Node.js 18+, one-time install)
cd tests/js
npm install
npm test
```

What is covered: WPM and accuracy formulas, name and payload validation, SQLite constraints, duplicate-save
protection, leaderboard ranking, personal-best detection, database-failure recovery, the Streamlit UI flow
(sign-in, start, restart, new passage, cancel, result screen, all tabs with and without data), and in the
browser engine: green/red marking, timer start, countdown finish, early completion, late-keystroke
rejection, paste blocking and "reruns never reset the timer".

### Manual checklist

1. Start a 30-second Easy test and type a few words with one deliberate typo: it shows red, Mistakes becomes 1.
2. Let the timer run out: the result screen appears and the score shows up in History and Leaderboard.
3. Change a leaderboard filter in the middle of a test: the timer keeps running.
4. Press **Restart** mid-test: same text, fresh timer. Press **New passage**: different text.
5. Play the Daily Challenge, then check the Daily tab of the leaderboard. Type with deliberate typos, then open Key Doctor: those keys glow red.
6. Finish your first test: a Certificate of Participation appears on the result screen. Open Rewards, download the PNG and PDF, then paste its ID into Verify.
7. Reload the page: you stay signed in (name is kept in the URL) and your history is still there.
8. Open the app on a phone (`streamlit run app.py --server.address 0.0.0.0`, then browse to your computer's IP).

## Certificates and badges

- Earned automatically. The first completed test unlocks the **Certificate of Participation** and it is offered
  right on the result screen. All files are also under **Rewards**.
- The **5-day streak** is the featured challenge: Five-day streak badge + Certificate of Consistency.
- Certificate IDs look like `TM-0001-FIRST-261121-9117A3`. The last part is an HMAC signature, so IDs cannot be
  forged. **Before launching publicly, set your own secret:** `TYPEMASTER_CERT_SECRET=your-long-random-string`
  (changing it later invalidates previously issued IDs).
- Founder name and title come from `typemaster/config.py` (`FOUNDER_NAME`, `FOUNDER_TITLE`).

## Customising

- Add passages in `typemaster/passages.py` (keep them plain ASCII, 200-450 characters; the tests check this).
- Change durations in `typemaster/config.py`. The database constraint is generated from the same list; delete
  `data/typemaster.db` after changing durations on an existing install.
- Use a different database file with `TYPEMASTER_DB=/path/to/file.db streamlit run app.py`.

## Troubleshooting

- **Typing area says "Click here"**: click inside it once; browsers sometimes block automatic focus.
- **Fonts look different offline**: the app uses Google Fonts and falls back to system fonts without internet.
- **`database is locked`**: close other programs that have `typemaster.db` open (for example a DB browser).
- **Player names** are not password-protected; they simply group scores. Anyone using the same name shares history.
