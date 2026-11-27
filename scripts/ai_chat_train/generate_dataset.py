#!/usr/bin/env python3
"""AI 채팅 전용 모델 학습 데이터 생성기 — 영어 질문 → HubQueryDTO JSON (docs/ai_chat_mlx_design.md T2).

칸 값을 먼저 뽑고 그 값에 맞는 질문을 조립하므로 라벨은 구성상 정확하다.
사용: python3 scripts/ai_chat_train/generate_dataset.py [--count 6000] [--seed 7] [--out DIR]
"""

import argparse
import json
import random
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# HubQueryPrompt.schemaFields 순서·HubQuery enum 값과 같아야 한다 — check_swift_schema 가 대조한다.
KEYS = [
    "intent", "daysAgo", "month", "dayOfMonth", "hour", "minute",
    "period", "origin", "destination", "event", "reference", "topic",
]
ENUMS = {
    "intent": ["video", "drive", "settingsHelp", "unknown"],
    "period": ["any", "morningCommute", "eveningCommute", "morning", "afternoon", "evening", "night"],
    "event": ["any", "impact"],
    "reference": ["none", "previous"],
}
# 스키마에서 enum 칸은 null 을 못 쓴다 — 말하지 않았으면 이 값이다.
DEFAULTS = {"period": "any", "event": "any", "reference": "none"}
STRING_KEYS = ("origin", "destination", "topic")

# 앱이 전용 모델에 보내는 지시문과 글자 단위로 같아야 한다(T4 에서 앱에 같은 문자열을 둔다).
SYSTEM_PROMPT = (
    "Convert a question about a dashcam app into search fields. Do not answer the question. "
    "Answer with one JSON object with exactly these keys: " + ", ".join(KEYS) + ". "
    "Use null for anything the user did not say."
)

QUOTAS = {"video": 0.33, "drive": 0.25, "reference": 0.07, "settingsHelp": 0.20, "unknown": 0.15}
# 고정 문장뿐인 종류는 문맥(today·previous result)만 바꿔 되풀이한다.
MAX_REPEATS = {"reference": 8, "unknown": 2}

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKDAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
NUM_WORDS = {3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}
# HubDayPeriod.hours 와 같은 범위(끝 포함). any 는 새벽을 뺀다.
HOURS = {
    "any": (5, 23), "morning": (6, 11), "afternoon": (12, 17), "evening": (18, 23),
    "night": (0, 5), "morningCommute": (6, 9), "eveningCommute": (17, 20),
}
PM_PERIODS = {"afternoon", "evening", "eveningCommute"}
MINUTES = [0, 0, 0, 0, 0, 5, 10, 15, 20, 30, 30, 40, 45, 50]

PLACES = [
    "Seattle", "Tacoma", "Bellevue", "Portland", "San Jose", "Oakland", "San Francisco",
    "Los Angeles", "Pasadena", "Santa Monica", "Long Beach", "San Diego", "Sacramento", "Fresno",
    "Las Vegas", "Phoenix", "Tucson", "Denver", "Boulder", "Salt Lake City", "Austin", "Dallas",
    "Houston", "San Antonio", "Fort Worth", "Oklahoma City", "Kansas City", "St. Louis", "Chicago",
    "Milwaukee", "Minneapolis", "Detroit", "Ann Arbor", "Cleveland", "Columbus", "Cincinnati",
    "Indianapolis", "Nashville", "Memphis", "Atlanta", "Charlotte", "Raleigh", "Miami", "Orlando",
    "Tampa", "Jacksonville", "Washington", "Baltimore", "Philadelphia", "Pittsburgh", "Newark",
    "Jersey City", "Brooklyn", "Manhattan", "Queens", "Boston", "Cambridge", "Providence",
    "Hartford", "Buffalo", "Toronto", "Vancouver", "Montreal", "Ottawa", "London", "Manchester",
    "Birmingham", "Leeds", "Dublin", "Sydney", "Melbourne", "Brisbane", "Auckland", "Berlin",
    "Munich", "Hamburg", "Frankfurt", "Paris", "Lyon", "Madrid", "Barcelona", "Rome", "Milan",
    "Amsterdam", "Brussels", "Zurich", "Vienna", "Seoul", "Busan", "Incheon", "Pangyo", "Tokyo",
    "Osaka", "Singapore", "Dubai", "Costco", "IKEA", "downtown", "school", "campus", "home",
]
# work 는 넣지 않는다 — "from work to home" 과 출퇴근 표현(drive home from work)의 라벨이 엇갈린다.

