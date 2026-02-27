"""
gen_audio.py
questions.json の各問題テキストを edge-tts で MP3 化するスクリプト。

使い方:
  python3 gen_audio.py

オプション（スクリプト先頭の定数を編集）:
  VOICES      … 使用する音声リスト（問題番号 % len(VOICES) でローテーション）
  OUTPUT_DIR  … MP3 の出力先フォルダ
  ADAPTIVE_RATE … True の場合、難易度スコアに応じて読み上げ速度を変化
                  低スコア（簡単）→ やや遅め / 高スコア（難しい）→ やや速め

音声ローテーション（5種）:
  1,6,11...  en-US-AriaNeural    女性・アメリカ
  2,7,12...  en-GB-SoniaNeural   女性・イギリス
  3,8,13...  en-US-GuyNeural     男性・アメリカ
  4,9,14...  en-AU-NatashaNeural 女性・オーストラリア
  5,10,15... en-GB-RyanNeural    男性・イギリス

速度バリエーション（ADAPTIVE_RATE=True 時）:
  スコア 1.0〜3.0 → -8%（やや遅め、初心者が聴きやすい）
  スコア 3.1〜5.0 → -3%（少しだけ遅め）
  スコア 5.1〜7.0 → +0%（標準速度）
  スコア 7.1〜8.5 → +5%（やや速め、ネイティブに近い）
  スコア 8.6〜10.0 → +10%（速め、上級者向け）
"""

import asyncio
import json
import os

import edge_tts

# ── 設定 ──────────────────────────────────────────────
VOICES = [
    "en-US-AriaNeural",     # 女性・アメリカ
    "en-GB-SoniaNeural",    # 女性・イギリス
    "en-US-GuyNeural",      # 男性・アメリカ
    "en-AU-NatashaNeural",  # 女性・オーストラリア
    "en-GB-RyanNeural",     # 男性・イギリス
]
ADAPTIVE_RATE = True    # 難易度スコアに応じた速度変化
OUTPUT_DIR    = "audio"
QUESTIONS     = "questions.json"
# ──────────────────────────────────────────────────────


def get_rate(score: float) -> str:
    """難易度スコアに応じた読み上げ速度を返す。"""
    if not ADAPTIVE_RATE:
        return "+0%"
    if score <= 3.0:
        return "-8%"
    if score <= 5.0:
        return "-3%"
    if score <= 7.0:
        return "+0%"
    if score <= 8.5:
        return "+5%"
    return "+10%"


async def generate_one(text: str, path: str, voice: str, rate: str) -> None:
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(path)


async def main() -> None:
    with open(QUESTIONS, encoding="utf-8") as f:
        questions = json.load(f)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total = len(questions)
    # 桁数に応じたゼロパディング（3000問対応）
    digits = max(3, len(str(total)))

    for i, q in enumerate(questions, 1):
        path = f"{OUTPUT_DIR}/q{i:0{digits}d}.mp3"
        voice = VOICES[(i - 1) % len(VOICES)]
        q_score = q.get("score", 5.0)
        rate = get_rate(q_score)
        print(f"[{i:{digits}d}/{total}] {path}  [{voice}] [{rate}]  ← {q['text'][:50]}...")
        await generate_one(q["text"], path, voice, rate)
        questions[i - 1]["audio"] = path

    # audio パスを questions.json に書き戻す
    with open(QUESTIONS, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 完了！ {total} 件の MP3 を /{OUTPUT_DIR} に生成しました。")
    print("次のステップ: python3 add_expl_kp.py")


asyncio.run(main())
