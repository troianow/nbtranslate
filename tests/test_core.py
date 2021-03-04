import os

from nbtranslate import core
import unittest


code_1 = '''

here_is_some_code = 123

# ----

and_some_other_code = {
    'foo': bar
}

"""
# cell
This is a markdown cell
```python
def this_is_a_test():
    pass
```

And this is using LaTeX:
Solve for $n$
$$ \exists a, b, c \in \mathbb{Z}\ a^n + b^n = c^n $$

"""

def foo():
    pass

# ----

foo()

# ---- new_section ----
def bar():
    pass


"""
# Another markdown comment
## Another header
This is text
"""
'''


def test_back_and_forth():
    # this tests that turning code into notebook and back is a noop
    cells = core.split_code_to_cells(code_1)
    nb = core.cells_to_notebook(cells)
    reconstructed_code = core.cells_to_code(core.nb_to_cells(nb))

    # The two notebooks should be equivalent up to empty lines. TODO: Fix it to make it exact
    reconstructed_code = '\n'.join([a for a in reconstructed_code.split('\n') if len(a) > 0])
    code = '\n'.join([a for a in code_1.split('\n') if len(a) > 0])
    assert reconstructed_code == code


def test_more_complex_example():
    directory = os.path.join(os.path.dirname(__file__), 'notebooks/more_complex_example.py')
