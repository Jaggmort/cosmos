import time
import curses
import asyncio
import random
import os
from curses_tools import get_frame_size, draw_frame
from fire_animation import fire
from itertools import cycle


TIC_TIMEOUT = 0.1
STAR_SYMBOLS = ["+", "*", ".", ":"]
SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 452
RIGHT_KEY_CODE = 454
UP_KEY_CODE = 450
DOWN_KEY_CODE = 456


async def sleep(ticks=1):
    for _ in range(ticks):
        await asyncio.sleep(0)


async def blink(canvas, row, column, symbol='*', offset_tics=3):
    await sleep(offset_tics)
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(20)

        canvas.addstr(row, column, symbol)
        await sleep(3)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(5)

        canvas.addstr(row, column, symbol)
        await sleep(3)


def draw(canvas, star_numbers):
    canvas.nodelay(1)
    canvas.border()
    curses.curs_set(False)
    max_row, max_col = canvas.getmaxyx()
    corutines = []
    for star in range(star_numbers):
        star = blink(canvas,
                     random.randint(1, max_row - 1),
                     random.randint(1, max_col - 1),
                     symbol=random.choice(STAR_SYMBOLS),
                     offset_tics=random.randint(0, 10),
                     )
        corutines.append(star)
    shot = fire(canvas, int(max_row-1), int(max_col/2))
    corutines.append(shot)
    rocket = draw_rocket(canvas)
    corutines.append(rocket)

    while True:
        for corutine in corutines.copy():
            try:
                corutine.send(None)
            except StopIteration:
                corutines.remove(corutine)
        canvas.refresh()                
        time.sleep(TIC_TIMEOUT)


def read_frame(dir, file_name):
    file_path = os.path.join(dir, file_name)
    with open(file_path) as animation_file:
        return animation_file.read()


def get_list_frames(folder):
    return [read_frame(folder, file_name) for file_name in os.listdir(folder)]


async def draw_rocket(canvas):
    max_row, max_col = canvas.getmaxyx()
    rocket_frames = get_list_frames('./rocket')
    current_frame = rocket_frames[0]
    rocket_rows, rocket_cols = get_frame_size(current_frame)
    iterator = cycle(rocket_frames)
    row = (max_row) / 2
    col = (max_col) / 2
    count = 0

    while True:
        draw_frame(canvas, row, col, current_frame, negative=True)
        count += 1

        pressed_key_code = canvas.getch()
        if pressed_key_code == 452 and rocket_cols - 2 < col:
            col -= 2
        if pressed_key_code == 454 and max_col - rocket_cols > col + 2:
            col += 2
        if pressed_key_code == 450 and row > 1:
            row -= 1
        if pressed_key_code == 456 and max_row - rocket_rows >= row + 2:
            row += 1

        if count == 2:
            current_frame = next(iterator)
            count = 0
        draw_frame(canvas, row, col, current_frame, negative=False)
        await sleep(1)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw, 20)
