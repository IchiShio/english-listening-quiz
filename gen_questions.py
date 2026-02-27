"""
gen_questions.py
Claude Haiku API を使って英語リスニングクイズの問題を生成する。

難易度は 1.0〜10.0 の連続スコアで自動判定（IRT対応）:
  - 語数          : 0〜3 点
  - 構文複雑度    : 0〜3 点
  - 語彙難度      : 0〜2 点
  - 口語特徴密度  : 0〜2 点

後方互換のため diff フィールド (beginner/intermediate/advanced) も維持。

使い方:
  pip install anthropic python-dotenv
  cp .env.example .env  # ANTHROPIC_API_KEY を記入
  python3 gen_questions.py

設定:
  TARGET     … 生成目標問題数
  BATCH_SIZE … 1回のAPIコールで生成する問題数
  OUTPUT     … 出力先JSONファイル
"""

"""
=== 3,000問達成スケジュール（2週間: 2/27〜3/13） ===

■ Week 1: インフラ整備 + 1,500問生成
  Day 1-2 (2/27-28): インフラ整備
    - [済] 難易度スコアリング (1.0-10.0) 設計・実装
    - [済] gen_questions.py: 20段階ティア対応、TARGET=3000
    - [済] gen_audio.py: 速度バリエーション対応
    - [済] index.html: IRT適応アルゴリズム実装
    - 既存455問の動作確認

  Day 3-4 (3/1-2): 第1弾生成（q456〜q955 = 500問）
    - python3 gen_questions.py  ※TARGET=500, 差分生成
    - python3 gen_audio.py
    - python3 add_expl_kp.py
    - python3 gen_translation.py
    - index.html に統合、動作確認

  Day 5-6 (3/3-4): 第2弾生成（q956〜q1455 = 500問）
    - 同上の生成パイプライン実行
    - 重複チェック・品質確認

  Day 7 (3/5): 第3弾生成（q1456〜q1955 = 500問）
    - 生成パイプライン実行
    - Week 1 QA: 全1,955問の品質レビュー

■ Week 2: 残り1,045問 + 品質管理
  Day 8-9 (3/6-7): 第4弾生成（q1956〜q2455 = 500問）
    - 生成パイプライン実行
    - スコア分布の偏りがないか確認・調整

  Day 10-11 (3/8-9): 第5弾生成（q2456〜q3000 = 545問）
    - 生成パイプライン実行
    - 全3,000問統合

  Day 12 (3/10): 品質管理
    - 重複問題の検出・除去
    - スコア分布の最終確認
    - 選択肢の質チェック

  Day 13 (3/11): アルゴリズム調整
    - IRT パラメータ（学習率、選出範囲）の微調整
    - 3,000問での応答速度テスト

  Day 14 (3/12-13): デプロイ・バッファ
    - 最終テスト
    - eikaiwa-hikaku/listening/ への反映
    - 本番デプロイ

■ 各バッチの実行手順:
  1. gen_questions.py を実行（TARGET を調整）
  2. gen_audio.py を実行（MP3 生成）
  3. add_expl_kp.py を実行（解説・キーフレーズ付与）
  4. gen_translation.py を実行（日本語仮訳）
  5. index.html の DATA 配列に統合
  6. 動作確認 → コミット

■ API コスト見積り:
  - 問題生成: ~128 API calls × $0.003 ≈ $0.38
  - 解説生成: ~128 API calls × $0.003 ≈ $0.38
  - 翻訳生成: ~128 API calls × $0.003 ≈ $0.38
  - 合計: 約 $1.14（Haiku使用時）

■ 音声生成:
  - edge-tts は無料（Microsoft Edge TTS）
  - 3,000ファイル × ~2秒/件 ≈ 約100分
"""

import json
import math
import os
import re
import time

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# ── 設定 ─────────────────────────────────────────
TARGET     = 3000
BATCH_SIZE = 20
OUTPUT     = "questions.json"
MODEL      = "claude-haiku-4-5-20251001"
# ──────────────────────────────────────────────────

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ── 難易度スコアリング (1.0〜10.0) ────────────────
CLAUSE_MARKERS = re.compile(
    r"\b(and|but|or|so|because|when|if|that|which|who|whom|whose|"
    r"although|though|while|since|after|before|until|unless|"
    r"however|therefore|moreover|furthermore|nevertheless|whereas|"
    r"whether|as soon as|even though|as long as|in order to|"
    r"so that|provided that|given that|not only|either|neither|"
    r"once|whenever|wherever|whatever|whoever|however much)\b",
    re.IGNORECASE,
)

CONTRACTIONS = re.compile(
    r"\b\w+'(t|s|re|ve|ll|d|m)\b", re.IGNORECASE
)

FILLERS = re.compile(
    r"\b(uh|um|like|you know|I mean|well|so|anyway|basically|"
    r"actually|honestly|literally|right|okay)\b",
    re.IGNORECASE,
)

