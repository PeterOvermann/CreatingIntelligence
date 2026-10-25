# English Verbs: Past Tense

A list of about 6,500 English verbs paired with their simple past tense, intended for experiments on the classic past-tense learning problem.

## Format

`english-verbs-past-tense.tsv` is a tab-separated, UTF-8 file with no header row and one verb per line:

| Column | Content |
|---|---|
| 1 | Base form |
| 2 | Simple past tense |

```
abandon	abandoned
begin	began
stop	stopped
```

## Conventions

- **American spelling** throughout (*labeled*, *traveled*, *bused*).
- **One past form per verb.** Where variants exist, only the more common modern form is listed (*broadcast*, *forecast*, *knitted*, *summited*, *bid*).
- **Simple past only**, not the past participle (*sang*, not *sung*).
- **One entry per spelling.** For homographs, a single sense was chosen (e.g. *lie* → *lay*, in the sense "recline").
- **No modal auxiliaries.** Forms such as *could* and *would* are not treated as past tenses.

## Usage

The file is stored sorted. Shuffle it at load time with a fixed seed for reproducible splits:

```python
import csv, random

with open("en-us-verbs-past-tense.tsv", encoding="utf-8") as f:
    pairs = list(csv.reader(f, delimiter="\t"))

random.Random(42).shuffle(pairs)
```

Only a small fraction of the verbs (roughly 2–3%) are irregular, so consider stratifying train/test splits so that irregular verbs are represented in the test set.

