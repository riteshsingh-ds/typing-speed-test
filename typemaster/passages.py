"""Typing passages grouped by difficulty. All text is original, plain ASCII."""
from __future__ import annotations

import itertools
import random
from datetime import date
from dataclasses import dataclass
from typing import Optional

from . import config

PASSAGES: dict[str, tuple[str, ...]] = {
    "Easy": (
        "The sun rose over the quiet hills and the village began to wake up. A baker opened his shop and the smell of fresh bread filled the street. Children ran to school with bags on their backs while their parents waved from the doors. It was going to be a warm and happy day.",
        "My dog loves to play in the park near our house. Every morning we walk to the big green field and he runs after his red ball. When he gets tired he lies down in the shade of an old tree. I sit next to him and watch the clouds move slowly across the blue sky.",
        "Learning to type is a lot like learning to ride a bike. At first you feel slow and a little lost, but with a bit of practice your fingers start to remember where to go. Keep your hands relaxed, look at the screen, and do not rush. Speed will come after you build a steady rhythm.",
        "We packed a small bag and took the early train to the sea. The window was full of fields, farms, and tiny white houses. After two hours we stepped out into the salty air and heard the gulls. We left our shoes on the sand and ran straight into the cool water.",
        "Our kitchen is the warmest room in the house. On cold nights we sit around the table and share soup with bread and cheese. Grandma tells old stories about her life on the farm, and we laugh until the tea is cold. I hope every night can be as good as this one.",
        "A little green frog sat on a large leaf in the middle of the pond. He watched the fish swim by and counted the ripples on the water. When the rain began to fall, he jumped into the pond with a loud splash and swam away to find his friends under the old wooden bridge.",
        "The library on our street is my favorite place to spend a rainy afternoon. I pick a thick book from the shelf, find a soft chair by the window, and read until the lamps come on. The only sounds are the pages turning and the rain tapping on the glass.",
        "Every Saturday my brother and I make pancakes for the whole family. He mixes the batter while I heat the pan and watch for tiny bubbles. We stack them high, add honey and sliced fruit, and carry the plate to the table. Nobody ever leaves a single bite behind.",
    ),
    "Medium": (
        "Good design is rarely noticed; it simply works. When a door opens the way you expect, or a menu leads you exactly where you wanted to go, nobody stops to applaud. Designers know that the best compliment is silence, because it means the person never had to think about the tool in front of them.",
        "The city's old tram line was restored last spring, and commuters have quickly fallen in love with it. It's slower than the bus, yet people say the gentle rocking and the wide windows make the morning trip feel like a small holiday. Ridership has doubled, which surprised everyone, including the mayor.",
        "Sleep is not a luxury, as researchers keep reminding us; it's a basic need. During the night the brain sorts memories, repairs tissue, and clears out waste. Skipping rest to study or work longer often backfires, since attention, mood, and reaction time all decline after only a few late nights.",
        "When the storm finally passed, the harbor looked completely different. Boats had drifted from their moorings, ropes lay tangled along the dock, and a thick layer of seaweed covered the road. Neighbors arrived with buckets, brooms, and flasks of hot coffee, and by noon the worst of the mess was gone.",
        "Programming is often described as writing instructions for a machine, but most of the work is really about people. You read code written by others, explain your decisions in comments, and agree on conventions with your team. A clear name or a short, honest message can save hours of confusion later.",
        "She had practiced the speech a dozen times in front of the mirror, yet her hands still trembled when she stepped onto the stage. Then she saw a friendly face in the third row, took a slow breath, and began. By the second paragraph, the nerves had turned into something closer to excitement.",
        "Coffee traveled a long way before it reached your cup. It was grown on a shaded hillside, picked by hand, dried in the sun, roasted in small batches, and shipped across the ocean. Knowing that makes the first sip taste a little richer, and it's a good reason to treat the farmers fairly.",
        "A good habit is built on small, repeatable actions rather than heroic effort. Walking ten minutes after lunch, writing one paragraph each morning, or tidying the desk before bed will not change your life overnight, but after a few months the results are impossible to ignore.",
    ),
    "Hard": (
        "In 2023, the cross-functional team shipped version 4.2.1 of the platform, reducing average latency from 480ms to 135ms (a 72% improvement). The release required refactoring 14 microservices, migrating 3.5TB of data, and rewriting the authentication layer; nevertheless, uptime stayed at 99.98% throughout.",
        "\"Efficiency,\" she argued, \"is doing things right; effectiveness is doing the right things.\" The committee, however, remained unconvinced: its members demanded quarterly reports, itemized budgets (including contingencies of 12-15%), and an independent audit before approving the $2.4 million proposal.",
        "To configure the server, set PORT=8080 and DEBUG=false in the .env file, then run: python manage.py migrate && python manage.py runserver. If the connection fails, check firewall rules, verify that the database accepts requests from 192.168.1.25, and inspect /var/log/app/error.log for stack traces.",
        "Photosynthesis converts carbon dioxide and water into glucose and oxygen: 6CO2 + 6H2O -> C6H12O6 + 6O2. Although the equation looks simple, the underlying biochemistry involves chlorophyll, electron-transport chains, and enzymes such as RuBisCO, which scientists consider the most abundant protein on Earth.",
        "Quarterly revenue climbed 18.6% year-over-year to $52.7M, driven by subscriptions (64%), enterprise licensing (25%), and one-time services (11%). Management expects margins of 31-33% next fiscal year; however, currency fluctuations, supply-chain disruptions, and regulatory uncertainty could affect results.",
        "The archaeologist's notebook read: 'Site B-7, depth 2.5m: fragments of pottery, bronze pins, and charred seeds; radiocarbon dating suggests c. 1,200 B.C.' She underlined three words twice, photographed the stratigraphy from four angles, and labeled each sample with a waterproof marker before sealing the crate.",
        "Never reuse passwords across accounts! Use a unique passphrase of at least 16 characters, enable two-factor authentication (2FA), and store credentials in a reputable manager. Phishing emails often mimic banks, couriers, or colleagues; hover over links, inspect sender addresses, and when in doubt, call the official number instead.",
        "Between 09:30 and 17:45, the laboratory processed 238 samples; 7 were rejected for contamination, 12 required re-testing, and the rest passed validation. Technician #4 flagged an anomaly in batch Q-19: the readings fluctuated by +/- 0.8 units, which exceeds the allowed tolerance of 0.5.",
    ),
}

