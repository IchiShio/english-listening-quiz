# CLAUDE.md - english-listening-quiz

## プロジェクト概要

ネイティブ英語を聴いてシチュエーションを5択で当てる学習Webアプリ（静的HTML）。
`eikaiwa-hikaku/listening/` の開発元リポジトリ。本番は `native-real.com/listening/` で公開中。

## 本番との関係

- **本番ファイル**: `/Users/yusuke/projects/claude/eikaiwa-hikaku/listening/index.html`
- **このリポジトリ**: ローカル開発・音声生成スクリプト置き場
- 変更後は `eikaiwa-hikaku/listening/index.html` にも同内容を反映してコミット・プッシュすること

## 技術スタック

- 静的 HTML / CSS / JavaScript（単一ファイル `index.html`）
- 問題データは `index.html` 内の `DATA` 配列にハードコード（JSON ファイルは不使用）
- Python（音声・問題生成スクリプト）

## 主要ファイル

| ファイル | 説明 |
|---|---|
| `index.html` | メインUI（問題データ・ロジック含む） |
| `audio/` | MP3音声ファイル（464件、`q001.mp3`〜） |
| `gen_questions.py` | 問題自動生成スクリプト（Claude Haiku） |
| `gen_audio.py` | 音声生成スクリプト（edge-tts / 5音声ローテーション） |
| `gen_translation.py` | 日本語仮訳生成スクリプト（Claude Haiku） |

## 問題データ構造

```json
{
  "id": "q001",
  "diff": "beginner",
  "text": "英語スクリプト",
  "ja": "日本語仮訳",
  "answer": "正解選択肢",
  "choices": ["選択肢A", "選択肢B", "選択肢C", "選択肢D", "選択肢E"],
  "audio": "audio/q001.mp3",
  "expl": "解説文",
  "kp": ["キーフレーズ1", "キーフレーズ2"]
}
```

- 455問（beginner: 155 / intermediate: 139 / advanced: 161）
- 音声: 5種ローテーション（AriaNeural/SoniaNeural/GuyNeural/NatashaNeural/RyanNeural）
- `ja` フィールド: Claude Haiku で生成した日本語仮訳（2026-02-25追加）

## アルゴリズム

### 適応型難易度（2026-02-24実装）

- intermediate からスタート（`currentLevel = 1`）
- 連続2問正解 → 1段階上（`correctStreak >= 2`）
- 1問不正解 → 1段階下（即時）、不正解問題は新レベルのプールに再挿入
- 難易度ラベルはユーザーに非表示
- 内部状態: `currentLevel`（0=beginner / 1=intermediate / 2=advanced）、`correctStreak`、`pools`

### ヒント機能（2026-02-24実装）

- 1回目の出題: ヒントなし
- 不正解 → 再出題（2回目）: キーフレーズ（`kp`）をアンバー色パネルで表示
- 再出題（3回目以降）: キーフレーズ + 解説（`expl`）を表示
- `hintLevel` プロパティを問題オブジェクトに付与して管理（0=なし / 1=kp / 2=kp+expl）

### 日本語仮訳（2026-02-25実装）

- 回答後のトランスクリプト欄（英文スクリプトの下）に `ja` フィールドの内容を表示
- `ja` が空の場合はラベルごと非表示（`:empty` で制御）
- `gen_translation.py` で再生成可能（実行前に既存 `ja: "` を削除すること）

## CSS設計

- **ブレークポイント**: base(mobile) / 640px(tablet) / 1024px(desktop 2カラム)
- **高さクエリ**: `@media (max-height: 700px)` — iPhone SE 等の短い画面向け
- **タップ領域**: `opt-btn` / `next-btn` に `min-height: 44px`、`play-btn` に `min-height: 48px`（iOS HIG準拠）
- **デスクトップ**: 1024px以上で音声カード左・選択肢右の2カラムレイアウト
- **loading timeout**: 400ms

## 開発ルール

- コード変更後は `eikaiwa-hikaku/listening/index.html` にも同内容を反映し、両リポジトリをコミット・プッシュ
- APIキーは `.env` に記載し、ソースコードに直接書かない
- HTML 内でマークダウン記法（`**太字**`）を使わない（静的 HTML はレンダリングされない）
