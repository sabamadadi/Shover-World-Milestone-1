import pytest
import sys
sys.path.insert(0, 'C:\\Users\\Asus\\Desktop\\shover_world')
from environment import ShoverWorldEnv, EMPTY, LAVA, BARRIER

def test_integer_map_loading_valid():
    text = """
    0 0 0 0
    0 10 10 0
    0 -100 0 0
    0 0 0 100
    """
    grid, agent = ShoverWorldEnv.parse_map_string(text)
    assert grid.shape == (4, 4)
    assert agent is None
    assert (grid[1, 1] == 10) and (grid[1, 2] == 10)


def test_symbolic_map_loading_valid():
    text = """
    .....
    .BB..
    .A.L.
    .#...
    .....
    """
    grid, agent = ShoverWorldEnv.parse_map_string(text)
    assert grid.shape == (5, 5)
    assert agent == (2, 1)  # row index of 'A', col index
    assert grid[1, 1] == 10  # B
    assert grid[2, 3] == -100  # L


def test_malformed_rows_raises():
    text = """
    0 0 0
    0 10
    """
    with pytest.raises(ValueError):
        ShoverWorldEnv.parse_map_string(text)


def test_invalid_symbol_raises():
    text = """
    ....
    .XZ.
    .A..
    ....
    """
    with pytest.raises(ValueError):
        ShoverWorldEnv.parse_map_string(text)


def test_box_on_edge_invalid():
    text = """
    B..
    .A.
    ...
    """
    with pytest.raises(ValueError):
        ShoverWorldEnv.parse_map_string(text)
