import numpy as np
import pytest
import sys
sys.path.insert(0, 'C:\\Users\\Asus\\Desktop\\shover_world')
from environment import (
    ShoverWorldEnv,
    EMPTY,
    LAVA,
    BARRIER,
)


def base_env():
    env = ShoverWorldEnv(
        render_mode=None,
        n_rows=5,
        n_cols=5,
        number_of_boxes=0,
        number_of_barriers=0,
        number_of_lavas=0,
        map_path=None,
        initial_force=4.0,
        unit_force=1.0,
        seed=0,
    )
    return env


def test_baseline_step_cost():
    env = base_env()
    env.grid[:] = EMPTY
    env.agent_row, env.agent_col = 2, 2

    before = env.stamina
    # move into empty cell
    obs, reward, done, info = env.step((np.array([2, 2]), 1))  # right
    assert env.stamina == pytest.approx(before - 1.0)  # only baseline
    assert reward < 0  # r_step


def test_push_stationary_vs_nonstationary():
    # two pushes in same direction: initial_force only paid once
    env = base_env()
    env.grid[:] = EMPTY
    env.grid[2, 2] = 10
    env.grid[2, 3] = 10
    env.agent_row, env.agent_col = 2, 1

    before = env.stamina
    # first push to the right: stationary
    obs, reward, done, info = env.step((np.array([2, 1]), 1))  # right
    after_first = env.stamina
    assert info["initial_force_charged"] is True

    # second push to the right, boxes are non-stationary
    obs, reward, done, info = env.step((np.array([2, 2]), 1))
    after_second = env.stamina
    assert info["initial_force_charged"] is False

    # non-stationary push should be cheaper than stationary
    assert after_first - after_second < before - after_first


def test_lava_refund():
    env = base_env()
    env.grid[:] = EMPTY
    env.grid[2, 2] = 10
    env.grid[2, 3] = LAVA
    env.agent_row, env.agent_col = 2, 1

    before = env.stamina
    obs, reward, done, info = env.step((np.array([2, 1]), 1))  # push right into lava

    # baseline + push cost - refund
    # push cost: initial_force(4) + unit_force(1)*1 = 5 => baseline1 => 6
    # refund: initial_force per box in lava = 4 => net -2
    assert pytest.approx(before - env.stamina, rel=1e-6) == 2.0
    assert info["lava_destroyed_this_step"] == 1
    # optional positive reward for lava
    assert reward > -10


def test_barrier_maker_stamina_gain():
    # 2x2 square -> Barrier Maker
    env = base_env()
    env.grid[:] = EMPTY
    env.grid[1, 1] = 10
    env.grid[1, 2] = 10
    env.grid[2, 1] = 10
    env.grid[2, 2] = 10
    env.agent_row, env.agent_col = 0, 0
    env._update_perfect_squares(initial=True)

    before = env.stamina
    obs, reward, done, info = env.step((np.array([0, 0]), 4))  # 4-> Barrier Maker (id 5)
    after = env.stamina

    # baseline -1 + Barrier Maker gain +4
    assert pytest.approx(after - before, rel=1e-6) == 3.0
    # cells turned into barriers
    assert (env.grid[1:3, 1:3] == BARRIER).all()


def test_hellify_effects():
    # 3x3 square for Hellify (n > 2)
    env = base_env()
    env.grid[:] = EMPTY
    for r in range(1, 4):
        for c in range(1, 4):
            env.grid[r, c] = 10
    env.agent_row, env.agent_col = 0, 0
    env._update_perfect_squares(initial=True)

    before_destroyed = env.total_destroyed
    obs, reward, done, info = env.step((np.array([0, 0]), 5))  # 5 -> Hellify (id 6)

    # border empty, interior lava
    assert env.grid[2, 2] == LAVA
    assert env.grid[1, 1] == EMPTY
    assert env.grid[1, 2] == EMPTY
    assert env.grid[1, 3] == EMPTY

    assert env.total_destroyed > before_destroyed
