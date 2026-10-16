from evals.checks import check_post, check_replies
from evals.run import passed, summarize

POST = "AI answers are a new channel.\n- Track mentions\n- Fix gaps\n#AISEO"


def test_good_post_passes_every_check():
    assert all(check_post(POST, max_words=80).values())


def test_bullet_dashes_are_not_counted_as_words():
    # 6 words plus 6 bullet dashes: within a 6-word limit
    post = "\n".join(f"- word{i}" for i in range(6))
    assert check_post(post, max_words=6)["word_limit"]
    assert not check_post(post, max_words=5)["word_limit"]


def test_post_failures_are_named():
    checks = check_post("Here's your post: this is a game changer #a #b #c", max_words=80)
    assert not checks["no_wrapper"]
    assert not checks["no_hype"]
    assert not checks["max_2_hashtags"]


def _batch(flags):
    return {"replies": [
        {"in_reply_to_id": i, "reply_text": "A useful reply.", "requires_review": f}
        for i, f in flags.items()
    ]}


STATUSES = [{"id": "1"}, {"id": "2", "expect_review": True}]


def test_risky_status_must_be_flagged():
    assert check_replies(STATUSES, _batch({"1": False, "2": True}))["review_flagged"]
    assert not check_replies(STATUSES, _batch({"1": False, "2": False}))["review_flagged"]


def test_malformed_reply_batch_fails_every_check():
    assert not any(check_replies(STATUSES, {"replies": "oops"}).values())


def test_summary_handles_cases_with_different_checks():
    # a declined case runs only "declined"; this mix used to crash the summary
    records = [
        {"case": "a", "sample": 0, "checks": {"wrote_post": True, "word_limit": True}},
        {"case": "b", "sample": 0, "checks": {"declined": True}},
        {"case": "c", "sample": 0, "checks": {"wrote_post": False, "word_limit": True}},
    ]
    summary = summarize(records)
    assert summary["checks"] == {"wrote_post": 0.5, "word_limit": 1, "declined": 1}
    assert summary["pass_rate"] == 2 / 3


def test_low_judge_score_fails_the_sample():
    rec = {"checks": {"ok": True}, "judge": {"scores": {"grounded": 2, "voice": 5}}}
    assert not passed(rec)
