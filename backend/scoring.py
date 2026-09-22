import difflib
import re

from pythainlp.tokenize import word_tokenize

# Thai script block + Thai-specific punctuation (paiyannoi, maiyamok) and spaces.
# Orchardrun's `language` param is only a hint, not an enforced constraint, so
# noisy/unclear audio can come back with stray Chinese/Korean/Latin tokens.
# Stripping anything outside the Thai block is the only lever we have to keep
# those out of the scoring — it can't stop the model decoding them, only hide
# the result.
_NON_THAI_RE = re.compile(r"[^฀-๿\s]")


def _keep_thai_only(text: str) -> str:
    return _NON_THAI_RE.sub("", text)


def _tokenize(text: str) -> list[str]:
    return [w for w in word_tokenize(text, engine="newmm") if w.strip()]


def score_attempt(target_text: str, transcript: str) -> dict:
    transcript = _keep_thai_only(transcript)
    target_words = _tokenize(target_text)
    transcript_words = _tokenize(transcript)

    matcher = difflib.SequenceMatcher(a=target_words, b=transcript_words)
    diff = []
    matched = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            matched += i2 - i1
            diff.extend({"word": w, "status": "match"} for w in target_words[i1:i2])
        else:
            diff.extend({"word": w, "status": "missing"} for w in target_words[i1:i2])
            diff.extend({"word": w, "status": "extra"} for w in transcript_words[j1:j2])

    score = round(100 * matched / max(len(target_words), 1))
    return {"score": score, "diff": diff, "transcript": transcript}
