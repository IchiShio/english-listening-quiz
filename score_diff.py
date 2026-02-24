"""
score_diff.py
questions.json の各問題テキストを読み、難易度を自動判定して上書きする。

判定基準:
  score = 語数 + 接続詞・従属節マーカーの数 × 3
  beginner     : score < 22
  intermediate : score < 25
  advanced     : score >= 25

使い方:
  python3 score_diff.py
"""

import json
import re
from collections import Counter

QUESTIONS = "questions.json"

CLAUSE_MARKERS = re.compile(
    r"\b(and|but|or|so|because|when|if|that|which|who|whom|whose|"
    r"although|though|while|since|after|before|until|unless|"
    r"however|therefore|moreover|furthermore|nevertheless|whereas|"
    r"whether|as soon as|even though|as long as|in order to|"
    r"so that|provided that|given that|not only|either|neither|"
    r"once|whenever|wherever|whatever|whoever)\b",
    re.IGNORECASE,
)


def assign_diff(text: str) -> str:
    word_count   = len(text.split())
    clause_count = len(CLAUSE_MARKERS.findall(text))
    score        = word_count + clause_count * 3
    if score < 22:
        return "beginner"
    if score < 25:
        return "intermediate"
    return "advanced"


def main():
    with open(QUESTIONS, encoding="utf-8") as f:
        questions = json.load(f)

    for q in questions:
        q["diff"] = assign_diff(q["text"])

    # 難易度順にソート
    order = {"beginner": 0, "intermediate": 1, "advanced": 2}
    questions.sort(key=lambda q: order[q["diff"]])

    with open(QUESTIONS, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    c = Counter(q["diff"] for q in questions)
    print(f"✅ 難易度を再判定しました（計{len(questions)}問）")
    print(f"  beginner:     {c['beginner']} 問")
    print(f"  intermediate: {c['intermediate']} 問")
    print(f"  advanced:     {c['advanced']} 問")


if __name__ == "__main__":
    main()
