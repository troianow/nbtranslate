import nbtemplate
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


class NBTemplateTests(unittest.TestCase):
    def test_back_and_forth(self):
        # this tests that turning code into notebook and back is a noop
        cells = nbtemplate.split_code_to_cells(code_1)
        nb = nbtemplate.cells_to_notebook(cells)
        reconstructed_code = nbtemplate.cells_to_code(nbtemplate.nb_to_cells(nb))

        # The two notebooks should be equivalent up to empty lines. TODO: Fix it to make it exact
        reconstructed_code = '\n'.join([a for a in reconstructed_code.split('\n') if len(a) > 0])
        code = '\n'.join([a for a in code_1.split('\n') if len(a) > 0])
        self.assertEqual(reconstructed_code, code)
