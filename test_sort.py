from shuffle import sort_by_awkfield, sort_by_field


def test_dsusort():
    input = ['a z c', 'z q r', 'w w w']
    output = ['z q r', 'w w w', 'a z c']
    assert sort_by_field(input, 2) == output


def test_dsusort2():
    input = ['a z c', 'z q r', 'w w w', 'b']
    output = ['b', 'z q r', 'w w w', 'a z c']
    assert sort_by_field(input, 2) == output


def test_sort_by_awkfield():
    input = ['a z c', 'z q r', 'w w w']
    output = ['z q r', 'w w w', 'a z c']
    assert sort_by_awkfield(input, 2) == output


def test_sort_by_awkfield2():
    input = ['a z c', 'z q r', 'w w w', 'b']
    output = ['b', 'z q r', 'w w w', 'a z c']
    assert sort_by_awkfield(input, 2) == output
