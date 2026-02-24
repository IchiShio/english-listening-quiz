"""
gen_translation.py
英語スクリプト（text フィールド）の日本語仮訳を生成し、
index.html の各問題オブジェクトに ja フィールドとして追加する。

使い方:
  python3 gen_translation.py

設定:
  INPUT_HTML  … 対象 HTML ファイル
  BATCH_SIZE  … 1回のAPIコールで翻訳する件数
  MODEL       … 使用モデル
"""

import os
import re
import time

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

INPUT_HTML = "index.html"
BATCH_SIZE = 20
MODEL      = "claude-haiku-4-5-20251001"

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def translate_batch(texts: list) -> list:
    """英語テキストをまとめて日本語に翻訳する。"""
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
    prompt = (
        "以下の英語のセリフを口語的・自然な日本語に翻訳してください。\n"
        "・英語の語順やニュアンスをできるだけ保つ\n"
        "・説明や注釈は不要。翻訳文のみを番号付きリストで返す\n\n"
        + numbered
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )

    result_text = response.content[0].text.strip()
    translations = []
    for line in result_text.split("\n"):
        line = re.sub(r"^\d+[.)]\s*", "", line.strip())
        if line:
            translations.append(line)

    # 件数が合わない場合は調整
    while len(translations) < len(texts):
        translations.append("")
    return translations[:len(texts)]


def main():
    with open(INPUT_HTML, encoding="utf-8") as f:
        html = f.read()

    # 既に ja フィールドが存在するかチェック
    existing_count = html.count('ja: "')
    if existing_count > 0:
        print(f"⚠️  ja フィールドが既に {existing_count} 件存在します。")
        print("   上書きする場合は既存の ja フィールドを削除してから再実行してください。")
        return

    # text フィールドを全件抽出
    pattern = re.compile(r'text: "([^"]*(?:\\.[^"]*)*)"')
    matches = list(pattern.finditer(html))

    if not matches:
        print("❌ text フィールドが見つかりませんでした。")
        return

    total = len(matches)
    print(f"📝 {total} 件の text フィールドを検出。翻訳を開始します...")

    texts = [m.group(1) for m in matches]
    translations = []

    for i in range(0, total, BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        end   = min(i + len(batch), total)
        print(f"  [{i+1:3d}〜{end:3d}/{total}] 翻訳中...", end=" ", flush=True)
        batch_trans = translate_batch(batch)
        translations.extend(batch_trans)
        print("完了")
        time.sleep(0.3)

    print(f"\n✅ 翻訳完了: {len(translations)} 件")

    # ja フィールドを text: "..." の直後に挿入（後ろから処理して位置ズレを防ぐ）
    result = html
    offset = 0
    for i, m in enumerate(matches):
        ja_escaped = translations[i].replace("\\", "\\\\").replace('"', '\\"')
        insert_pos  = m.end() + offset
        insertion   = f', ja: "{ja_escaped}"'
        result = result[:insert_pos] + insertion + result[insert_pos:]
        offset += len(insertion)

    with open(INPUT_HTML, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"📄 {INPUT_HTML} を更新しました。")
    print("\n次のステップ:")
    print("  cp index.html ../eikaiwa-hikaku/listening/index.html")
    print("  cd ../eikaiwa-hikaku && git add listening/index.html && git commit -m '...' && git push")


if __name__ == "__main__":
    main()
