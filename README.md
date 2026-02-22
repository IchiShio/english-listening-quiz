# English Listening Quiz

ネイティブ英語を聴いて、どんなシチュエーションか5択で当てる学習Webアプリ。

## フェーズ

| フェーズ | 内容 | 状態 |
|---------|------|------|
| Mockup  | 静的HTMLで UI / UX を確認 | ✅ 完成 |
| MVP     | Claude API + Node.js サーバー | 🔜 次フェーズ |

## Mockup の起動方法

```bash
open mockup.html
# または
open -a "Google Chrome" mockup.html
```

ブラウザで `mockup.html` を直接開くだけで動作します。サーバー不要。

### 動作環境
- Chrome / Edge / Safari (macOS) 推奨
- Web Speech API が使える環境であれば英語音声が自動再生されます

### ハードコードされた問題（6問）
- 初級 × 2問（日常会話）
- 中級 × 2問（カフェ・レストラン）
- 上級 × 2問（ビジネス英語）

## MVP の起動方法（次フェーズ）

```bash
cp .env.example .env
# .env に ANTHROPIC_API_KEY を記入

npm install
npm start
# → http://localhost:3000
```
