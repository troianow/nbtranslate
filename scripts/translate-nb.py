#! /usr/bin/env python
import argparse
import logging
import os
from nbtranslate import core

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Converts to python code')
    parser.add_argument('-i', '--input', required=True)
    parser.add_argument('-o', '--output')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--replace_ext', action='store_true')
    parsed = parser.parse_args()
    input_file = parsed.input
    output_file = parsed.output
    overwrite = parsed.overwrite
    replace_ext = parsed.replace_ext
    dirname = os.path.dirname(input_file)
    name, ext = os.path.splitext(os.path.basename(input_file))
    if ext not in ['.py', '.ipynb']:
        raise ValueError(f"The input's extension must end in `py` or `ipynb`. Got '{input_file}' instead")
    elif ext == '.py':
        new_ext = '.ipynb'
    else:
        new_ext = '.py'

    if output_file is None:
        output_file = os.path.join(dirname, f'{name}{new_ext}')
    else:
        base_output_file, out_ext = os.path.splitext(output_file)
        if replace_ext:
            output_file = base_output_file + new_ext
        elif out_ext != new_ext:
            raise ValueError(f"Since the input's extension is {ext}, the output's must be {new_ext}")

    if os.path.exists(output_file) and not overwrite:
        raise FileExistsError(
            'The file "{}" already exists. Chose another filename or set --overwrite'.format(output_file)
        )

    if ext == ".ipynb":
        cells = core.nb_file_to_cells(input_file)
        code = core.cells_to_code(cells)

        with open(output_file, 'w') as f:
            f.write(code)

    else:
        with open(input_file, 'r') as f:
            code = f.read(-1)
        cells = core.split_code_to_cells(code)
        nb = core.cells_to_notebook(cells)
        core.nb_to_file(nb, output_file, overwrite=overwrite)


if __name__ == '__main__':
    main()
