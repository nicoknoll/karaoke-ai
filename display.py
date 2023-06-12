import pygame

# from lib.constants import SCREEN_WIDTH, SCREEN_HEIGHT
# from viewcontrollers.Base import BaseView
import subprocess as sp


SCREEN_WIDTH = 720
SCREEN_HEIGHT = 405

FFMPEG_BIN = "ffmpeg"
BYTES_PER_FRAME = SCREEN_WIDTH * SCREEN_HEIGHT * 3


command = [
    FFMPEG_BIN,
    "-loglevel",
    "quiet",
    "-i",
    "out/corinne_bailey_rae_put_your_records_on/generated.mp4",
    "-f",
    "image2pipe",
    "-pix_fmt",
    "rgb24",
    "-vcodec",
    "rawvideo",
    "-",
]
proc = sp.Popen(command, stdout=sp.PIPE, bufsize=BYTES_PER_FRAME * 2)

# fps = video.get(cv2.CAP_PROP_FPS)

window = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

fps = 30

run = True

raw_image = proc.stdout.read(BYTES_PER_FRAME)
image = pygame.image.frombuffer(raw_image, (SCREEN_WIDTH, SCREEN_HEIGHT), "RGB")
proc.stdout.flush()
window.blit(image, (0, 0))


while run:
    clock.tick(fps)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

    raw_image = proc.stdout.read(BYTES_PER_FRAME)
    image = pygame.image.frombuffer(raw_image, (SCREEN_WIDTH, SCREEN_HEIGHT), "RGB")
    proc.stdout.flush()

    window.blit(image, (0, 0))

    pygame.display.flip()

pygame.quit()
exit()
