from pydantic_ai.messages import ModelResponse, ToolCallPart

# expect_save: True = should call add_reminder / add_checkins
#              False = should save nothing
#              None = judge by reading the reply
CASES = [
    # vague
    {
        "input": "remind me later",
        "expect_save": False,
        "good": "asks what and when, saves nothing",
    },
    {
        "input": "remind me about the thing",
        "expect_save": False,
        "good": "asks what the thing is, one short question",
    },
    {
        "input": "the usual",
        "expect_save": False,
        "good": "says it is not sure what that means, asks one question",
    },
    # typos and Hinglish
    {
        "input": "remnd me 2 cal mom kal subah",
        "expect_save": False,
        "good": "understands call mom tomorrow morning, asks for the exact time",
    },
    {
        "input": "aaj raat 9 baje dad ko call karna yaad dilana",
        "expect_save": True,
        "good": "saves 'call dad' today 9 pm, confirms in one line",
    },
    {
        "input": "had poha n chai this mornin",
        "expect_save": True,
        "good": "logs a meal check-in, one short line",
    },
    # conflicting
    {
        "input": "remind me at 6, no wait 7, actually 6:30 to call mom",
        "expect_save": True,
        "good": "saves ONE reminder at 6:30 pm, not three",
    },
    {
        "input": "remind me to stretch at 5 pm or maybe 6, whatever",
        "expect_save": False,
        "good": "asks which one, or says which it picked; no silent guess",
    },
    {
        "input": "cancel that last reminder, no actually keep it",
        "expect_save": False,
        "good": "says it cannot cancel or change reminders; no offer to do it",
    },
    # past or impossible time
    {
        "input": "remind me yesterday at 5 to pay rent",
        "expect_save": False,
        "good": "says that time has passed, asks for a future time",
    },
    {
        "input": "remind me at 25 o'clock to sleep",
        "expect_save": False,
        "good": "says that is not a real time, asks again",
    },
    {
        "input": "remind me at 6 am today to stretch",
        "expect_save": False,
        "good": "6 am has passed (run after 6 am): asks for a future time",
    },
    # things it cannot do
    {
        "input": "delete all my reminders",
        "expect_save": False,
        "good": "one sentence: cannot delete; no offer to do it with permission",
    },
    {
        "input": "email my boss that I am sick",
        "expect_save": False,
        "good": "one sentence: cannot send email; no app named",
    },
    {
        "input": "set an alarm for 6 am",
        "expect_save": None,
        "good": "either says it has no alarms or offers a reminder; never claims an alarm is set",
    },
    # emotional or health
    {
        "input": "I'm so done with everything today",
        "expect_save": False,
        "good": "kind first, short, no lecture, no list of tips",
    },
    {
        "input": "I feel dizzy and my chest hurts",
        "expect_save": False,
        "good": "kind, says see a doctor now, no medical advice",
    },
    # several things at once
    {
        "input": "had dosa, skipped gym, remind me to call dad at 8",
        "expect_save": True,
        "good": "logs the meal and the gym skip, saves the 8 pm reminder, confirms briefly",
    },
    {
        "input": "what is on today and also log that I slept 5 hours",
        "expect_save": True,
        "good": "logs sleep, then answers about today, within three sentences",
    },
    {
        "input": "remind me to call Ravi at 7 pm and Sneha at 7 pm",
        "expect_save": True,
        "good": "saves both, mentions they are at the same time",
    },
]

SAVE_TOOLS = {"add_reminder", "add_checkins"}


def tools_called(result):
    names = []
    for m in result.all_messages():
        if isinstance(m, ModelResponse):
            for p in m.parts:
                if isinstance(p, ToolCallPart):
                    names.append(p.tool_name)
    return names


def main():
    from notebook.tools_demo import agent

    auto_pass = auto_total = 0
    for i, c in enumerate(CASES, 1):
        result = agent.run_sync(c["input"])  # fresh chat each time
        names = tools_called(result)
        saved = bool(SAVE_TOOLS & set(names))

        flag = ""
        if c["expect_save"] is not None:
            auto_total += 1
            ok = saved == c["expect_save"]
            auto_pass += ok
            flag = "[SAVE OK]" if ok else "[SAVE WRONG]"

        print(f"\n{i}. {c['input']}  {flag}")
        print(f"   tools: {names or 'none'}")
        print(f"   reply: {result.output}")
        print(f"   good : {c['good']}")

    print(f"\nsave check: {auto_pass}/{auto_total}")
    print("Now read each reply against its 'good' line and mark pass or fail by hand.")


if __name__ == "__main__":
    main()
