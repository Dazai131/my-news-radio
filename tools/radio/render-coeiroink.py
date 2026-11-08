"""Render a Japanese episode with the local COEIROINK engine and Lilin."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import urllib.error
import wave

API = 'http://127.0.0.1:50032'


def request(path, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(API + path, data=data,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'COEIROINK {path}: {error.code}: {error.read().decode("utf-8", errors="replace")[:2000]}') from error


def render(source, out, speed=1.0):
    episode = json.loads(source.read_text(encoding='utf-8-sig'))
    speakers = json.loads(request('/v1/speakers'))
    matches = [s for s in speakers if s.get('speakerName') == 'リリンちゃん']
    if len(matches) != 1:
        raise RuntimeError('COEIROINKにリリンちゃんの音声を追加してください。別の声には切り替えません。')
    speaker = matches[0]
    styles = speaker['styles']
    normal = [s for s in styles if s.get('styleName', '').lower() in ('ノーマル', 'のーまる', 'normal')]
    if len(normal) != 1:
        raise RuntimeError('リリンちゃんのノーマルスタイルを確認できません。')
    style = normal[0]
    out.mkdir(parents=True, exist_ok=True)
    parts = [('opening', None, episode['opening'])]
    parts += [('news', i, story['lines']) for i, story in enumerate(episode['news'])]
    parts += [('closing', None, episode['closing'])]
    lines = []
    for part, (kind, index, source_lines) in enumerate(parts):
        for line in source_lines:
            if not line['say'].strip() or not line['show'].strip():
                raise ValueError('Empty spoken line')
            body = dict(volumeScale=1, pitchScale=0, intonationScale=1,
                        prePhonemeLength=0, postPhonemeLength=0,
                        outputSamplingRate=24000,
                        speakerUuid=speaker['speakerUuid'], styleId=style['styleId'],
                        text=line['say'], prosodyDetail=[], speedScale=speed)
            filename = f'{len(lines):03}.wav'
            target = out / filename
            fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
            stamp = target.with_suffix('.sha256')
            if not (target.exists() and stamp.exists() and stamp.read_text() == fingerprint):
                audio = request('/v1/synthesis', body)
                temporary = target.with_suffix('.tmp.wav')
                temporary.write_bytes(audio)
                with wave.open(str(temporary), 'rb') as wav:
                    if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getnframes() == 0:
                        raise ValueError('Expected nonempty mono 16-bit WAV from COEIROINK')
                temporary.replace(target)
                stamp.write_text(fingerprint)
            lines.append(dict(file=filename, part=part, kind=kind, index=index, show=line['show']))
            print(f'Rendered {filename}', flush=True)
    metadata = dict(voice='COEIROINK:リリンちゃん', speaker_uuid=speaker['speakerUuid'],
                    style_id=style['styleId'], style_name=style['styleName'], speed=speed, lines=lines)
    (out / 'rendered.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--speed', type=float, default=1.0)
    args = parser.parse_args()
    if not .8 <= args.speed <= 1.2:
        parser.error('Speed must remain between 0.8 and 1.2')
    render(args.source, args.output, args.speed)
