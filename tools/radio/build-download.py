"""Package the existing radio as one offline HTML file, without a web server."""
import base64
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parent
SITE = ROOT / 'site'
OUT = ROOT.parent.parent / 'outputs'
DAY = '2026-11-08'


def data_url(path, mime):
    return 'data:' + mime + ';base64,' + base64.b64encode(path.read_bytes()).decode('ascii')


def build():
    documents = {name: json.loads((SITE / name).read_text(encoding='utf-8')) for name in
                 ['station.json', 'episodes.json', 'character/character.json', f'episodes/{DAY}-ja.json']}
    station = documents['station.json']
    documents['episodes.json'] = [e for e in documents['episodes.json'] if e['date'] == DAY]
    station['logo'] = data_url(SITE / 'logo.svg', 'image/svg+xml')
    station.pop('repo', None)
    station.pop('url', None)
    station.pop('comments', None)
    station['weather'] = False
    episode = documents[f'episodes/{DAY}-ja.json']
    date = dt.date.fromisoformat(DAY)
    display_date = f'{date.year}年{date.month}月{date.day}日'
    minutes, seconds = divmod(round(episode['seconds']), 60)
    duration = f'{minutes}分{seconds:02}秒'
    for story in episode.get('news', []):
        if isinstance(story.get('link'), dict):
            story['link'].update(image=None, icon=None)
    assets = {'audio/' + DAY + '-ja.mp3': data_url(SITE / f'audio/{DAY}-ja.mp3', 'audio/mpeg')}
    for path in (SITE / 'character').glob('*.png'):
        assets['character/' + path.name] = data_url(path, 'image/png')
    literal = lambda value: json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    bootstrap = '''<script>
const OFFLINE_DOCUMENTS = %s;
const OFFLINE_ASSETS = %s;
const offlineFile = name => OFFLINE_ASSETS[name] || name;
async function offlineFetch(input) {
  const path = String(input).split(/[?#]/)[0];
  const key = Object.keys(OFFLINE_DOCUMENTS).find(k => path === k || path.endsWith('/' + k));
  return key ? new Response(JSON.stringify(OFFLINE_DOCUMENTS[key]), {headers:{'Content-Type':'application/json'}})
             : new Response('', {status:404});
}
</script>
''' % (literal(documents), literal(assets))
    html = (SITE / 'index.html').read_text(encoding='utf-8')
    html = re.sub(r'\bfetch\(', 'offlineFetch(', html)
    replacements = {
        'const charUrl = f => `character/${f}`;': 'const charUrl = f => offlineFile(`character/${f}`);',
        'audio.src = (ep.audio || `audio/${name}.mp3`) + `?v=${encodeURIComponent(ep.made_at || "")}`;':
            'audio.src = offlineFile(ep.audio || `audio/${name}.mp3`);',
        'if (new URL(audio.currentSrc || audio.src, location.href).origin !== location.origin) return;':
            'if (!audio.src.startsWith("data:") && new URL(audio.currentSrc || audio.src, location.href).origin !== location.origin) return;',
    }
    for before, after in replacements.items():
        if html.count(before) != 1:
            raise ValueError('Player source changed; review offline adaptation: ' + before)
        html = html.replace(before, after)
    license_text = (ROOT / 'player-license.txt').read_text(encoding='utf-8')
    html = html.replace('<head>', '<head>\n<!-- Original player license:\n' + license_text + '\n-->\n' + bootstrap, 1)
    html = html.replace('<title>ニュースラジオ</title>', f'<title>ニュースラジオ｜保存した放送 {DAY}</title>')
    html = html.replace('<main>', f'<main>\n<p style="margin:0 0 10px;color:#8d93a8;font-size:13px">保存した放送：{display_date} · {duration}（自動更新なし）</p>', 1)
    output_name = f'ニュースラジオ_{DAY}_開く.html'
    (OUT / output_name).write_text(html, encoding='utf-8')
    readme = f'''ニュースラジオ：保存した放送（{display_date}）

【開き方】
ZIPを右クリックして「すべて展開」を選び、
「{output_name}」をダブルクリックしてください。
PCのChromeまたはMicrosoft Edgeで開き、黄色い再生ボタンを押します。
音が出ない場合は、画面下のスピーカーボタンで音声をオンにしてください。

音声・キャラクター画像・字幕はHTMLの中に入っています。
Pythonや音声ソフトのインストール、Webサーバー、GitHubへのログインは不要です。
本編の再生にインターネット接続は不要です。出典の記事を開くときだけ必要です。
スマートフォンでは、ファイルを開くアプリによって動作しない場合があります。

【内容】
{display_date}の試験放送、約{duration}です。新しいニュースには自動更新されません。
MP3は音声だけで聴くためのファイルです。キャラクター表示にはHTMLを使ってください。

【共有】
渡した相手は、この放送を保存してオフラインで聴けます。
ファイルの転送やコピーを制限する機能、あとから閲覧を取り消す機能はありません。
URLによる一般公開は行っていません。

【クレジット】
声：COEIROINK:リリンちゃん（のーまる）
キャラクター画像：AI生成
プレーヤー原作：monoradio102/myradio
COEIROINKの音声を素材として再配布したり、音声モデルの学習に使ったりしないでください。
音声の利用条件：https://coeiroink.com/terms
https://coeiroink.com/character/audio-character/lilin-m
'''
    (OUT / 'ダウンロード版の使い方.txt').write_text(readme, encoding='utf-8-sig')
    archive = OUT / f'ニュースラジオ_{DAY}_お渡し用.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(OUT / output_name, output_name)
        z.write(OUT / 'ダウンロード版の使い方.txt', 'はじめに.txt')
        z.writestr('プレーヤーのライセンス.txt', license_text)
        z.write(SITE / f'audio/{DAY}-ja.mp3', f'音声だけ_{DAY}.mp3')
    print(json.dumps({'html':str(OUT / output_name),'zip':str(archive),'zip_bytes':archive.stat().st_size}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default=DAY)
    DAY = parser.parse_args().date
    dt.date.fromisoformat(DAY)
    build()
