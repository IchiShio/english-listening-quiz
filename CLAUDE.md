# CLAUDE.md

## プロジェクト概要
ネイティブ英語を聴いてシチュエーションを5択で当てる学習Webアプリ。
現在はMockupフェーズ（静的HTML）。次フェーズでClaude API + Node.js を追加予定。

## 技術スタック
- 静的HTML / CSS / JavaScript（Mockupフェーズ）
- Python（音声・問題生成スクリプト）
- 次フェーズ: Claude API + Node.js サーバー

## 主要ファイル
| ファイル | 説明 |
|---|---|
| `index.html` | メインUI |
| `questions.json` | 問題データ（455問） |
| `audio/` | MP3音声ファイル（464件） |
| `gen_questions.py` | 問題自動生成スクリプト |
| `gen_audio.py` | 音声生成スクリプト |

## 開発ルール
- コード変更後は自動でコミット＆プッシュまで行う
- APIキーは `.env` に記載し、ソースコードに直接書かない
