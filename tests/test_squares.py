import numpy as np
import sys
sys.path.insert(0, 'C:\\Users\\Asus\\Desktop\\shover_world')
from environment import ShoverWorldEnv, EMPTY, BOX_MIN, BOX_MAX


def make_env_for_squares(grid):
    n_rows = len(grid)
    n_cols = len(grid[0])
    env = ShoverWorldEnv(
        render_mode=None,
        n_rows=n_rows,
        n_cols=n_cols,
        number_of_boxes=0,
        number_of_barriers=0,
        number_of_lavas=0,
        map_path=None,
        seed=0,
    )
    env.grid = np.array(grid, dtype=np.int32)
    env.n_rows, env.n_cols = env.grid.shape
    env._update_perfect_squares(initial=True)
    return env


def test_detect_2x2_square():
    grid = [
        [0, 0, 0, 0],
        [0, 10, 10, 0],
        [0, 10, 10, 0],
        [0, 0, 0, 0],
    ]
    env = make_env_for_squares(grid)
    squares = env._sorted_perfect_squares()
    assert squares == [(2, 1, 1)]


def test_detect_3x3_square():
    grid = [
        [0, 0, 0, 0, 0],
        [0, 10, 10, 10, 0],
        [0, 10, 10, 10, 0],
        [0, 10, 10, 10, 0],
        [0, 0, 0, 0, 0],
    ]
    env = make_env_for_squares(grid)
    squares = env._sorted_perfect_squares()
    assert squares == [(3, 1, 1)]


def test_adjacent_boxes_break_perfect_square():
    # a 2x2 square but with an extra box touching the perimeter -> not perfect
    grid = [
        [0, 0, 0, 0],
        [0, 10, 10, 10],
        [0, 10, 10, 0],
        [0, 0, 0, 0],
    ]
    env = make_env_for_squares(grid)
    squares = env._sorted_perfect_squares()
    assert squares == []