PHRASAL_VERBS = re.compile(
    r"\b(turn (down|up|off|on|out|around)|pick (up|out)|"
    r"give (up|in|out)|take (off|on|out|over|up)|"
    r"put (on|off|up|down|out|away)|get (up|out|off|on|over|through)|"
    r"come (up|on|out|back|across)|go (on|out|off|through|over)|"
    r"look (up|out|into|after|forward)|run (out|into|over)|"
    r"break (down|up|out|in)|bring (up|back|down|out)|"
    r"figure (out)|work (out|on)|set (up|off|out)|"
    r"hold (on|up|off)|cut (off|out|down)|pull (off|out|up))\b",
    re.IGNORECASE,
)

# 高頻度語リスト（上位1000語相当 — 6文字以上の単語はやや難）
COMMON_SHORT = {"the", "be", "to", "of", "and", "a", "in", "that", "have",
    "i", "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
    "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
    "or", "an", "will", "my", "one", "all", "would", "there", "their",
    "what", "so", "up", "out", "if", "about", "who", "get", "which", "go",
    "me", "when", "make", "can", "like", "time", "no", "just", "him",
    "know", "take", "people", "into", "year", "your", "good", "some",
    "could", "them", "see", "other", "than", "then", "now", "look",
    "only", "come", "its", "over", "think", "also", "back", "after",
    "use", "two", "how", "our", "work", "first", "well", "way", "even",
    "new", "want", "give", "most", "find", "here", "thing", "many",
    "day", "had", "has", "been", "did", "got", "am", "are", "is", "was",
    "were", "very", "much", "too", "really", "right", "still", "own",
    "down", "should", "need", "home", "big", "old", "long", "may"}


def compute_score(text: str) -> float:
    """テキストの聴解難易度を 1.0〜10.0 で算出する。"""
    words = text.split()
    word_count = len(words)
    clause_count = len(CLAUSE_MARKERS.findall(text))

    # 1. 語数スコア (0〜3)
    wc = min(word_count / 20.0, 3.0)

    # 2. 構文複雑度 (0〜3)
    cc = min(clause_count / 3.0, 3.0)

    # 3. 語彙難度 (0〜2)
    long_or_rare = sum(
        1 for w in words
        if len(w) >= 7 and w.lower().strip(".,!?;:'\"") not in COMMON_SHORT
    )
    vd = min(long_or_rare / max(word_count, 1) * 10.0, 2.0)

    # 4. 口語特徴密度 (0〜2)
    contraction_count = len(CONTRACTIONS.findall(text))
    filler_count = len(FILLERS.findall(text))
    phrasal_count = len(PHRASAL_VERBS.findall(text))
    oral_density = (contraction_count + filler_count + phrasal_count) / max(word_count, 1)
    od = min(oral_density * 8.0, 2.0)

    raw = wc + cc + vd + od  # 0〜10
    return round(max(1.0, min(10.0, raw + 1.0)), 1)


def score_to_diff(score: float) -> str:
    """連続スコアを後方互換の3段階ラベルに変換。"""
    if score < 4.0:
        return "beginner"
    if score < 7.0:
        return "intermediate"
    return "advanced"


# ── プロンプト ────────────────────────────────────
SYSTEM = (
    "あなたは英語リスニングクイズ問題作成の専門家です。"
    "ネイティブスピーカーの自然な発話（独り言・会話・電話・アナウンスなど）を英語で書き、"
    "その状況を日本語で表す5択問題を作成します。"
)

# 20段階の複雑さテンプレート
COMPLEXITY_TIERS = {
    1: "非常に短く単純な発話（8〜12語）。接続詞なし。「Hello」「Excuse me」レベルの日常挨拶・一言。",
    2: "短い発話（10〜15語）。接続詞0〜1個。買い物・道案内など明確な1文。",
    3: "短い発話（12〜18語）。接続詞1個。日常的な依頼・質問。短縮形を使用。",
    4: "やや短め（15〜20語）。接続詞1〜2個。感想・不満・簡単な説明。フィラー1個程度。",
    5: "標準的な長さ（18〜25語）。接続詞2個。職場・学校での日常会話。句動詞を1つ含む。",
    6: "標準的な長さ（20〜28語）。接続詞2〜3個。予定・計画・提案の会話。短縮形を2つ以上。",
    7: "やや長め（25〜32語）。接続詞3個。理由を説明する場面。フィラー・句動詞混在。",
    8: "やや長め（28〜35語）。接続詞3〜4個。カフェ・旅行・トラブル対応。やや専門的な語彙1〜2語。",
    9: "中程度の長さ（30〜38語）。接続詞4個。仕事の相談・報告。複文が1つ。",
    10: "中程度の長さ（32〜40語）。接続詞4〜5個。交渉・依頼・意見交換。関係代名詞を含む。",
    11: "やや長い（35〜42語）。接続詞5個。ビジネスメール的内容の口語版。専門語彙2〜3語。",
    12: "やや長い（38〜45語）。接続詞5〜6個。プレゼン・報告場面。従属節2つ以上。",
    13: "長め（40〜48語）。接続詞6個。会議・議論。意見の対立を含む。句動詞2つ以上。",
    14: "長め（42〜50語）。接続詞6〜7個。ニュース・アナウンス。フォーマルな表現混在。",
    15: "長い（45〜55語）。接続詞7個。契約・法律・医療の日常場面。専門語彙3〜4語。",
    16: "長い（48〜58語）。接続詞7〜8個。複雑な指示・手順説明。複文3つ以上。",
    17: "かなり長い（50〜62語）。接続詞8個以上。講義・セミナーの一部。抽象的な概念を含む。",
    18: "かなり長い（55〜65語）。接続詞8〜9個。ディベート・専門的議論。仮定法を含む。",
    19: "非常に長い（60〜70語）。接続詞9個以上。学術的・技術的な説明。複雑な構文。",
    20: "非常に長い（65語以上）。接続詞10個以上。スピーチ・講演の一節。高度な語彙・複文多用。",
}