V_VERBS = [
    "Show me", "Show", "Play", "Pull up", "Find", "Bring up", "Open", "Let me watch", "Let me see",
    "I want to see", "I want to watch", "I'd like to see", "I need", "Give me", "Can you show me",
    "Can you pull up", "Could you play", "Can I see", "Please show me", "Please play",
]
V_NOUNS = [
    "the video", "the recording", "the clip", "the footage", "the dashcam video",
    "the dashcam footage", "the recorded video",
]
V_IMPACT_NOUNS = [
    "the accident video", "the crash footage", "the crash video", "the impact video",
    "the collision clip", "the collision footage", "the near-miss video", "the hard braking video",
    "the video of the accident", "the footage of the crash", "the video of the collision",
    "the recording of the impact", "the video where I slammed on the brakes",
    "the clip where someone hit my car", "the video of when I almost got hit",
    "the recording of the sudden stop", "the video where I braked hard",
    "the footage of the near miss", "the video of the bump", "the video where another car hit me",
    "the footage from when I almost crashed",
]
V_EXISTS = [
    "Is there a video", "Are there any recordings", "Is there any footage",
    "Do you have a recording", "Are there any clips", "Did the dashcam save a video",
]
V_EXISTS_IMPACT = [
    "Is there an accident video", "Are there any impact videos", "Is there a video of the crash",
    "Is there any crash footage", "Do you have a recording of the collision",
    "Are there any near-miss videos",
]
V_RECORDED = [
    "What did the dashcam record {adv}?", "Play what the dashcam recorded {adv}",
    "I want to see what was recorded {adv}", "Show me what the camera recorded {adv}",
    "What was recorded {adv}?",
]
V_NARRATIVES = [
    "Someone hit my car", "I almost got hit", "I had to slam on the brakes",
    "A car cut me off and I braked hard", "I think I hit something", "There was an accident",
    "I was in a crash", "Somebody bumped into my car",
]
V_NARRATIVE_TAILS = [
    "show me the video", "can you show me the video?", "play the footage", "I need the footage",
    "pull up the recording",
]

D_PLAIN = [
    "Show me the route {frm}", "Show me my route {frm}", "Show my drive {frm} on the map",
    "Map of my trip {frm}", "Show me my drive log {frm}", "Show me the path I took {adv}",
    "Where did I drive {adv}?", "Where did I go {adv}?", "What route did I take {adv}?",
    "Which way did I go {adv}?", "Show me where I drove {adv}", "Show me my trip {frm} on the map",
    "route {frm}", "my driving route {frm}", "Show the driving history {frm}",
]
D_COMMUTE = [
    "Show me the route of {np}", "Show me the route for {np}", "Map of {np}",
    "Show {np} on the map", "Where did I go on {np}?",
]
D_PLACES = {
    "both": [
        "Show the route from {o} to {d} {adv}", "Show me my drive from {o} to {d} {adv}",
        "Map of my trip from {o} to {d} {adv}", "Trip from {o} to {d} {adv}, show me the path",
        "What route did I take from {o} to {d} {adv}?", "Show me how I got from {o} to {d} {adv}",
        "the drive from {o} to {d} {adv}",
    ],
    "dest": [
        "What route did I take to {d} {adv}?", "Show me my trip to {d} {adv}",
        "Which way did I go to {d} {adv}?", "Show me the map for my trip to {d} {adv}",
        "Show the route to {d} {adv}", "Show me the drive to {d} {adv}",
    ],
    "origin": [
        "Show me the drive that started from {o} {adv}", "Show the route starting from {o} {adv}",
        "Where did I go from {o} {adv}?", "Show my trip leaving {o} {adv}",
    ],
    "home": ["Show me the drive home from {o} {adv}", "Show my route home from {o} {adv}"],
}
D_IMPACT = [
    "Where did I brake hard {adv}?", "Where did the accident happen {adv}?",
    "Show me where the crash happened {adv}", "Where was the impact detected {adv}?",
    "Show the location of the near miss {adv}", "Where did I stop suddenly {adv}?",
    "Show me where I almost crashed {adv}",
    "Show me the route and where the accident happened {adv}", "location of the accident {frm}",
    "Where did someone hit my car {adv}?", "Where was I when I slammed on the brakes {adv}?",
    "Show the spot where I braked hard {adv}",
]
D_IMPACT_PLACES = {
    "both": [
        "Where did I brake hard on the way from {o} to {d} {adv}?",
        "Show me where the accident happened on my trip from {o} to {d} {adv}",
        "I almost had an accident {adv} going from {o} to {d}. Show me the route and where it happened",
        "Where was the impact detected on the drive from {o} to {d} {adv}?",
    ],
    "dest": [
        "Where did I stop suddenly on the way to {d} {adv}?",
        "Show me where I almost crashed on my trip to {d} {adv}",
    ],
}

REF_VIDEO = [
    "Show me that video", "Play the video for that", "Show me the video of the above",
    "Can I see the footage from that moment?", "Play that video again",
    "Show me the video from then", "Let me see the video of that",
    "Show the recording for that drive", "Play the clip from that time",
    "Show me the footage of that event", "Show me the video for the above case",
    "I want to watch that video", "Show me that clip again", "Video of that, please",
    "Show the video from that drive", "Play the recording from that moment",
    "Can you play the video of it?", "Let me watch the footage for that one",
    "Pull up the video for that drive", "Show the video of what happened then",
]
REF_DRIVE = [
    "Show me the route for that drive", "Where did that happen?", "Show that on the map",
    "Show the route at that time", "Where was that?", "Show me the route for that",
    "Map of that drive", "Where was that video taken?", "Show me that drive on the map",
    "What route was that?", "Show the location of that", "Show the path for the above",
    "Where did that take place?", "Show me the map for that one", "Where was I then?",
    "Show the route of the above drive", "Show me where it happened",
]

