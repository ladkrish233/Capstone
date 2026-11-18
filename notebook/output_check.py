"""Run the 10 output tests through the friend and flag replies that are not speakable.

Run from the project folder:  python -m notebook.output_check
Before running, save a few reminders for today so the time tests mean something.
"""

import re

# (message, max sentences allowed)
TESTS = [
    ("What can you do?", 3),
    ("Plan my whole week", 3),
    ("Give me tips to sleep better", 3),
    ("Compare gym in the morning versus evening", 3),
    ("Plan my day", 3),
    ("When is my next reminder?", 3),
    ("List all my reminders", 3),
    ("Explain how you work in detail", 4),  # detail was asked for, so one more sentence
    ("Give me a workout plan for the week", 3),
    ("Summarise everything I logged today", 3),
]

MAX_WORDS_PER_SENTENCE = 25

LIST_LINE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.MULTILINE)
CLOCK_TIME = re.compile(r"\b\d{1,2}:\d{2}\b")
ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def check(reply: str, max_sentences: int) -> list[str]:
    """Return a list of problems. An empty list means the reply passes."""
    problems = []

    if LIST_LINE.search(reply):
        problems.append("uses a bullet or numbered list")
    if re.search(r"(\*\*|__|`|^#{1,6}\s|\|)", reply, re.MULTILINE):
        problems.append("uses markdown (bold, code, heading or table)")
    if CLOCK_TIME.search(reply):
        problems.append("writes a clock time like 18:00")
    if ISO_DATE.search(reply):
        problems.append("writes a date like 2026-11-12")

    sentences = split_sentences(reply)
    if len(sentences) > max_sentences:
        problems.append(f"{len(sentences)} sentences (max {max_sentences})")
    longest = max((len(s.split()) for s in sentences), default=0)
    if longest > MAX_WORDS_PER_SENTENCE:
        problems.append(
            f"a sentence has {longest} words (max {MAX_WORDS_PER_SENTENCE})"
        )
    if reply.count("?") > 1:
        problems.append("asks more than one question")

    return problems


def main() -> None:
    # Imported here so the check() function can be tested without the agent.
    from notebook.tools_demo import agent

    passed = 0
    for number, (message, max_sentences) in enumerate(TESTS, start=1):
        result = agent.run_sync(message)  # fresh chat each time: no history
        reply = result.output
        problems = check(reply, max_sentences)
        status = "PASS" if not problems else "FAIL"
        passed += not problems
        print(f"\n{number}. [{status}] {message}")
        print(f"   {reply}")
        for p in problems:
            print(f"   - {p}")

    print(f"\n{passed}/{len(TESTS)} passed")


if __name__ == "__main__":
    main()
