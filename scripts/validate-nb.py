#! /usr/bin/env python
import argparse
import logging
import os

import nbformat

from nbtranslate import core

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Converts to python code')
    parser.add_argument('filename', required=True)
    parsed = parser.parse_args()
    input_file = parsed.filename

    with open(input_file) as f:
        nb = nbformat.read(f, as_version=4)
    is_valid = core.validate_notebook_translation(nb)
    if is_valid:
        print(f'The notebook "{input_file}" is valid')
    else:
        raise ValueError(f'The notebook "{input_file}" is NOT valid')
    # TODO: Add some information on why it's not valid, like the cell that failed


if __name__ == '__main__':
    main()
