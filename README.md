# ニュースラジオ

AI・3D制作・PC・ゲームのニュースを、キャラクターと日本語音声でお届けします。

公開先： https://dazai131.github.io/my-news-radio/  
初回はSettings → Pagesで、公開元を`gh-pages`・`/(root)`に設定してから利用できます。

- 毎朝8時（日本時間）から作成・更新を開始します。1回5〜10分です。
- 黄色い再生ボタンで再生し、左の番号で話題を切り替えられます。
- 記事の出典と台本はラジオ画面内で確認できます。

声：**COEIROINK:リリンちゃん（のーまる）**  
キャラクター画像：AI生成  
プレーヤー原作：[monoradio102/myradio](https://github.com/monoradio102/myradio)

`main`には設定、台本、番組の一覧と運用コードを保存します。音声は`main`にコミットせず、公開用の`gh-pages`に直近30日分を置きます。
日々の運用は[docs/radio-workflow.md](docs/radio-workflow.md)を参照してください。

プログラムは[LICENSE](LICENSE)を参照してください。生成音声には[COEIROINKの利用規約](https://coeiroink.com/terms)と[リリンちゃんの音声利用条件](https://coeiroink.com/character/audio-character/lilin-m)が適用されます。
