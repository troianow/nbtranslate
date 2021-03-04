"""
# Import section
"""

import re
import sys
import os

# ----

from os import path
from concurrent import futures

"""
# Section 1

$$ \{n\in\mathbb{N^*} | \exists x, y, z \in\mathbb{Z},\ x^n + y^n = z^n\} = \{1, 2\}$$

## Iterator exhaustion
"""

# iterator exhaustion example

x = (a for a in range(10))
if 3 in x:
    print(list(x))

# expected answer: [4, 5, 6, 7, 8, 9]

"""
## Late binding example
"""

# late binding on lambdas
list_of_functions = [lambda x: x + n for n in range(10)]

[f(10) for f in list_of_functions]
# [19, 19, 19, 19, 19, 19, 19, 19, 19, 19]