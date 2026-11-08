"""Assemble rendered speech, exact subtitle timings and a myradio episode."""
import argparse
import array
import datetime as dt
import json
from pathlib import Path
import sys
import wave

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'vendor'))
import lameenc


def assemble(source_path, render_dir, site_dir):
    episode = json.loads(source_path.read_text(encoding='utf-8-sig'))
    rendered = json.loads((render_dir / 'rendered.json').read_text(encoding='utf-8-sig'))
    day = dt.date.fromisoformat(episode['date'])
    if episode.get('lang') != 'ja' or not 4 <= len(episode['news']) <= 8:
        raise ValueError('Expected a Japanese episode with 4–8 stories')
    for story in episode['news']:
        if not story.get('url', '').startswith('https://') or not story.get('points'):
            raise ValueError('Every story needs points and a verified HTTPS source')
    pcm = bytearray()
    rate = None
    timings, segments = [], []

    def silence(seconds):
        pcm.extend(b'\0\0' * round(rate * seconds))

    for i, line in enumerate(rendered['lines']):
        with wave.open(str(render_dir / line['file']), 'rb') as wav:
            if (wav.getnchannels(), wav.getsampwidth()) != (1, 2):
                raise ValueError('Expected mono signed 16-bit WAV')
            if rate is None:
                rate = wav.getframerate()
                silence(0.4)
            if wav.getframerate() != rate:
                raise ValueError('Mixed sample rates')
            frames = wav.readframes(wav.getnframes())
        if len(frames) < rate or max(array.array('h', frames), default=0) < 30:
            raise ValueError('Silent or unexpectedly short speech')
        start = len(pcm) / (rate * 2)
        if not segments or segments[-1]['kind'] != line['kind'] or segments[-1]['index'] != line['index']:
            if segments:
                segments[-1]['end'] = round(start, 3)
            segments.append({'kind': line['kind'], 'index': line['index'], 'start': round(start, 3)})
        pcm.extend(frames)
        end = len(pcm) / (rate * 2)
        timings.append({'start': round(start, 3), 'end': round(end, 3), 'show': line['show'], 'part': line['part']})
        next_line = rendered['lines'][i + 1] if i + 1 < len(rendered['lines']) else None
        silence(0.8 if next_line is None or next_line['part'] != line['part'] else 0.2)
    duration = len(pcm) / (rate * 2)
    segments[-1]['end'] = round(duration, 3)
    if not 300 <= duration <= 600:
        raise ValueError(f'Episode duration {duration:.2f}s is outside requested 5–10 minutes')
    encoder = lameenc.Encoder()
    encoder.set_in_sample_rate(rate)
    encoder.set_channels(1)
    encoder.set_bit_rate(48)
    encoder.set_quality(2)
    mp3 = encoder.encode(bytes(pcm)) + encoder.flush()
    if len(mp3) < 100_000:
        raise ValueError('Unexpectedly small MP3')
    name = f'{day.isoformat()}-ja'
    audio_dir = site_dir / 'audio'
    episode_dir = site_dir / 'episodes'
    audio_dir.mkdir(parents=True, exist_ok=True)
    episode_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / f'{name}.mp3'
    audio_path.write_bytes(mp3)
    episode.update(seconds=round(duration, 3), lines_timed=timings, segments=segments,
                   audio=f'audio/{name}.mp3', made_at=dt.datetime.now(dt.timezone.utc).isoformat())
    episode_path = episode_dir / f'{name}.json'
    episode_path.write_text(json.dumps(episode, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    index_path = site_dir / 'episodes.json'
    old_index = json.loads(index_path.read_text(encoding='utf-8-sig')) if index_path.exists() else []
    # Preserve the published archive even when only today's episode was fetched.
    index = [x for x in old_index if x['date'] != day.isoformat()]
    index.append({'date': day.isoformat(), 'ja': {'title': episode['title'], 'seconds': round(duration, 3)}})
    index.sort(key=lambda x: x['date'], reverse=True)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'seconds': round(duration, 3), 'minutes': round(duration / 60, 2), 'lines': len(timings),
                      'audio_bytes': len(mp3), 'audio': str(audio_path), 'episode': str(episode_path)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('renders', type=Path)
    parser.add_argument('site', type=Path)
    args = parser.parse_args()
    assemble(args.source, args.renders, args.site)
