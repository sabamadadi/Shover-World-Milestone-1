import numpy as np
import pytest
import sys
sys.path.insert(0, 'C:\\Users\\Asus\\Desktop\\shover_world')
from environment import (
    ShoverWorldEnv,
    EMPTY,
    BOX_MIN,
    BOX_MAX,
)


def make_env_with_grid(grid, agent_pos, initial_force=4.0, unit_force=1.0):
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
        initial_force=initial_force,
        unit_force=unit_force,
        seed=0,
    )
    env.grid = np.array(grid, dtype=np.int32)
    env.n_rows, env.n_cols = env.grid.shape
    env.agent_row, env.agent_col = agent_pos
    env.stamina = env.initial_stamina
    env.timestep = 0
    env.non_stationary_until = np.zeros((4, n_rows, n_cols), dtype=np.int32)
    env.perfect_squares = {}
    return env


def test_push_chain_length_and_movement():
    # three boxes in a row to the right of the agent
    grid = [
        [0, 0, 0, 0, 0],
        [0, 10, 10, 10, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ]
    env = make_env_with_grid(grid, agent_pos=(1, 0), initial_force=5.0, unit_force=2.0)

    before_stamina = env.stamina
    action = (np.array([1, 0]), 1)  # 1 -> right (after +1)
    obs, reward, done, info = env.step(action)

    # chain length 3, boxes shifted one cell to the right
    assert info["chain_length"] == 3
    assert env.grid[1, 1] == EMPTY
    assert env.grid[1, 2] == 10
    assert env.grid[1, 3] == 10
    assert env.grid[1, 4] == 10
    # agent moved into former head box cell
    assert env.agent_row == 1 and env.agent_col == 1
    # push cost = 5 + 2*3 = 11 plus baseline 1
    expected_delta = 1 + 11
    assert pytest.approx(before_stamina - env.stamina, rel=1e-6) == expected_delta


def test_push_blocked_by_wall():
    # boxes blocked by edge -> push invalid
    grid = [
        [0, 0, 0, 0, 0],
        [0, 10, 10, 10, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ]
    env = make_env_with_grid(grid, agent_pos=(1, 1))
    # push left so last box would go out of bounds
    action = (np.array([1, 1]), 3)  # 3 -> left (after +1)
    obs, reward, done, info = env.step(action)

    assert info["chain_length"] == 0
    # boxes unchanged
    assert (env.grid[1] == np.array([0, 10, 10, 10, 0])).all()
