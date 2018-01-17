from shuffle import dsusort


def test_dsusort():
    input = ['a z c', 'z q r', 'w w w']
    output = ['z q r', 'w w w', 'a z c']
    assert dsusort(input, 2) == output


def test_dsusort2():
    input = ['a z c', 'z q r', 'w w w', 'b']
    output = ['b', 'z q r', 'w w w', 'a z c']
    assert dsusort(input, 2) == output

