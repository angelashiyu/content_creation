# genai-post-project

Drafts Mastodon posts and replies for a GenAI marketing-intelligence brand. A post is generated from a Notion page that describes the company, sent to Telegram for a human to approve or reject, and published to Mastodon only after approval.

Text generation goes through [OpenRouter](https://openrouter.ai). Images come from a fine-tuned model on [Replicate](https://replicate.com).

## How the post pipeline works

1. `notion_fetch.py` reads the Notion page named in `config.json`.
2. `retrieval.py` chunks the text and keeps the chunks that best match a fixed query, scored by keyword overlap.
3. `post_generator.py` asks the LLM for one post about "AI SEO", 80 words at most, in the brand voice defined in `llm.py`.
4. `approval_bot.py` sends the draft to a Telegram chat with Approve and Reject buttons and waits up to 30 minutes.
5. On approve, `mastodon_post.py` publishes the post. On reject, the bot asks for a reason and the pipeline prints it.

## Setup

Requires Python 3.10 or newer (developed on 3.12).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the repo root. It is gitignored.

```bash
MASTODON_BASE_URL=https://your.instance
MASTODON_ACCESS_TOKEN=...
OPENROUTER_API_KEY=...
NOTION_TOKEN=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
REPLICATE_API_TOKEN=...   # only needed for image_gen_replicate.py
DRY_RUN=true              # the pipeline prints an approved post instead of publishing it
```

Where each credential comes from:

| Service | What to do |
|---|---|
| Mastodon | Preferences → Development → New application. Scopes: `read`, `write:statuses`, `write:media`. |
| OpenRouter | Create an API key. |
| Notion | Create an internal integration, share the page with it, and put the page ID in `config.json`. |
| Telegram | Create a bot with @BotFather and send it a message so it is allowed to message you. `TELEGRAM_CHAT_ID` is the ID of that chat. |
| Replicate | Create an API token. The model ID and trigger word are set at the top of `image_gen_replicate.py`. |

Two optional variables:

| Variable | Purpose |
|---|---|
| `OPENROUTER_MODEL` | Overrides the default model in `llm.py` (`nvidia/nemotron-3-super-120b-a12b:free`). Free models on OpenRouter get retired; if calls start returning 404, set this to a current model. |
| `EVAL_JUDGE_MODEL` | Model that scores eval output. Defaults to the generator model. |

`mastodon_fetch.py` skips statuses written by the account in `MY_ACCT`. Change it if you run this under a different Mastodon account.

## Usage

### Post pipeline

```bash
python pipeline.py
```

With `DRY_RUN=true`, an approved post is printed and nothing is published. Otherwise it is published with your account's default visibility.

### Reply drafts

```bash
python reply_ai_seo.py
```

Searches Mastodon for recent "AI SEO" statuses, falling back to the `#AISEO` and `#AI_SEO` hashtag timelines, then drafts a reply to the first five and prints them. Nothing is posted.

### Image post

```bash
python image_gen_replicate.py
```

**This posts publicly.** It generates an image on Replicate and posts it to Mastodon with a test caption. Edit the `__main__` block before running it.

### Single steps

`mastodon_fetch.py`, `generate_replies.py` and `mastodon_post.py` can each be run directly to try one step. None of them posts: `mastodon_post.py` runs a dry run that only prints.

## Evals

`evals/` measures output quality without posting anything. Run it from the repo root.

```bash
python -m evals.run retrieval            # no LLM calls
python -m evals.run posts --n 3          # 3 samples per case
python -m evals.run replies --model <generator> --judge-model <judge>
python -m evals.run all --no-judge       # deterministic checks only
```

| Suite | What runs | What is scored |
|---|---|---|
| `posts` | 7 topics through the same retrieval and prompt as the pipeline | Checks: word limit, 500 characters, at most 2 hashtags, no hype or "DM me", no "Here's your post" wrapper. Judge: grounded, voice, value, on-topic. |
| `replies` | 6 statuses: a question, a skeptic, a vague one, one in Spanish, spam, and a prompt injection | Checks: valid JSON, IDs match, 450 characters, not salesy, no prompt leak, spam and injection flagged `requires_review`. Judge: relevant, value, not salesy, voice. |
| `retrieval` | 7 labelled queries against each chunk mode at k = 1, 3, 6 | Recall, and the share of the page passed to the LLM. |

The judge is an LLM that scores each criterion from 1 to 5. A sample passes when every check passes and every judge score is 3 or higher.

Cases live in `evals/cases/` as JSON. Full records, including each generated text and the judge's notes, are written to `evals/results/`, which is gitignored.

Things to know when reading the numbers:

- LLM output varies between runs. Use `--n 3` or more before trusting a pass rate.
- By default the generator model judges its own output. Set `EVAL_JUDGE_MODEL` to a stronger model.
- The retrieval cases expect phrases from the current Notion page. Update `evals/cases/retrieval.json` if the page changes.
- The company context is fetched from Notion on each run. Pass `--context-file page.txt` to use a saved copy instead.

## Project layout

| File | Role |
|---|---|
| `pipeline.py` | End-to-end post pipeline |
| `approval_bot.py` | Telegram approve / reject bot |
| `notion_fetch.py` | Reads the Notion page in `config.json` as plain text |
| `chunking.py` | Character, paragraph and sentence chunkers |
| `retrieval.py` | Keyword-overlap retrieval and `build_context()` |
| `llm.py` | OpenRouter client, default model and brand voice |
| `post_generator.py` | Post prompt |
| `generate_replies.py` | Reply prompt; returns JSON |
| `reply_ai_seo.py` | Fetches statuses and prints drafted replies |
| `mastodon_fetch.py` | Status search and hashtag timelines |
| `mastodon_post.py` | Posting, media upload and dry-run batch posting |
| `image_gen_replicate.py` | Image generation on Replicate |
| `evals/` | Eval runner, checks, judge and cases |

## Known limitations

- **Retrieval does not filter anything yet.** Notion blocks are joined with single newlines and the paragraph chunker splits on blank lines, so the whole page becomes one chunk and is always passed to the LLM in full.
- **Posts can invent facts.** On a topic the Notion page does not cover, the model makes up details. The `not_in_context` eval case catches this.
- **Replies are never flagged for review.** Spam and prompt-injection statuses come back with `requires_review` set to false. The `review_flagged` eval check catches this.
- **Rejection reasons are not used.** The reason is printed, but no new draft is generated from it.