DIFFICULTY_BLURBS: dict[str, str] = {
    "Easy": "Everyday words and simple sentences. Ideal for building rhythm.",
    "Medium": "Richer vocabulary with commas, semicolons and apostrophes.",
    "Hard": "Numbers, symbols, quotes and technical terms. Built to slow you down.",
}


@dataclass(frozen=True)
class Challenge:
    text: str
    difficulty: str
    duration: int
    first_index: int


def build_challenge(
    difficulty: str,
    duration: int,
    rng: Optional[random.Random] = None,
    avoid_first: Optional[int] = None,
) -> Challenge:
    """Assemble a random, non-repeating text long enough for ``duration``.

    ``avoid_first`` is the index of the passage that opened the previous test
    of the same difficulty, so "New challenge" never starts with the same one.
    """
    if difficulty not in PASSAGES:
        raise ValueError(f"Unknown difficulty: {difficulty!r}")
    if duration not in config.TARGET_CHARS:
        raise ValueError(f"Unsupported duration: {duration!r}")

    rng = rng or random.Random()
    bank = PASSAGES[difficulty]
    order = list(range(len(bank)))
    rng.shuffle(order)
    if avoid_first is not None and len(order) > 1 and order[0] == avoid_first:
        order[0], order[-1] = order[-1], order[0]

    target = config.TARGET_CHARS[duration]
    parts: list[str] = []
    length = 0
    for index in itertools.cycle(order):
        parts.append(bank[index])
        length += len(bank[index]) + 1
        if length - 1 >= target:
            break
    return Challenge(" ".join(parts), difficulty, duration, order[0])


def daily_challenge(day: date) -> Challenge:
    """The same text for everybody on a given calendar day."""
    rng = random.Random(f"typemaster-daily-{day.isoformat()}")
    return build_challenge(config.DAILY_DIFFICULTY, config.DAILY_DURATION, rng=rng)