# (주제, 표시) — c 값을 바꾼다 · t 켜고 끈다 · n 관사 없이 쓴다 · p 막고 싶은 문제
TOPICS = [
    ("impact sensitivity", "c"), ("parking impact sensitivity", "c"),
    ("driving impact sensitivity", "c"), ("motion sensitivity", "c"), ("motion detection", "ctn"),
    ("parking mode", "ctn"), ("parking recording", "ctn"), ("parking recording time", "c"),
    ("parking recording type", "c"), ("time-lapse", "ctn"), ("time-lapse recording", "ctn"),
    ("low-power mode", "ctn"), ("low voltage cutoff", "c"), ("cutoff voltage", "c"),
    ("battery protection", "ctn"), ("voice recording", "ctn"), ("audio recording", "ctn"),
    ("microphone", "t"), ("speaker volume", "c"), ("voice guidance", "ctn"),
    ("voice commands", "tn"), ("LED", "t"), ("status LED", "t"), ("security LED", "t"),
    ("Wi-Fi band", "c"), ("Wi-Fi password", "c"), ("Wi-Fi name", "c"), ("video resolution", "c"),
    ("video quality", "c"), ("frame rate", "c"), ("HDR", "tn"), ("night vision", "tn"),
    ("rear camera", "t"), ("interior camera", "t"), ("SD card", ""), ("memory card", ""),
    ("storage allocation", "c"), ("event recording", "ctn"), ("loop recording", "ctn"),
    ("time zone", "c"), ("date and time", "c"), ("daylight saving time", "tn"),
    ("speed unit", "c"), ("speed display", "ct"), ("speed stamp", "t"), ("GPS", "tn"),
    ("ADAS", "tn"), ("lane departure warning", "tn"), ("forward collision warning", "tn"),
    ("front vehicle departure alert", "t"), ("speed camera alerts", "tn"), ("firmware", ""),
    ("firmware update", ""), ("language", "c"), ("screen saver", "ct"),
    ("display brightness", "c"), ("auto power off", "ctn"), ("continuous recording", "ctn"),
    ("recording duration", "c"), ("clip length", "c"), ("video download", "n"), ("live view", "n"),
    ("privacy mode", "tn"), ("event file protection", "tn"), ("overwrite protection", "tn"),
    ("parking notifications", "tn"), ("heat protection", "tn"), ("radar sensor", "ct"),
    ("time stamp", "t"), ("watermark", "t"), ("date format", "c"), ("beep sound", "ct"),
    ("startup sound", "ct"), ("alert volume", "c"), ("recording quality", "c"), ("bitrate", "c"),
    ("parking timer", "c"), ("G-sensor", "ct"), ("power saving", "ctn"), ("battery drain", "pn"),
    ("false alarms", "pn"), ("false parking alerts", "pn"),
    ("unnecessary event recordings", "pn"), ("overheating", "pn"),
]
S_GENERIC = [
    "Where is the {t} setting?", "Where can I find the {t} setting?", "Where do I find {the}{t}?",
    "Is there a setting for {the}{t}?", "Help me with the {t} setting",
    "How do I set up {the}{t}?", "Where's the option for {the}{t}?",
    "I can't find the {t} setting. Where is it?", "{t} settings", "How do I use {the}{t}?",
    "How does {the}{t} work?", "What does {the}{t} do?", "Tell me about the {t} setting",
    "How does {the}{t} work in this app?", "Does this dashcam have {t} settings?",
    "Walk me through {the}{t}", "Can you explain {the}{t}?",
]
# it·that·this 는 직전 결과나 오늘을 가리키는 말이 아니다 — reference·daysAgo 를 채우지 않는 예로 넣는다.
S_CHANGE = [
    "How do I change the {t}?", "How can I change the {t}?", "Where do I change the {t}?",
    "How do I adjust the {t}?", "I want to change the {t}. Where is it?", "How to change {t}",
    "Can I change the {t}?", "Which setting controls the {t}?", "How do I set the {t}?",
    "change {t}", "What is the {t} set to and how do I change it?",
    "The {t} seems wrong. How do I fix that?",
]
S_LEVEL = [
    "How do I lower the {t}?", "How do I turn down the {t}?",
    "The {t} is too high. How do I lower it?", "How do I increase the {t}?",
]
S_TOGGLE = [
    "How do I turn off {the}{t}?", "How do I turn on {the}{t}?", "How to turn off {t}",
    "how to enable {t}", "Can I disable {the}{t}?", "How do I disable {the}{t}?",
    "Can I turn off {the}{t}?", "How can I enable {the}{t}?", "I want to turn off {the}{t}. How?",
    "turn off {t}", "I don't need {the}{t}. Can I turn it off?",
    "Is {the}{t} on? How do I turn it off?",
]
S_PROBLEM = [
    "What should I change to prevent {t}?", "How do I stop {t}?", "How can I reduce {t}?",
    "What setting helps with {t}?", "Which setting fixes {t}?",
]
S_SPECIAL = {
    "SD card": ["How do I format the {t}?", "Where can I format the {t}?", "format {t}",
                "Walk me through formatting the {t}"],
    "memory card": ["How do I format the {t}?", "Where can I format the {t}?"],
    "firmware": ["How do I update the {t}?", "Where can I update the {t}?", "How do I check the {t} version?"],
    "firmware update": ["How do I run a {t}?", "Where is the {t}?"],
    "video download": ["How does {t} work in this app?", "Where is {t}?"],
}
S_SUFFIXES = [
    "", "", "", "", "", " in the app", " on my dashcam", " in settings", " in this app",
    " on this dashcam",
]

