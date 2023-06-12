from moviepy.editor import *

from lyrics import Line, Lyrics

OFFSET_START = 1
OFFSET_END = 4

FADEOUT_SPEED = 2

CANVAS_WIDTH = 720
CANVAS_HEIGHT = int(CANVAS_WIDTH * 9 / 16)

SEGMENT_THRESHOLD = 2


text_kwargs = {
    "font": "Fabrikat-Mono-Medium",  # Real-Vhs-Font-Regular  # Camcorder-Monospaced-Regular  # VCR-OSD-Mono  # Fabrikat-Mono-Medium
    "kerning": 0,
    "fontsize": 40,
}


def get_line_breakpoints(line):
    full_width = TextClip(line.text, color="white", **text_kwargs).size[0]
    current_width = 0
    breakpoints = []

    for word in line.words:
        word_width = TextClip(word.text + " ", color="white", **text_kwargs).size[0]
        current_width += word_width

        current_percentage = min(current_width / full_width, 1)

        breakpoints.append((word.end - line.start, current_percentage))

    breakpoints.append((line.end - line.start, 1))

    return breakpoints


def get_text_line_clip(
    text, duration, animation_duration=None, animation_offset=0, breakpoints=None
):
    text = text.upper()
    text_clip = TextClip(text, color="white", **text_kwargs).set_duration(duration)
    text_size = text_clip.size

    # add border
    text_clip_border = (
        TextClip(
            text,
            color="black",
            stroke_color="black",
            stroke_width=4,
            **text_kwargs,
        )
        .set_duration(duration)
        .set_position((-2, -2))
    )

    if animation_duration is None:
        return CompositeVideoClip(
            [text_clip_border, text_clip], size=text_size
        ).set_duration(duration)

    # add animated layer
    text_overlay = TextClip(
        text,
        color="orange",
        **text_kwargs,
    )

    if not breakpoints:
        breakpoints = [(animation_duration, 1)]

    def animated_width(gf, t):
        frame = gf(t)

        current_breakpoint = (0, 0)
        next_breakpoint = (animation_duration, 1)
        for b in breakpoints:
            if b[0] >= t:
                next_breakpoint = b
                break
            current_breakpoint = b

        current_width = current_breakpoint[1] * text_size[0]
        next_width = next_breakpoint[1] * text_size[0]
        width_diff = next_width - current_width

        breakpoint_progress = (
            (t - current_breakpoint[0]) / (next_breakpoint[0] - current_breakpoint[0])
            if next_breakpoint[0] - current_breakpoint[0] > 0
            else 1
        )

        return frame[:, : int(current_width + width_diff * breakpoint_progress)]

    text_overlay = text_overlay.fl(animated_width, apply_to="mask")
    text_overlay = text_overlay.set_start(animation_offset)
    text_overlay = text_overlay.set_duration(duration - animation_offset)

    return CompositeVideoClip(
        [text_clip_border, text_clip, text_overlay], size=text_size
    )


def get_pair_clip(first_line, second_line):
    clips = []

    # always one second buffer in the front and 4 seconds in the back
    visible_at = first_line.start - OFFSET_START
    visible_until = max(
        second_line and second_line.end + OFFSET_END or 0, first_line.end + OFFSET_END
    )
    visible_for = visible_until - visible_at

    clips.append(
        get_text_line_clip(
            first_line.text,
            duration=visible_for,
            animation_duration=(first_line.end - first_line.start),
            animation_offset=(first_line.start - visible_at),
            breakpoints=get_line_breakpoints(first_line),
        ).set_pos(("center", "center"))
    )

    if second_line:
        clips[0] = clips[0].set_pos(("center", "top"))

        clips.append(
            get_text_line_clip(
                second_line.text,
                duration=visible_for,
                animation_duration=(second_line.end - second_line.start),
                animation_offset=(second_line.start - visible_at),
                breakpoints=get_line_breakpoints(second_line),
            ).set_pos(("center", "bottom"))
        )

    return (
        visible_at,
        visible_until,
        CompositeVideoClip(
            clips,
            size=(
                CANVAS_WIDTH,
                clips[0].size[1]
                + 20
                + (clips[1].size[1] if len(clips) > 1 else clips[0].size[1]),
            ),
        ),
    )


def get_title_clip(song_name, artist_name):
    song_clip = get_text_line_clip(
        song_name,
        duration=10,
        animation_duration=0,
        animation_offset=10,
    ).set_pos(("center", "top"))

    artist_clip = get_text_line_clip(
        artist_name,
        duration=10,
        animation_duration=0,
        animation_offset=10,
    ).set_pos(("center", "bottom"))

    return CompositeVideoClip(
        [song_clip, artist_clip],
        size=(CANVAS_WIDTH, song_clip.size[1] + 20 + artist_clip.size[1]),
    ).set_position(("center", "center"))


