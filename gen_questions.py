"""
gen_questions.py
Claude Haiku API を使って英語リスニングクイズの問題を生成する。

難易度は以下の客観基準で自動判定：
  score = 語数 + 接続詞・従属節マーカーの数 × 3
  beginner     : score < 28
  intermediate : score < 50
  advanced     : score >= 50

使い方:
  pip install anthropic python-dotenv
  cp .env.example .env  # ANTHROPIC_API_KEY を記入
  python3 gen_questions.py

設定:
  TARGET     … 生成目標問題数
  BATCH_SIZE … 1回のAPIコールで生成する問題数
  OUTPUT     … 出力先JSONファイル
"""

import json
import os
import re
import time

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# ── 設定 ─────────────────────────────────────────
TARGET     = 500
BATCH_SIZE = 20
OUTPUT     = "questions.json"
MODEL      = "claude-haiku-4-5-20251001"
# ──────────────────────────────────────────────────

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ── 難易度判定 ────────────────────────────────────
CLAUSE_MARKERS = re.compile(
    r"\b(and|but|or|so|because|when|if|that|which|who|whom|whose|"
    r"although|though|while|since|after|before|until|unless|"
    r"however|therefore|moreover|furthermore|nevertheless|whereas|"
    r"whether|as soon as|even though|as long as|in order to|"
    r"so that|provided that|given that|not only|either|neither|"
    r"once|whenever|wherever|whatever|whoever|however much)\b",
    re.IGNORECASE,
)


def assign_diff(text: str) -> str:
    word_count    = len(text.split())
    clause_count  = len(CLAUSE_MARKERS.findall(text))
    score         = word_count + clause_count * 3
    if score < 28:
        return "beginner"
    if score < 50:
        return "intermediate"
    return "advanced"


# ── プロンプト ────────────────────────────────────
SYSTEM = (
    "あなたは英語リスニングクイズ問題作成の専門家です。"
    "ネイティブスピーカーの自然な発話（独り言・会話・電話・アナウンスなど）を英語で書き、"
    "その状況を日本語で表す5択問題を作成します。"
)


def make_prompt(batch_size: int, complexity: str) -> str:
    guide = {
        "simple": (
            "短く自然な発話（15〜22語）。接続詞は0〜1個。"
            "日常的でわかりやすい場面。"
        ),
        "medium": (
            "中程度の長さ（25〜38語）。接続詞3〜5個。"
            "カフェ・職場・旅行など、やや限定的な場面。"
        ),
        "complex": (
            "長め（40語以上）。接続詞6個以上、複文・従属節を多用。"
            "ビジネス・交渉・専門的な場面。"
        ),
    }[complexity]

    return f"""以下の形式でJSON配列を{batch_size}問生成してください。

複雑さの指定: {guide}

[
  {{
    "text": "英語の発話テキスト（自然な話し言葉、省略形・フィラーOK）",
    "answer": "正解の状況説明（日本語・20字以内）",
    "choices": [
      "正解の状況説明（answerと同じ文字列）",
      "紛らわしい不正解1",
      "不正解2",
      "不正解3",
      "不正解4"
    ]
  }}
]

注意:
- choices[0] は必ず answer と同じ文字列
- 問題は互いに重複しないこと
- JSONのみ出力（前後の説明文は不要）"""


def generate_batch(batch_size: int, complexity: str) -> list[dict]:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM,
        messages=[{"role": "user", "content": make_prompt(batch_size, complexity)}],
    )
    raw = resp.content[0].text.strip()
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        raise ValueError(f"JSON not found:\n{raw[:300]}")
    items = json.loads(m.group())
    for item in items:
        item["diff"]  = assign_diff(item["text"])
        item["audio"] = ""  # gen_audio.py で後から埋める
    return items


# ── メイン ────────────────────────────────────────
def main() -> None:
    # 複雑さ別の生成目標（合計 TARGET 問）
    plans = [
        ("simple",  TARGET * 5 // 10),   # 250問 → 主に beginner
        ("medium",  TARGET * 3 // 10),   # 150問 → 主に intermediate
        ("complex", TARGET * 2 // 10),   # 100問 → 主に advanced
    ]

    questions: list[dict] = []

    for complexity, goal in plans:
        generated = 0
        print(f"\n── {complexity.upper()} ({goal}問) ──────────────")
        while generated < goal:
            bs = min(BATCH_SIZE, goal - generated)
            attempt = 0
            while attempt < 3:
                try:
                    batch = generate_batch(bs, complexity)
                    questions.extend(batch)
                    generated += len(batch)
                    print(f"  [{generated:3d}/{goal}] {len(batch)}問 生成")
                    time.sleep(0.8)
                    break
                except Exception as e:
                    attempt += 1
                    print(f"  エラー ({attempt}/3): {e}")
                    time.sleep(3 * attempt)

    # 難易度順にソート
    order = {"beginner": 0, "intermediate": 1, "advanced": 2}
    questions.sort(key=lambda q: order[q["diff"]])

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    from collections import Counter
    c = Counter(q["diff"] for q in questions)
    print(f"\n✅ 完了: 計{len(questions)}問 を {OUTPUT} に保存")
    print(f"  beginner:     {c['beginner']} 問")
    print(f"  intermediate: {c['intermediate']} 問")
    print(f"  advanced:     {c['advanced']} 問")
    print("\n次のステップ: python3 gen_audio.py")


if __name__ == "__main__":
    main()