UNKNOWN_FIXED = [
    "Hi there", "Thanks", "Good morning", "How are you?", "Who are you?", "What can you do?",
    "What's your name?", "Are you a robot?", "Never mind", "asdf", "Test", "ok",
    "What is the meaning of life?", "Is there traffic on the highway?",
    "What's the traffic like on my way to work?", "Show me funny cat videos",
    "Play a YouTube video", "Record a video with my phone",
    "What movies are playing this evening?", "Open the camera app",
    "Turn on the air conditioning", "Lock the car doors", "Start the engine",
    "What's my tire pressure?", "When is my next oil change?",
    "How many miles per gallon does my car get?", "Check my calendar for tomorrow",
    "What's on my schedule today?", "Send a message to the group chat",
    "What's the stock price of Apple?", "Convert 50 miles to kilometers",
    "How many ounces are in a pound?", "Spell necessary", "Sing a song", "Buy a new dashcam",
    "Which dashcam is the best?", "Is this dashcam waterproof?",
    "What's the warranty on this dashcam?", "Where can I buy a rear camera?",
    "Who made this app?", "What's the news today?", "Read me a bedtime story",
    "What year is it?", "What day is Christmas?", "Find cheap flights to Tokyo",
    "Track my package", "Pay my parking ticket", "Find parking near me",
    "How much is parking downtown?", "Reserve a parking spot at the airport",
    "What's the best route to avoid traffic?", "How far is the nearest rest stop?",
    "Is the highway closed?", "Report an accident to the police",
    "Call my insurance company about the accident", "What should I do after a car accident?",
    "Summarize the news", "What's the speed limit on the freeway?", "Is my car due for service?",
    "Turn up the radio", "What song is this?", "Do I need an umbrella today?",
    # 날짜·시간대 낱말이 있어도 범위 밖이면 칸을 채우지 않는다.
    "What's the speed limit on this street?", "How fast is this car?", "Is this road closed?",
    "What does this warning light mean?", "What city is this?",
    "Is it going to snow this weekend?", "What should I eat this evening?",
    "What's on TV this evening?", "Any good movies out this week?",
    "How's traffic this morning?", "Did it rain yesterday?", "What's the date today?",
    "Who won the game yesterday?", "What happened in the news this morning?",
    "What time does the store close today?", "Is the bank open today?",
    "How cold was it yesterday morning?", "Is this a toll road?",
]
U_APPS = ["video editing", "photo editing", "navigation", "music", "parking", "weather", "fitness"]
U_CAR_LIGHTS = ["check engine", "tire pressure", "battery", "oil", "brake", "airbag"]
U_CITIES = ["Seattle", "Chicago", "Boston", "Denver", "Miami", "London", "Paris", "Tokyo", "Sydney", "Toronto"]
U_TEMPLATES = [
    ("What's the weather like in {a}?", U_CITIES, None),
    ("Will it rain in {a} tomorrow?", U_CITIES, None),
    ("What time is it in {a}?", U_CITIES, None),
    ("Navigate to {a}", U_CITIES, None),
    ("Give me directions to {a}", U_CITIES, None),
    ("How long does it take to drive to {a}?", U_CITIES, None),
    ("Recommend a good {b} in {a}", U_CITIES, ["restaurant", "hotel", "coffee shop", "museum", "bar"]),
    ("Find a {a} near me", ["gas station", "coffee shop", "parking garage", "car wash", "charging station",
                            "pharmacy", "restaurant", "hotel", "grocery store", "bank"], None),
    ("Call {a}", ["my wife", "my husband", "mom", "dad", "my boss", "John", "Sarah", "the office"], None),
    ("Text {a} that I'm running late", ["my wife", "my husband", "mom", "my boss", "Sarah"], None),
    ("Write an email to {a}", ["my boss", "my landlord", "the team", "my teacher"], None),
    ("Play {a}", ["some music", "jazz", "the radio", "my playlist", "a podcast", "the news"], None),
    ("What is {a} times {b}?", list(range(2, 30)), list(range(2, 13))),
    ("What's {a} plus {b}?", list(range(10, 200, 7)), list(range(3, 90, 4))),
    ("Translate {a} into {b}", ["good morning", "thank you", "where is the station", "how much is this"],
     ["Spanish", "French", "German", "Japanese", "Korean"]),
    ("Set an alarm for {a}", ["6:30 am", "7 am", "8:15 am", "5 pm", "noon"], None),
    ("Set a timer for {a} minutes", [5, 10, 15, 20, 30, 45], None),
    ("Remind me to {a} at {b}", ["call the dentist", "buy milk", "pick up the kids", "pay rent"],
     ["9 am tomorrow", "5 pm", "noon", "8 this evening"]),
    ("How much does {a} cost?", ["this dashcam", "a new SD card", "a rear camera", "gas", "car insurance", "an oil change"], None),
    ("How do I change {a}?", ["a flat tire", "my oil", "my wiper blades", "a headlight bulb", "my brake pads"], None),
    ("What's the capital of {a}?", ["France", "Japan", "Canada", "Brazil", "Egypt", "Australia", "Italy", "Kenya"], None),
    ("Tell me a {a}", ["joke", "story", "fun fact", "riddle"], None),
    ("Who won the {a} game?", ["Lakers", "Yankees", "Seahawks", "Arsenal", "Warriors", "Cubs"], None),
    ("Book a table for {a} at {b}", [2, 4, 6], ["7 pm", "8 pm", "noon"]),
    ("Order {a}", ["a pizza", "sushi", "a coffee", "groceries"], None),
    # 앱·폰·차량 일반 질문 — video·light·setting 같은 낱말이 있어도 블랙박스 설정이 아니다.
    ("Recommend a good {a} app", U_APPS, None),
    ("What's the best {a} app for iPhone?", U_APPS, None),
    ("How do I {a} on my phone?", ["edit a video", "free up storage", "update iOS", "turn on dark mode",
                                   "back up my photos", "record my screen"], None),
    ("How do I change my iPhone's {a}?", ["wallpaper", "ringtone", "font size", "passcode"], None),
    ("Why is my {a} light on?", U_CAR_LIGHTS, None),
    ("Why has my {a} light been on since {b}?", U_CAR_LIGHTS, ["this morning", "yesterday", "last week"]),
    ("How do I reset the {a} light?", ["tire pressure", "oil change", "maintenance", "check engine"], None),
    ("My car {a}. What's wrong?", ["makes a noise when I brake", "won't start", "pulls to the left",
                                   "smells like burning"], None),
    ("How do I {a}?", ["jump start my car", "check my tire pressure", "pair my phone with my car",
                       "reset my car's clock"], None),
]


