# Level 3 capstone: a smaller prompt

Goal: shorten the prompt without losing any test.

| | v1 | v2 | v3 |
|---|---|---|---|
| Prompt tokens | 2100 | 1957 | 1785 (-15%) |
| output_check | 10/10 | 10/10 | 10/10 |
| tricky_inputs saves | 19/19 | 19/19 | 19/19 |
| injection_inputs | 11/11 | 11/11 | 11/11 |

## What I changed
- Merged the five "cannot do" bullets into two with the same rules.
- Merged Honesty into Using tools; merged Health bullets.
- Moved Context (the date) to the bottom so the long text above it can stay cached.

## What I learned
- Test on the same clean data. My first v2 run scored 7/10 only because earlier tests had filled
  the database, which made the plans longer than 3 sentences.
- The prompt was already tight: a careful rewrite saved only 7%. The bigger saving is caching (about 65% cheaper per message).
- I stopped after one round. More cuts would save a few tokens each and risk breaking a rule.

- v3: removed two examples, a repeated sentence about spoken times, and the tool-by-tool explanations
  (the tool definitions already describe them).