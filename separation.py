from pathlib import Path

import torch as th
from demucs.apply import apply_model
from demucs.audio import save_audio
from demucs.pretrained import get_model, DEFAULT_MODEL
from demucs.separate import load_track


def separate_vocals(audio_path, output_path=None):
    model = get_model(name=DEFAULT_MODEL)

    model.cpu()
    model.eval()

    audio_path = Path(audio_path)

    wav = load_track(audio_path, model.audio_channels, model.samplerate)

    ref = wav.mean(0)
    wav = (wav - ref.mean()) / ref.std()
    sources = apply_model(
        model,
        wav[None],
        device="cpu",
        shifts=1,
        split=True,
        overlap=0.25,
        progress=True,
        num_workers=0,
    )[0]
    sources = sources * ref.std() + ref.mean()

    out = Path(output_path or "out/separated/{track}")
    stem_name = "vocals"

    kwargs = {
        "samplerate": model.samplerate,
        "bitrate": 320,
        "clip": "rescale",
        "as_float": False,
        "bits_per_sample": 16,
    }

    sources = list(sources)
    vocals_stem = out / "{stem}.{ext}".format(
        track=audio_path.name.rsplit(".", 1)[0],
        trackext=audio_path.name.rsplit(".", 1)[-1],
        stem=stem_name,
        ext="wav",
    )
    vocals_stem.parent.mkdir(parents=True, exist_ok=True)
    save_audio(sources.pop(model.sources.index(stem_name)), str(vocals_stem), **kwargs)

    # Warning : after poping the stem, selected stem is no longer in the list 'sources'
    other_stem = th.zeros_like(sources[0])
    for i in sources:
        other_stem += i

    no_vocals_stem = out / "{stem}.{ext}".format(
        track=audio_path.name.rsplit(".", 1)[0],
        trackext=audio_path.name.rsplit(".", 1)[-1],
        stem="no_" + stem_name,
        ext="wav",
    )
    no_vocals_stem.parent.mkdir(parents=True, exist_ok=True)
    save_audio(other_stem, str(no_vocals_stem), **kwargs)

    return str(vocals_stem), str(no_vocals_stem)


if __name__ == "__main__":
    separate_vocals("data/ilomilo.mp3")