def check_swift_schema():
    """KEYS·ENUMS 가 Swift 스키마와 어긋나면 멈춘다."""
    prompt = (ROOT / "Hub/Domain/UseCases/AIChat/HubQueryPrompt.swift").read_text()
    block = re.search(r"static let schemaFields.*?= \[(.*?)\n  \]", prompt, re.S)
    assert block, "HubQueryPrompt.schemaFields 를 찾지 못했다"
    swift_keys = re.findall(r'\("(\w+)",', block.group(1))
    assert swift_keys == KEYS, f"schemaFields 순서가 다르다: {swift_keys}"
    # 앱의 전용 지시문은 키 목록 앞뒤 문장을 리터럴로 들고 있다 — 둘 다 SYSTEM_PROMPT 와 같아야 한다.
    head, tail = SYSTEM_PROMPT.split(", ".join(KEYS))
    for part in (head.split("Answer with")[0], "Answer with" + head.split("Answer with")[1], tail):
        assert f'"{part}"' in prompt, f"HubQueryPrompt.dedicatedInstructions 가 다르다: {part!r}"
    query = (ROOT / "Hub/Domain/Entities/AIChat/HubQuery.swift").read_text()
    names = {"intent": "HubQueryIntent", "period": "HubDayPeriod", "event": "HubEventFilter",
             "reference": "HubQueryReference"}
    for key, name in names.items():
        body = re.search(rf"enum {name}: String, CaseIterable \{{(.*?)\n\}}", query, re.S)
        assert body, f"{name} 을 찾지 못했다"
        cases = re.findall(r"^  case (\w+)$", body.group(1), re.M)
        assert cases == ENUMS[key], f"{name} 값이 다르다: {cases}"


def ordinal(n):
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def pick_day(rng):
    """(종류, 글, 칸). 요일 표현은 daysAgo 를 비운다."""
    kind = rng.choices(
        ["none", "today", "yesterday", "before", "ndays", "date", "weekday"],
        weights=[20, 16, 24, 8, 10, 15, 7])[0]
    if kind == "none":
        return kind, "", {}
    if kind == "today":
        return kind, "today", {"daysAgo": 0}
    if kind == "yesterday":
        return kind, "yesterday", {"daysAgo": 1}
    if kind == "before":
        text = rng.choice(["the day before yesterday", "two days ago", "2 days ago"])
        return kind, text, {"daysAgo": 2}
    if kind == "ndays":
        n = rng.randint(3, 14)
        word = NUM_WORDS.get(n)
        text = f"{word} days ago" if word and rng.random() < 0.4 else f"{n} days ago"
        return kind, text, {"daysAgo": n}
    if kind == "date":
        month = rng.randint(1, 12)
        day = rng.randint(1, DAYS_IN_MONTH[month - 1])
        name = MONTHS[month - 1]
        text = rng.choice([
            f"{name} {day}", f"{name} {day}", f"{name} {ordinal(day)}", f"{name[:3]} {day}",
            f"the {ordinal(day)} of {name}", f"{day} {name}"])
        return kind, text, {"month": month, "dayOfMonth": day}
    weekday = rng.choice(WEEKDAYS)
    return kind, rng.choice([f"last {weekday}", weekday]), {}


def needs_on(kind, text):
    return kind == "date" or (kind == "weekday" and not text.startswith("last"))


