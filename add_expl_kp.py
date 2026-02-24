#!/usr/bin/env python3
"""
add_expl_kp.py
questions.json の全問題に expl（解説）と kp（キーフレーズ）を追加し、
index.html の DATA 配列も更新するスクリプト。
"""

import anthropic
import json
import re
import time

BATCH_SIZE = 20
PROGRESS_FILE = "expl_kp_progress.json"
MODEL = "claude-haiku-4-5-20251001"

client = anthropic.Anthropic()


def generate_batch(questions):
    items = []
    for i, q in enumerate(questions):
        items.append(f'{i + 1}. "{q["text"]}"\n   → 正解: "{q["answer"]}"')

    prompt = f"""英語リスニング問題の「解説」と「キーフレーズ」を生成してください。

【ルール】
- expl: 英文のどの表現が正解の根拠になるかを日本語で1〜2文（30〜60字）
- kp: 英文中の覚えておきたい重要な英語フレーズや単語を2〜4個の配列

【問題一覧】
{chr(10).join(items)}

以下の形式のJSON配列のみを返してください（コードブロック・他のテキスト不要）:
[
  {{"expl": "解説テキスト", "kp": ["フレーズ1", "フレーズ2"]}},
  ...
]"""

    resp = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    # コードブロックが含まれていたら除去
    text = re.sub(r"```(?:json)?\n?", "", text).strip().rstrip("`").strip()
    return json.loads(text)


def main():
    with open("questions.json", encoding="utf-8") as f:
        questions = json.load(f)

    # 進捗ロード
    try:
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            progress = json.load(f)
    except FileNotFoundError:
        progress = {}

    total = len(questions)
    processed = 0

    for start in range(0, total, BATCH_SIZE):
        batch = questions[start : start + BATCH_SIZE]
        indices = list(range(start, min(start + BATCH_SIZE, total)))

        # 全件処理済みならスキップ
        if all(str(i) in progress for i in indices):
            for i in indices:
                questions[i]["expl"] = progress[str(i)]["expl"]
                questions[i]["kp"] = progress[str(i)]["kp"]
            processed += len(indices)
            print(f"[skip] {start + 1}〜{start + len(batch)}/{total}")
            continue

        print(f"[{start + 1}〜{start + len(batch)}/{total}] 生成中...", end=" ", flush=True)

        for attempt in range(3):
            try:
                results = generate_batch(batch)
                break
            except Exception as e:
                print(f"\n  エラー (attempt {attempt + 1}/3): {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt * 2)
                else:
                    raise

        for i, r in zip(indices, results):
            questions[i]["expl"] = r["expl"]
            questions[i]["kp"] = r["kp"]
            progress[str(i)] = {"expl": r["expl"], "kp": r["kp"]}
            processed += 1

        # 進捗保存
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False)

        print(f"完了")
        time.sleep(0.3)

    # questions.json 更新
    with open("questions.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"\n✅ questions.json 更新完了（{processed}問）")

    # index.html の DATA 配列を更新
    update_html(questions)
    print("✅ index.html 更新完了")


def update_html(questions):
    with open("index.html", encoding="utf-8") as f:
        content = f.read()

    # DATA 配列の開始・終了位置を特定
    start_marker = "const DATA = ["
    start_pos = content.index(start_marker)
    end_pos = content.index("];", start_pos) + 2

    # 新しい DATA 配列を構築（1問1行）
    lines = ["const DATA = ["]
    for q in questions:
        entry = {
            "diff": q["diff"],
            "text": q["text"],
            "answer": q["answer"],
            "choices": q["choices"],
            "audio": q["audio"],
            "expl": q.get("expl", ""),
            "kp": q.get("kp", []),
        }
        # JSON → JS オブジェクトリテラル形式に変換
        line = (
            f'  {{ diff: {json.dumps(entry["diff"])}, '
            f'text: {json.dumps(entry["text"], ensure_ascii=False)}, '
            f'answer: {json.dumps(entry["answer"], ensure_ascii=False)}, '
            f'choices: {json.dumps(entry["choices"], ensure_ascii=False)}, '
            f'audio: {json.dumps(entry["audio"])}, '
            f'expl: {json.dumps(entry["expl"], ensure_ascii=False)}, '
            f'kp: {json.dumps(entry["kp"], ensure_ascii=False)} }},'
        )
        lines.append(line)
    lines.append("];")
    new_data_block = "\n".join(lines)

    # 置換
    new_content = content[:start_pos] + new_data_block + content[end_pos:]

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(new_content)


if __name__ == "__main__":
    main()