# 各ティアの生成目標比率（中間難度を厚めに分布 — 正規分布的）
TIER_WEIGHTS = {
    1: 3, 2: 4, 3: 5, 4: 6, 5: 7, 6: 8, 7: 9, 8: 10, 9: 10, 10: 10,
    11: 10, 12: 9, 13: 8, 14: 7, 15: 6, 16: 5, 17: 4, 18: 3, 19: 2, 20: 2,
}


def make_prompt(batch_size: int, tier: int) -> str:
    guide = COMPLEXITY_TIERS[tier]

    return f"""以下の形式でJSON配列を{batch_size}問生成してください。

複雑さの指定（ティア {tier}/20）: {guide}

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
- 各問題のシチュエーションを多様にすること
- JSONのみ出力（前後の説明文は不要）"""


def generate_batch(batch_size: int, tier: int) -> list[dict]:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM,
        messages=[{"role": "user", "content": make_prompt(batch_size, tier)}],
    )
    raw = resp.content[0].text.strip()
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        raise ValueError(f"JSON not found:\n{raw[:300]}")
    items = json.loads(m.group())
    for item in items:
        item["score"] = compute_score(item["text"])
        item["diff"]  = score_to_diff(item["score"])
        item["audio"] = ""  # gen_audio.py で後から埋める
    return items


# ── メイン ────────────────────────────────────────
def main() -> None:
    total_weight = sum(TIER_WEIGHTS.values())
    plans = []
    for tier in sorted(COMPLEXITY_TIERS.keys()):
        goal = max(1, round(TARGET * TIER_WEIGHTS[tier] / total_weight))
        plans.append((tier, goal))

    # 端数調整
    diff = TARGET - sum(g for _, g in plans)
    if diff > 0:
        plans[9] = (plans[9][0], plans[9][1] + diff)
    elif diff < 0:
        plans[9] = (plans[9][0], max(1, plans[9][1] + diff))

    questions: list[dict] = []

    for tier, goal in plans:
        generated = 0
        print(f"\n── ティア {tier:2d}/20 ({goal}問) ──────────────")
        while generated < goal:
            bs = min(BATCH_SIZE, goal - generated)
            attempt = 0
            while attempt < 3:
                try:
                    batch = generate_batch(bs, tier)
                    questions.extend(batch)
                    generated += len(batch)
                    print(f"  [{generated:3d}/{goal}] {len(batch)}問 生成 "
                          f"(スコア範囲: {min(q['score'] for q in batch):.1f}"
                          f"〜{max(q['score'] for q in batch):.1f})")
                    time.sleep(0.8)
                    break
                except Exception as e:
                    attempt += 1
                    print(f"  エラー ({attempt}/3): {e}")
                    time.sleep(3 * attempt)

    # スコア順にソート
    questions.sort(key=lambda q: q["score"])

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    from collections import Counter
    c = Counter(q["diff"] for q in questions)
    scores = [q["score"] for q in questions]
    print(f"\n✅ 完了: 計{len(questions)}問 を {OUTPUT} に保存")
    print(f"  スコア範囲: {min(scores):.1f} 〜 {max(scores):.1f}")
    print(f"  beginner:     {c.get('beginner', 0)} 問")
    print(f"  intermediate: {c.get('intermediate', 0)} 問")
    print(f"  advanced:     {c.get('advanced', 0)} 問")
    print(f"\n  スコア分布:")
    for bucket in range(1, 11):
        count = sum(1 for s in scores if bucket <= s < bucket + 1)
        bar = "█" * (count // 5)
        print(f"    {bucket:2d}.0〜{bucket}.9: {count:4d} {bar}")
    print("\n次のステップ: python3 gen_audio.py")


if __name__ == "__main__":
    main()