def render_clock(rng, hour, minute, period):
    """(시각 부사구, 전치사 없는 표기, 시간대 낱말을 품었는지). 라벨은 24시간제, 글은 여러 표기.

    전치사 없는 표기는 혼자 써도 시각으로 읽히는 것만 준다(없으면 None).
    """
    h12 = hour % 12 or 12
    mm = f":{minute:02d}" if minute else ""
    styles = ["ampm", "ampm"]
    if hour >= 13 or minute:
        styles.append("24h")
    # am·pm 없는 12시간 표기는 오후 시간대 낱말이 있을 때만 오후로 읽는다.
    if period in PM_PERIODS or 1 <= hour < 12:
        styles.append("bare")
    if hour == 12 and minute == 0 and period in ("any", "afternoon"):
        styles += ["noon"] * 3
    if period in ("morning", "afternoon", "evening"):
        styles.append("inword")
    style = rng.choice(styles)
    if style == "noon":
        return rng.choice(["at noon", "around noon"]), "noon", False
    if style == "ampm":
        mark = "am" if hour < 12 else "pm"
        mark = rng.choice([f" {mark}", f" {mark}", mark, f" {mark.upper()}", f" {mark[0]}.m."])
        text = f"{h12}{mm}{mark}"
    elif style == "24h":
        text = f"{hour}:{minute:02d}" if hour else f"00:{minute:02d}"
    else:
        text = f"{h12}{mm}"
    prep = rng.choice(["at", "at", "around", "at about", "at around", "about"])
    if style == "inword":
        return f"{prep} {text} in the {period}", None, True
    return f"{prep} {text}", text if style in ("ampm", "24h") else None, False


def make_when(rng):
    """언제를 말하는 구절. frm 은 명사 뒤, adv 는 문장 뒤, np 는 출퇴근 명사구에 쓴다.

    frm0 은 시각을 뺀 frm, raw 는 명사 앞에 붙일 수 있는 시각 표기다("the 4:45 pm clip").
    """
    kind, day, fields = pick_day(rng)
    period = rng.choices(
        ["any", "morning", "afternoon", "evening", "night", "morningCommute", "eveningCommute"],
        weights=[50, 9, 8, 8, 4, 11, 10])[0]
    if period == "night" and kind == "today":
        period = "any"
    clock, raw, inword = "", None, False
    if rng.random() < 0.35:
        hour = rng.randint(*HOURS[period])
        minute = rng.choice(MINUTES)
        if period in ("any", "afternoon") and rng.random() < 0.06:
            hour, minute = 12, 0
        clock, raw, inword = render_clock(rng, hour, minute, period)
        fields.update(hour=hour, minute=minute)
    if period != "any":
        fields["period"] = period
    day_adv = ("on " + day if needs_on(kind, day) else day) if kind != "none" else ""
    day_frm = "from " + day if kind != "none" else ""
    np = None
    if period == "any" or inword:
        adv0, frm0 = day_adv, day_frm
    elif period in ("morning", "afternoon", "evening"):
        phrase = {
            "none": f"in the {period}", "today": f"this {period}",
            "yesterday": f"yesterday {period}", "weekday": f"{day} {period}",
        }.get(kind)
        if phrase is None:
            of_form = kind == "date" and rng.random() < 0.4
            phrase = f"the {period} of {day}" if of_form else f"{day} in the {period}"
        adv0 = "on " + phrase if needs_on(kind, day) else phrase
        frm0 = phrase if kind == "none" else "from " + phrase
    elif period == "night":
        late = rng.choice(["at night", "late at night"])
        phrase = {
            "none": late, "weekday": f"{day} night",
            "yesterday": rng.choice(["yesterday late at night", "late at night yesterday"]),
        }.get(kind) or f"{day} {late}"
        adv0 = "on " + phrase if needs_on(kind, day) else phrase
        frm0 = phrase if phrase.startswith(("at ", "late ")) else "from " + phrase
    else:
        morning = period == "morningCommute"
        base = "morning commute" if morning else "evening commute"
        part = "morning" if morning else "evening"
        noun = rng.choice([
            base, "commute to work" if morning else "commute home",
            "drive to work" if morning else "drive home from work"])
        way = rng.choice(
            ["on my way to work", "on the way to work", f"during my {base}", f"on my {base}"]
            if morning else
            ["on my way home from work", "on the way home from work", f"during my {base}", f"on my {base}"])
        if kind == "none":
            np, adv0 = f"my {noun}", way
        elif kind == "today":
            np = rng.choice([
                f"this {part}'s commute", f"today's {base}", f"my {noun} today", f"my {noun} this {part}"])
            adv0 = rng.choice([f"{way} today", f"{way} this {part}", f"during this {part}'s commute"])
        elif kind == "yesterday":
            np = rng.choice([f"yesterday's {base}", f"my {noun} yesterday"])
            adv0 = rng.choice([f"{way} yesterday", f"during yesterday's {base}"])
        else:
            np = f"{day}'s {base}" if kind == "weekday" and rng.random() < 0.4 else f"my {noun} {day_adv}"
            adv0 = f"{way} {day_adv}"
        frm0 = f"from {np}"
        np = f"{np} {clock}".strip()
    adv, frm = adv0, frm0
    if clock:
        # 시각이 놓이는 자리를 섞는다 — 뒤("yesterday at 8 pm"), 앞("from 8 pm yesterday"), 전치사 없이("yesterday 7am").
        roll = rng.random()
        movable = adv0 and not inword and period in ("any", "morning", "afternoon", "evening")
        if movable and roll < 0.25:
            adv = f"{clock} {adv0}"
            frm = f"from {raw} {adv0}" if raw else adv
        elif raw and adv0 and roll < 0.4:
            adv, frm = f"{adv0} {raw}", f"{frm0} {raw}"
        else:
            adv = f"{adv0} {clock}"
            frm = f"from {raw}" if raw and not frm0 and roll < 0.7 else f"{frm0} {clock}"
    return {
        "frm": frm.strip(), "adv": adv.strip(), "np": np, "frm0": frm0, "raw": raw, "fields": fields}


