import time
import curses
import asyncio
import random
import os
from tools.curses_tools import get_frame_size, draw_frame, read_controls
from tools.physics import update_speed
from tools.obstacles import Obstacle
from tools.explosions import explode
from tools.game_scenario import get_garbage_delay_tics
from itertools import cycle


TIC_TIMEOUT = 0.1
STAR_SYMBOLS = ["+", "*", ".", ":"]
CORUTINES = []
OBSTACLES = []
OBSTACLES_IN_LAST_COLLISIONS = []
YEAR = 1957
PHRASES = {
    1957: "First Sputnik",
    1961: "Gagarin flew!",
    1969: "Armstrong got on the moon!",
    1971: "First orbital space station Salute-1",
    1981: "Flight of the Shuttle Columbia",
    1998: 'ISS start building',
    2011: 'Messenger launch to Mercury',
    2020: "Take the plasma gun! Shoot the garbage!",
}


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
    garbage_frames = get_list_frames('./images/garbage')
    for _ in range(star_numbers):
        CORUTINES.append(blink(canvas,
                               random.randint(1, max_row - 2),
                               random.randint(1, max_col - 2),
                               symbol=random.choice(STAR_SYMBOLS),
                               offset_tics=random.randint(0, 10),
                               ))
    CORUTINES.append(draw_rocket(canvas))
    CORUTINES.append(fill_orbit_with_garbage(canvas, max_col, garbage_frames))
    CORUTINES.append(show_year(canvas, PHRASES, max_row))
    while True:
        for corutine in CORUTINES.copy():
            try:
                corutine.send(None)
            except StopIteration:
                CORUTINES.remove(corutine)
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
    rocket_frames = get_list_frames('./images/rocket')
    current_frame = rocket_frames[0]
    rocket_rows, rocket_cols = get_frame_size(current_frame)
    iterator = cycle(rocket_frames)
    row = (max_row - 1) / 2
    col = (max_col) / 2
    count = 0
    row_speed = col_speed = 0
    while True:
        draw_frame(canvas, row, col, current_frame, negative=True)
        count += 1
        move_row, move_col, space = read_controls(canvas)
        row_speed, col_speed = update_speed(row_speed, col_speed, move_row, move_col)

        if row + row_speed + rocket_rows > max_row - 1 or row + row_speed < 1:
            row_speed = 0
        if col + col_speed + rocket_cols > max_col - 1 or col + col_speed < 1:
            col_speed = 0
        row += row_speed
        col += col_speed

        if space:
            CORUTINES.append(fire(canvas, row-1, col+2))
        if count == 2:
            current_frame = next(iterator)
            count = 0

        for obstacle in OBSTACLES:
            if obstacle.has_collision(row, col):
                game_over = read_frame('./images', 'game_over.txt')
                over_row, over_col = get_frame_size(game_over)
                CORUTINES.append(print_game_over(canvas, (max_row-over_row)/2, (max_col-over_col)/2, game_over))
                return

        draw_frame(canvas, row, col, current_frame, negative=False)
        await sleep(1)


async def fly_garbage(canvas, col, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    max_row, max_col = canvas.getmaxyx()
    garbage_rows, garbage_cols = get_frame_size(garbage_frame)
    row = 1
    garbage_obstacle_frame = Obstacle(row, col, garbage_rows, garbage_cols)
    OBSTACLES.append(garbage_obstacle_frame)
    await sleep(1)

    while row < max_row - 1 - garbage_rows and col > 1 and col + garbage_cols < max_col - 1:
        draw_frame(canvas, row, col, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, col, garbage_frame, negative=True)
        row += speed
        garbage_obstacle_frame.row += speed
        for obstacle in OBSTACLES_IN_LAST_COLLISIONS:
            if garbage_obstacle_frame is obstacle:
                OBSTACLES.remove(obstacle)
                await explode(canvas, row, col)
                return


async def fill_orbit_with_garbage(canvas, max_col, garbage_frames):
    while True:
        if YEAR > 1961:
            CORUTINES.append(fly_garbage(canvas,
                                         random.randint(1, max_col-1),
                                         random.choice(garbage_frames),
                                         ))
            await sleep(get_garbage_delay_tics(YEAR))
        else:
            await asyncio.sleep(0)


async def fire(canvas, start_row, start_column, rows_speed=-1, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""
    if YEAR >= 2020:
        row, column = start_row, start_column

        canvas.addstr(round(row), round(column), '*')
        await asyncio.sleep(0)

        canvas.addstr(round(row), round(column), 'O')
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')

        row += rows_speed
        column += columns_speed

        symbol = '-' if columns_speed else '|'

        rows, columns = canvas.getmaxyx()
        max_row, max_column = rows - 1, columns - 1

        curses.beep()

        while 1 < row < max_row and 1 < column < max_column:
            canvas.addstr(round(row), round(column), symbol)
            await asyncio.sleep(0)
            canvas.addstr(round(row), round(column), ' ')
            row += rows_speed
            column += columns_speed

            for obstacle in OBSTACLES:
                if obstacle.has_collision(row, column):
                    OBSTACLES_IN_LAST_COLLISIONS.append(obstacle)
                    return


async def print_game_over(canvas, raw, col, frame):
    while True:
        draw_frame(canvas, raw, col, frame)
        await sleep(1)


def draw_message(canvas, year, phrase, row):
    small_window = canvas.derwin(3, 50, row - 3, 0)
    small_window.addstr(1, 2, f'{year}: {phrase}')
    small_window.refresh()


async def show_year(canvas, phrases, rows):
    global YEAR
    years = list(phrases)
    for YEAR, phrase in phrases.items():
        try:
            next_year = years[years.index(YEAR) + 1]
        except (ValueError, IndexError):
            next_year = YEAR
        for __ in range(5 * (next_year - YEAR)):
            draw_message(canvas, YEAR, phrase, rows)
            await sleep(1)
    while True:
        draw_message(canvas, YEAR, phrase, rows)
        await sleep(1)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw, 20)
