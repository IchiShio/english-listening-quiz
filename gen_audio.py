"""
gen_audio.py
questions.json の各問題テキストを edge-tts で MP3 化するスクリプト。

使い方:
  python3 gen_audio.py

オプション（スクリプト先頭の定数を編集）:
  VOICES    … 使用する音声リスト（問題番号 % len(VOICES) でローテーション）
  OUTPUT_DIR … MP3 の出力先フォルダ
  RATE      … 読み上げ速度 (+0% がデフォルト、遅くするには -10% など)

音声ローテーション（5種）:
  1,6,11...  en-US-AriaNeural    女性・アメリカ
  2,7,12...  en-GB-SoniaNeural   女性・イギリス
  3,8,13...  en-US-GuyNeural     男性・アメリカ
  4,9,14...  en-AU-NatashaNeural 女性・オーストラリア
  5,10,15... en-GB-RyanNeural    男性・イギリス
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
RATE       = "+0%"
OUTPUT_DIR = "audio"
QUESTIONS  = "questions.json"
# ──────────────────────────────────────────────────────


async def generate_one(text: str, path: str, voice: str) -> None:
    communicate = edge_tts.Communicate(text, voice, rate=RATE)
    await communicate.save(path)


async def main() -> None:
    with open(QUESTIONS, encoding="utf-8") as f:
        questions = json.load(f)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total = len(questions)

    for i, q in enumerate(questions, 1):
        path = f"{OUTPUT_DIR}/q{i:02d}.mp3"
        voice = VOICES[(i - 1) % len(VOICES)]
        print(f"[{i:02d}/{total}] {path}  [{voice}]  ← {q['text'][:50]}...")
        await generate_one(q["text"], path, voice)
        questions[i - 1]["audio"] = path

    # audio パスを questions.json に書き戻す
    with open(QUESTIONS, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 完了！ {total} 件の MP3 を /{OUTPUT_DIR} に生成しました。")
    print("次のステップ: python3 gen_audio.py 実行後に mockup.html を更新します。")


asyncio.run(main())