def build_video(rng):
    when = make_when(rng)
    fields = {"intent": "video", **when["fields"]}
    impact = rng.random() < 0.3
    if impact:
        fields["event"] = "impact"
    frm, adv = when["frm"], when["adv"]
    shape = rng.random()
    if impact and shape < 0.2:
        sep = rng.choice([", ", ". "])
        tail = rng.choice(V_NARRATIVE_TAILS)
        tail = tail if sep == ", " else tail[0].upper() + tail[1:]
        return f"{rng.choice(V_NARRATIVES)} {adv}".strip() + sep + tail, fields
    if shape < 0.32:
        return f"{rng.choice(V_EXISTS_IMPACT if impact else V_EXISTS)} {frm}?", fields
    if shape < 0.42 and adv and not impact:
        return rng.choice(V_RECORDED).format(adv=adv), fields
    if shape < 0.5:
        noun = rng.choice(
            ["accident video", "crash footage", "impact video"] if impact
            else ["video", "footage", "recording", "dashcam video", "clip"])
        return f"{noun} {frm}", fields
    verb = rng.choice(V_VERBS)
    noun = rng.choice(V_IMPACT_NOUNS if impact else V_NOUNS)
    # where·when 절 뒤에는 from 없이 붙인다 ("…slammed on the brakes yesterday").
    tail = adv if " where " in noun or " when " in noun else frm
    if when["raw"] and noun in V_NOUNS and rng.random() < 0.25:
        noun, tail = noun.replace("the ", f"the {when['raw']} ", 1), when["frm0"]
    question = f"{verb} {noun} {tail}".strip()
    return question + ("?" if verb.startswith(("Can", "Could")) else ""), fields


def build_drive(rng):
    when = make_when(rng)
    fields = {"intent": "drive", **when["fields"]}
    impact = rng.random() < 0.3
    if impact:
        fields["event"] = "impact"
    frm, adv, np = when["frm"], when["adv"], when["np"]
    if rng.random() < 0.4:
        modes = ["both"] if np else ["both", "dest"] if impact else ["both", "dest", "origin", "home"]
        mode = rng.choice(modes)
        origin, destination = rng.sample(PLACES, 2)
        if mode == "home":
            origin = rng.choice([p for p in PLACES if p != "home"])
            destination = "home"
        if mode in ("both", "origin", "home"):
            fields["origin"] = origin
        if mode in ("both", "dest", "home"):
            fields["destination"] = destination
        template = rng.choice((D_IMPACT_PLACES if impact else D_PLACES)[mode])
        return template.format(o=origin, d=destination, adv=adv), fields
    if impact:
        return rng.choice(D_IMPACT).format(adv=adv, frm=frm), fields
    if np and rng.random() < 0.5:
        return rng.choice(D_COMMUTE).format(np=np), fields
    return rng.choice(D_PLAIN).format(adv=adv, frm=frm), fields


def build_reference(rng):
    intent = rng.choice(["video", "drive"])
    base = rng.choice(REF_VIDEO if intent == "video" else REF_DRIVE)
    prefix = rng.choice(["", "", "", "Now ", "OK, ", "Then ", "Please ", "And "])
    if prefix and not base.startswith("I "):
        base = base[0].lower() + base[1:]
    return prefix + base, {"intent": intent, "reference": "previous"}


def build_settings(rng):
    topic, flags = rng.choice(TOPICS)
    templates = list(S_SPECIAL.get(topic, []))
    if "p" in flags:
        templates += S_PROBLEM
    else:
        templates += S_GENERIC
        if "c" in flags:
            templates += S_CHANGE
            if any(word in topic for word in ("sensitivity", "volume", "brightness")):
                templates += S_LEVEL
        if "t" in flags:
            templates += S_TOGGLE
    question = rng.choice(templates).format(t=topic, the="" if "n" in flags else "the ")
    suffix = rng.choice(S_SUFFIXES)
    if suffix and question.endswith("?") and question.count("?") == 1 and ". " not in question:
        question = question[:-1] + suffix + "?"
    return question, {"intent": "settingsHelp", "topic": topic}


def build_unknown(rng):
    if rng.random() < 0.35:
        return rng.choice(UNKNOWN_FIXED), {"intent": "unknown"}
    template, first, second = rng.choice(U_TEMPLATES)
    question = template.format(a=rng.choice(first), b=rng.choice(second) if second else "")
    return question, {"intent": "unknown"}


BUILDERS = {
    "video": build_video, "drive": build_drive, "reference": build_reference,
    "settingsHelp": build_settings, "unknown": build_unknown,
}


def normalize(question):
    return question.lower().rstrip("?.! ")


def polish(rng, question, fields):
    """공백을 정리하고, 일부는 소문자·문장부호 없는 입력으로 바꾼다."""
    question = re.sub(r"\s+", " ", question).strip()
    question = re.sub(r"\s+([?.,])", r"\1", question)
    if rng.random() < 0.12:
        question = question.lower().rstrip("?.")
        for key in STRING_KEYS:
            if fields.get(key):
                fields[key] = fields[key].lower()
    return question, fields


