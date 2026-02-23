"""
gen_audio.py
questions.json の各問題テキストを edge-tts で MP3 化するスクリプト。

使い方:
  python3 gen_audio.py

オプション（スクリプト先頭の定数を編集）:
  VOICE     … 使用する音声（下記一覧参照）
  OUTPUT_DIR … MP3 の出力先フォルダ
  RATE      … 読み上げ速度 (+0% がデフォルト、遅くするには -10% など)

主な英語 Neural 音声:
  en-US-JennyNeural   女性・自然な会話調（デフォルト）
  en-US-GuyNeural     男性・落ち着いた声
  en-US-AriaNeural    女性・表現豊か
  en-GB-SoniaNeural   女性・英国アクセント
  en-GB-RyanNeural    男性・英国アクセント
  en-AU-NatashaNeural 女性・オーストラリア
"""

import asyncio
import json
import os

import edge_tts

# ── 設定 ──────────────────────────────────────────────
VOICE      = "en-US-JennyNeural"
RATE       = "+0%"          # 速度調整: "-10%" で少し遅く
OUTPUT_DIR = "audio"
QUESTIONS  = "questions.json"
# ──────────────────────────────────────────────────────


async def generate_one(text: str, path: str) -> None:
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    await communicate.save(path)


async def main() -> None:
    with open(QUESTIONS, encoding="utf-8") as f:
        questions = json.load(f)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total = len(questions)

    for i, q in enumerate(questions, 1):
        path = f"{OUTPUT_DIR}/q{i:02d}.mp3"
        print(f"[{i:02d}/{total}] {path}  ← {q['text'][:50]}...")
        await generate_one(q["text"], path)
        questions[i - 1]["audio"] = path

    # audio パスを questions.json に書き戻す
    with open(QUESTIONS, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 完了！ {total} 件の MP3 を /{OUTPUT_DIR} に生成しました。")
    print("次のステップ: python3 gen_audio.py 実行後に mockup.html を更新します。")


asyncio.run(main())
