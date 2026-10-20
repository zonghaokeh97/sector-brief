# Sector Brief

A daily business briefing organized the way consultants think about industries: 7 sectors and 28 sub-industries, each with an industry profile, company context, and the day's news. A daily 10-question quiz with spaced review helps the knowledge stick.

Live at **brief.zonghaokeh.com**. Built by [Zong Hao Keh](https://zonghaokeh.com).

## How it works

- Each morning at 7:00 am PT, an AI research run gathers 15–20 business stories, writes the summaries, "why it matters" notes and quiz, and commits them to `data/`.
- The site is a single static page (`index.html`) that reads those JSON files. No server, no build step.
- Quiz progress is saved in each visitor's own browser. Nothing is collected.

Summaries are AI-generated from the linked sources and may contain errors.

## Data layout

| File | Contents |
| --- | --- |
| `data/index.json` | Latest edition date and the list of monthly files |
| `data/reference.json` | Sector overviews and recaps, sub-industry profiles, company profiles |
| `data/stories/YYYY-MM.json` | Stories for that month, keyed by `YYYY-MM-DD-NN` |
| `data/quizzes/YYYY-MM.json` | Daily quizzes for that month, keyed by date |

New editions are merged with `python3 scripts/add_edition.py payload.json`, which validates the content before writing anything.
