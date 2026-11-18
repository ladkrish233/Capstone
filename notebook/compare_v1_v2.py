import os
import re
import subprocess
import sys

VERSIONS = ["prompts/friend_v2.md", "prompts/friend_v3.md"]
WIPE = [
    "docker",
    "compose",
    "exec",
    "-T",
    "db",
    "psql",
    "-U",
    "postgres",
    "-d",
    "friend",
    "-c",
    "TRUNCATE reminders, checkins RESTART IDENTITY",
]


def run(module, prompt):
    subprocess.run(WIPE, capture_output=True)
    env = {**os.environ, "PROMPT_FILE": prompt, "PYTHONIOENCODING": "utf-8"}
    p = subprocess.run(
        [sys.executable, "-m", module],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return p.stdout + p.stderr


def find(pattern, text):
    m = re.search(pattern, text)
    return m.group(0) if m else "n/a"


print("This wipes ALL reminders and check-ins. Test data only.")
if input("Type yes to continue: ").strip().lower() != "yes":
    sys.exit()

for prompt in VERSIONS:
    out_check = run("notebook.output_check", prompt)
    tricky = run("notebook.tricky_inputs", prompt)
    print(f"\n{prompt}")
    print("  output_check :", find(r"\d+/\d+ passed", out_check))
    print("  tricky saves :", find(r"save check: \d+/\d+", tricky))
    print("  tokens       :", find(r"tokens in:.*", tricky))