def user_prompt(rng, question, with_previous):
    """HubQueryPrompt.userPrompt 와 같은 형식."""
    today = datetime(2026, 1, 1) + timedelta(minutes=rng.randrange(2 * 365 * 24 * 60))
    lines = [f"today: {today:%Y-%m-%d} ({WEEKDAY_ABBR[today.weekday()]}) {today:%H:%M}"]
    if with_previous:
        start = (today - timedelta(days=rng.randint(0, 10))).replace(
            hour=rng.randint(0, 22), minute=rng.randint(0, 59))
        if start > today:
            start -= timedelta(days=1)
        if rng.random() < 0.6:
            end = min(start + timedelta(minutes=rng.randint(5, 90)), start.replace(hour=23, minute=59))
            line = f"previous result: drive {start:%Y-%m-%d %H:%M}-{end:%H:%M}"
            if rng.random() < 0.5:
                line += f", event {start + (end - start) * rng.random():%H:%M}"
        else:
            line = f"previous result: video {start:%Y-%m-%d %H:%M}"
        lines.append(line)
    lines.append(f"question: {question}")
    return "\n".join(lines)


def target(fields):
    full = {key: fields.get(key, DEFAULTS.get(key)) for key in KEYS}
    return json.dumps(full, separators=(",", ":"), ensure_ascii=False)


def validate(question, answer):
    """조립 실수를 잡는다 — 키 순서, 값 범위, 글자 칸이 질문 안에 있는지."""
    fields = json.loads(answer)
    assert list(fields) == KEYS, question
    for key, allowed in ENUMS.items():
        assert fields[key] in allowed, (question, key)
    assert (fields["topic"] is not None) == (fields["intent"] == "settingsHelp"), question
    assert (fields["hour"] is None) == (fields["minute"] is None), question
    if fields["hour"] is not None:
        assert 0 <= fields["hour"] <= 23 and 0 <= fields["minute"] <= 59, question
    assert (fields["month"] is None) == (fields["dayOfMonth"] is None), question
    assert fields["month"] is None or fields["daysAgo"] is None, question
    for key in STRING_KEYS:
        assert fields[key] is None or fields[key] in question, (question, key)
    if fields["intent"] == "unknown":
        assert all(fields[key] == DEFAULTS.get(key) for key in KEYS[1:]), question


def generate(count, seed):
    rng = random.Random(seed)
    # 평가셋 세 개 모두 학습 문장에서 뺀다 — 독립셋 문장이 템플릿과 우연히 같을 수 있다
    eval_files = [ROOT / "scripts/fixtures/ai_chat_eval_en.json"] + sorted(
        Path(__file__).resolve().parent.glob("eval_independent*_en.json"))
    held_out = {normalize(case["q"]) for path in eval_files for case in json.loads(path.read_text())}
    rows, seen, skipped = [], Counter(), 0
    for kind, share in QUOTAS.items():
        wanted, made, attempts = round(count * share), 0, 0
        while made < wanted:
            attempts += 1
            assert attempts < wanted * 200, f"{kind}: {made}/{wanted} 에서 새 문장이 나오지 않는다"
            question, fields = polish(rng, *BUILDERS[kind](rng))
            key = normalize(question)
            if key in held_out:
                skipped += 1
                continue
            if seen[key] >= MAX_REPEATS.get(kind, 1):
                continue
            seen[key] += 1
            with_previous = rng.random() < (0.8 if kind == "reference" else 0.2)
            answer = target(fields)
            validate(question, answer)
            rows.append({"kind": kind, "question": question, "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt(rng, question, with_previous)},
                {"role": "assistant", "content": answer},
            ]})
            made += 1
    rng.shuffle(rows)
    assert not held_out & set(seen), "평가셋 문항이 학습 데이터에 들어갔다"
    return rows, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--count", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "data")
    args = parser.parse_args()

    check_swift_schema()
    rows, skipped = generate(args.count, args.seed)
    valid_count = max(1, len(rows) // 20)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, part in (("valid", rows[:valid_count]), ("train", rows[valid_count:])):
        with (args.out / f"{name}.jsonl").open("w") as file:
            for row in part:
                file.write(json.dumps({"messages": row["messages"]}, ensure_ascii=False) + "\n")

    answers = [json.loads(row["messages"][2]["content"]) for row in rows]
    filled = Counter(
        key for answer in answers for key in KEYS[1:] if answer[key] != DEFAULTS.get(key))
    previous = sum("previous result:" in row["messages"][1]["content"] for row in rows)
    print(f"rows {len(rows)} (train {len(rows) - valid_count}, valid {valid_count}) -> {args.out}")
    print("kind  ", dict(Counter(row["kind"] for row in rows)))
    print("intent", dict(Counter(answer["intent"] for answer in answers)))
    print("filled", dict(filled))
    print(f"previous-result lines {previous}, unique questions {len({row['question'] for row in rows})}")
    print(f"eval overlap 0 (skipped {skipped} candidates)")
    for row in rows[:24]:
        print(f"  {row['question']}\n    {row['messages'][2]['content']}")


if __name__ == "__main__":
    main()
