import os

import nbtranslate
from nbtranslate import core


def main():
    path = os.path.join(os.path.dirname(__file__), '../tests/notebooks/more_complex_example.ipynb')
    cells = core.nb_file_to_cells(path)
    code = core.cells_to_code(cells)
    print(code)
    cells2 = core.split_code_to_cells(code)


if __name__ == '__main__':
    main()
