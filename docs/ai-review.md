# AI-assisted testing review (M0.6)

Goal of this module: use an AI assistant to write tests, then review what it wrote instead of trusting it.

## What I asked for

The assistant wrote `test/test_api.py` for the reminders and check-ins API. It covers:

- creating a reminder returns 201 with an `id`
- the list is empty at the start
- the list shows a reminder after it is created
- a lead time of 300 returns 422 and nothing is saved
- deleting a reminder works, and deleting it again returns 404
- a non-numeric id returns 422
- creating a check-in returns 201
- a bad check-in `kind` returns 422 and nothing is saved

## What I found when I reviewed it

| Finding | What happened | What I did |
|---|---|---|
| Undefined name | The tests used a `REMINDER` constant that was never defined, so they failed before testing anything. | Added the constant at the top of the file. |
| Test setup | The tests need a clean, separate database for each test. The generated file did not set that up. | Wrote `conftest.py`: it points the app at `friend_test` and truncates the tables before each test. |
| Real bug found by a test | The delete test failed with `200 == 204`. The route returned 200 because `status_code=204` was missing in the decorator. | Fixed the route. |
| Real bug found while running the API | Route functions had the same names as the database functions they imported, which caused a `RecursionError`. | Renamed the route functions. |

TODO: add any other wrong or missing pieces you found in `test_api.py`, such as a wrong status code, an unrealistic example, or a test that could never fail.

## Breaking the tests on purpose

I changed the code to check that the tests fail when something is wrong. One of these runs failed with `204 == 404`. That was expected, and it showed the delete-then-404 test checks something real.

TODO: list each change you made, the test that failed, and the message. If a change did not make any test fail, write it here as a gap in the tests.

## What I learned

1. Read generated tests line by line. A test that cannot run or cannot fail proves nothing.
2. Run the tests against the real design, from `docs/api.md`, and check each expected status code against it.
3. Tests that write to a database need their own database and a clean state, or they affect each other.
4. A test that fails for a good reason is the best use of the AI's output.

## What I would do differently

TODO: one or two sentences in your own words.