def break_balanced(line: Line, max_length=25) -> [Line]:
    """
    Break long strings into evenly distributed lines

    Example:
        break_balanced(Line("This is a very long line that should be broken into multiple lines"))
        [Line("This is a very long line"), Line("that should be broken"), Line("into multiple lines")]
    """
    lines = []

    words = line.words
    text = line.text

    num_lines = len(text) / max_length
    chars_per_line = len(text) / num_lines

    line_words = []
    chars = 0

    for word in words:
        next_chars = chars + len(word.text) + 1
        chars_to_chars_per_line = abs(chars_per_line - chars)
        next_chars_to_chars_per_line = abs(chars_per_line - next_chars)

        if (
            next_chars_to_chars_per_line > chars_to_chars_per_line
            or next_chars > max_length
        ):
            lines.append(Line.from_words(line_words))
            line_words = []
            chars = 0

        line_words.append(word)
        chars += len(word.text) + 1

    if line_words:
        lines.append(Line.from_words(line_words))

    return lines


class VideoGenerator:
    def __init__(
        self,
        canvas_size=(CANVAS_WIDTH, CANVAS_HEIGHT),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        duration=None,
        bg_color=None,
        bg_image_path=None,
        bg_blur=False,
        text_font="Mindset",
        text_fontsize=40,
        text_color="white",
        text_kerning=5,
        text_active_color="green",
    ):
        self.canvas_size = canvas_size
        self.canvas_width = canvas_size[0]
        self.canvas_height = canvas_size[1]

        self.fps = fps
        self.codec = codec
        self.audio_codec = audio_codec
        self.duration = duration

        self.bg_color = bg_color
        self.bg_image_path = bg_image_path
        self.bg_blur = bg_blur

        self.text_font = text_font
        self.text_fontsize = text_fontsize
        self.text_color = text_color
        self.text_kerning = text_kerning
        self.text_active_color = text_active_color

    def generate(
        self,
        lyrics: Lyrics,
        audio_path: str,
        no_vocals_path: str,
        output_path=None,
        song_name=None,
        artist_name=None,
    ):

        lines = []
        for i, line in enumerate(lyrics.lines):
            if not line.words or not line.text.strip():
                continue

            if len(line.text) < 30:
                lines.append(line)
                continue

            lines.extend(break_balanced(line))

        segments = []
        segment = []
        for i, line in enumerate(lines):
            prev_line = lines[i - 1] if i > 0 else None
            if not prev_line:
                segment.append(line)
                continue

            if (
                line.start
                and prev_line.end
                and line.start - prev_line.end > SEGMENT_THRESHOLD
            ):
                segments.append(segment)
                segment = []

            segment.append(line)

        if segment:
            segments.append(segment)

        segment_clips = []

        # add interpret and title
        if song_name and artist_name:
            duration_before_first_line = lines[0].start
            duration = min(duration_before_first_line - 3, 3)

            if duration > 1:
                segment_clips.append(
                    (
                        0,
                        duration,
                        get_title_clip(song_name, artist_name).set_duration(duration),
                    )
                )

        for segment in segments:
            pair_clips = []

            for i in range(0, len(segment), 2):
                pair_clips.append(
                    get_pair_clip(
                        segment[i], segment[i + 1] if i + 1 < len(segment) else None
                    )
                )

            for i, (visible_at, visible_until, pair_clip) in enumerate(pair_clips):
                position = ("center", "top" if i % 2 == 0 else "bottom")
                pair_clip = pair_clip.set_pos(position)
                pair_clip = pair_clip.set_start(visible_at)
                pair_clip = pair_clip.set_end(visible_until - 3)
                pair_clip = pair_clip.crossfadein(0.2).crossfadeout(1.1)

                pair_clips[i] = (visible_at, visible_until, pair_clip)

            segment_clips.extend(pair_clips)

        no_vocals_clip = AudioFileClip(no_vocals_path)
        audio_clip = AudioFileClip(audio_path).volumex(0.3)

        cac = CompositeAudioClip([audio_clip, no_vocals_clip])
        segments_clip = CompositeVideoClip(
            [p[2] for p in segment_clips], size=(CANVAS_WIDTH, CANVAS_HEIGHT - 140)
        ).set_pos("center")

        if self.bg_image_path:

            from skimage.filters import gaussian
            from moviepy.editor import VideoFileClip

            def blur(image):
                if not self.bg_blur:
                    return image

                return gaussian(image.astype(float), sigma=self.bg_blur)

            bg_clip = (
                ImageClip(self.bg_image_path)
                .resize((CANVAS_WIDTH, CANVAS_HEIGHT))
                .fl_image(blur)
            )

            cvc = CompositeVideoClip(
                [bg_clip, segments_clip],
                size=(CANVAS_WIDTH, CANVAS_HEIGHT),
                bg_color=self.bg_color or (0, 0, 0),
                # use_bgclip=True,
            )
        else:
            cvc = CompositeVideoClip(
                [segments_clip],
                size=(CANVAS_WIDTH, CANVAS_HEIGHT),
                bg_color=self.bg_color or (0, 0, 0),
            )

        cvc.audio = cac

        out_path = (
            output_path or f"out/{os.path.basename(audio_path).split('.')[0]}.mp4"
        )

        cvc.set_duration(90 or cac.duration).write_videofile(
            out_path,
            codec="libx264",  # "libx264",  # 'mpeg4',
            audio_codec="aac",
            fps=30,
        )

        return out_path


def generate_video(
    lyrics, audio_path, no_vocals_path, output_path, song_name=None, artist_name=None
):
    generator = VideoGenerator()
    return generator.generate(
        lyrics, audio_path, no_vocals_path, output_path, song_name, artist_name
    )


if __name__ == "__main__":
    # generate_video()
    pass
