import argparse
import json
import os.path
import re

from cover import download_cover
from lyrics import (
    merge_lyrics,
    WhisperLyricsExtractor,
    SpotifyLyricsExtractor,
    Lyrics,
)
from separation import separate_vocals
from video import VideoGenerator


def slugify(s):
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    s = s.replace("-", "_")
    return s


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("file", type=str)

    parser.add_argument("-n", "--name", type=str)
    parser.add_argument("-a", "--artist", type=str)

    return parser.parse_args()


def main():
    args = parse_args()

    song_path = args.file

    song_name = args.name
    artist_name = args.artist

    artist_and_name = os.path.splitext(os.path.basename(song_path))[0].split(" - ")

    if not artist_name:
        artist_name = artist_and_name[0]

    if not song_name:
        song_name = artist_and_name[1]

    song_query = f"{artist_name} - {song_name}"

    output_path = f"out/{slugify(f'{artist_name} {song_name}')}"
    os.makedirs(output_path, exist_ok=True)

    # print("Storing cover image")
    # cover_path = download_cover(song_query, output_path)

    cache = True

    print("Separating vocals")

    if not cache or not (
        os.path.exists(f"{output_path}/vocals.wav")
        and os.path.exists(f"{output_path}/no_vocals.wav")
    ):

        vocals_path, no_vocals_path = separate_vocals(song_path, output_path)
        print(f"Vocals saved to {vocals_path}, no vocals saved to {no_vocals_path}")
        # vocals_path = "out/robbie_williams_angels/vocals.wav"
        # no_vocals_path = "out/robbie_williams_angels/no_vocals.wav"

    else:
        print("Loading vocals from cache")
        vocals_path = f"{output_path}/vocals.wav"
        no_vocals_path = f"{output_path}/no_vocals.wav"

    if not cache or not os.path.exists(f"{output_path}/lyrics.json"):
        print("Extracting lyrics")

        if not cache or not os.path.exists(f"{output_path}/lyrics_spotify.json"):
            try:
                spotify_lyrics = SpotifyLyricsExtractor().extract(
                    song_query, vocals_path
                )
                with open(f"{output_path}/lyrics_spotify.json", "w") as f:
                    json.dump(spotify_lyrics.to_dict(), f, indent=4)
            except:
                spotify_lyrics = None

        else:
            with open(f"{output_path}/lyrics_spotify.json", "r") as f:
                spotify_lyrics = Lyrics.from_dict(json.load(f))

            print("Loaded Spotify lyrics from cache")

        if not cache or not os.path.exists(f"{output_path}/lyrics_whisper.json"):
            try:
                whisper_lyrics = WhisperLyricsExtractor().extract(
                    song_query, vocals_path
                )
                with open(f"{output_path}/lyrics_whisper.json", "w") as f:
                    json.dump(whisper_lyrics.to_dict(), f, indent=4)
            except Exception as e:
                print(e)
                whisper_lyrics = None

        else:
            with open(f"{output_path}/lyrics_whisper.json", "r") as f:
                whisper_lyrics = Lyrics.from_dict(json.load(f))

            print("Loaded Whisper lyrics from cache")

        return

        merged_lyrics = {}

        if not spotify_lyrics:
            print("No lyrics found on Spotify")
            merged_lyrics = whisper_lyrics

        if not whisper_lyrics:
            print("No lyrics found on Whisper")
            merged_lyrics = spotify_lyrics

        if spotify_lyrics and whisper_lyrics:
            merged_lyrics = merge_lyrics(spotify_lyrics, whisper_lyrics)

        with open(f"{output_path}/lyrics.json", "w") as f:
            pass
            # json.dump(merged_lyrics.to_dict(), f, indent=4)

    else:
        print("Loading lyrics from cache")
        merged_lyrics = Lyrics.from_dict(json.load(open(f"{output_path}/lyrics.json")))

    print("Generating video")
    video_path = VideoGenerator(bg_blur=100).generate(
        merged_lyrics,
        song_path,
        no_vocals_path,
        output_path=f"{output_path}/_generated.mp4",
        song_name=song_name,
        artist_name=artist_name,
    )
    print(f"Video saved to {video_path}")


if __name__ == "__main__":
    main()
