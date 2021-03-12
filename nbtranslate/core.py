import os
import re
import collections
import subprocess
import tempfile
import nbformat
from IPython import display


try:
    import pygments
    from pygments.formatters.html import HtmlFormatter
    from pygments.lexers.python import PythonLexer
except ModuleNotFoundError:
    pygments = None

try:
    import difflib
except ModuleNotFoundError:
    difflib = None


DIFFLIB_DIFFERENCE_TYPES = ['ndiff', 'context_diff', 'unified_diff']

PADDING_LENGTH = 4
SEPARATOR_COMMENT = '# ' + '-' * PADDING_LENGTH
SECTION_COMMENT_PATTERN = '# %s {} %s' % (('-' * PADDING_LENGTH,) * 2)
DEFAULT_SECTION = '__no_section__'
MD_CELL_PATTERN = '"""(.*?)"""'
CODE_MAGICS_PATTERN = '^%.+$'
CODE_MAGICS_MARKER = '# __magic__:'

RawCell = collections.namedtuple('RawCell', 'start end kind content')

# TODO: Add support for RAW cells. Should only be treated like markdown cells (with something identifying them)

class AbstractCell:
    _nb_cell_maker_name_ = None

    def __init__(self, content, section=None):
        self.content = content
        self.section = section

    def format_cell(self):
        return self.content

    @classmethod
    def parse_content(cls, c):
        return c

    def get_cell_maker_name(self):
        if self._nb_cell_maker_name_ is None:
            raise ValueError('This cell is not expected to be added to the notebook: {}'.format(type(self)))
        else:
            return self._nb_cell_maker_name_


class MarkdownCell(AbstractCell):
    _nb_cell_maker_name_ = 'new_markdown_cell'

    def format_cell(self):
        # escaping triple quotes because they're used as boundaries for markdown cells
        content = self.content.replace('"""', r'\"\"\"')
        return f'''"""\n{content}\n"""'''

    @classmethod
    def parse_content(cls, c):
        return c.replace(r'\"\"\"', '"""')


class Separator(AbstractCell):
    pass


class Section(AbstractCell):
    pass


class CodeCell(AbstractCell):
    _nb_cell_maker_name_ = 'new_code_cell'

    def format_cell(self):
        result = ''
        for l in self.content.split('\n'):
            res = re.match('\s*(%\S+)\s{0,1}(.*)$', l)

            if res is not None:
                mgc, expr = res.groups()
                result += f"{expr}{CODE_MAGICS_MARKER}{mgc}\n"
            else:
                result += l + '\n'
        return result

    @classmethod
    def parse_content(cls, c):
        result = ''
        for l in c.split('\n'):
            res = re.match(f'(.*){re.escape(CODE_MAGICS_MARKER)}(\S+)$', l)
            if res is not None:
                expr, mgc = res.groups()
                result += f'{mgc} {expr}\n'
            else:
                result += f'{l}\n'
        return result


CELL_TYPE_TO_TYPE = {
    'code': CodeCell,
    'markdown': MarkdownCell
}


def _split_to_raw_cells(code):
    """breaks the code into raw cells, a list of regions describing the code in terms of their functions (code areas,
    markdown areas, separators or sections)

    :param code: string representing the code
    :return:
    """
    raw_cells = []
    # capturing the MD raw_cells
    for m in re.finditer(MD_CELL_PATTERN, code, re.M + re.S):
        cell = RawCell(m.start(), m.end(), MarkdownCell, code[slice(*m.span(1))])
        raw_cells.append(cell)

    for m in re.finditer(SEPARATOR_COMMENT, code, re.M):
        cell = RawCell(m.start(), m.end(), Separator, None)
        raw_cells.append(cell)

    for m in re.finditer(SECTION_COMMENT_PATTERN.format('(.*)'), code, re.M):
        cell = RawCell(m.start(), m.end(), Section, m.group(1))
        raw_cells.append(cell)

    raw_cells = sorted(raw_cells, key=lambda x: (x.start, x.end))

    # when everything else is parsed, the rest is code
    code_cells = []
    if raw_cells[0].start > 0:
        code_cells += [RawCell(0, raw_cells[0].start - 1, CodeCell, code[:raw_cells[0].start - 1])]
    for previous_cell, next_cell in zip(raw_cells[:-1], raw_cells[1:]):
        start = previous_cell.end + 1
        end = next_cell.start
        if start < end:
            code_cells.append(RawCell(start, end, CodeCell, code[start:end]))

    code_cells.append(RawCell(raw_cells[-1].end + 1, len(code) + 1, CodeCell, code[raw_cells[-1].end + 1:]))

    raw_cells += code_cells
    raw_cells = sorted(raw_cells, key=lambda x: (x.start, x.end))

    return raw_cells


def _raw_cells_to_cells(raw_cells):
    """ converts the list of RawCell (convenience, intermediate format) to a list of AbstractCell

    :param raw_cells: list of raw cells
    :return: list of AbstractCell
    """
    cells = []
    section = DEFAULT_SECTION
    for c in raw_cells:
        content = c.content
        if issubclass(c.kind, Separator):
            continue
        if issubclass(c.kind, Section):
            section = c.content
            continue
        if issubclass(c.kind, MarkdownCell):
            content = c.kind.parse_content(content)

        if issubclass(c.kind, CodeCell):
            content = c.kind.parse_content(content)

        cells.append(c.kind(content, section))

    def to_content(c):
        content = c.content.strip('\n')
        return content

    # strip line returns and filter out empty cells
    cells = [type(a)(b, a.section) for a in cells for b in [to_content(a)] if b is not None]
    return cells


def split_code_to_cells(code):
    """converts code to a list of AbstractCell

    :param code: string representing the code
    :return: list of AbstractCell
    """
    raw_cells = _split_to_raw_cells(code)
    return _raw_cells_to_cells(raw_cells)


def code_file_to_cells(filename):
    with open(filename, 'r') as f:
        return split_code_to_cells(f.read())


def cells_to_code(cells):
    previous_section = DEFAULT_SECTION
    code = ''
    previous_cell = None
    for cell in cells:
        if previous_section != cell.section:
            code += SECTION_COMMENT_PATTERN.format(cell.section) + '\n'
        elif isinstance(cell, CodeCell) and isinstance(previous_cell, CodeCell):
            code += SEPARATOR_COMMENT + '\n'
        code += cell.format_cell() + '\n'
        previous_cell = cell
        previous_section = cell.section
    return code


def cells_to_notebook(cells):
    """converts the cells to a notebook object

    :param cells: list of AbstractCells
    :return: notebook object
    """
    nb = nbformat.v4.new_notebook()
    nb_cells = []
    for cell in cells:
        new_cell = getattr(nbformat.v4, cell.get_cell_maker_name())(cell.content)
        new_cell['metadata']['section'] = cell.section
        nb_cells.append(new_cell)

    nb['cells'] = nb_cells
    return nb


def nb_to_file(nb, filename, overwrite=False):
    """saves the notebook to the given filename

    :param nb: notebook object
    :param filename: name of the file to save it to
    :param overwrite: if true, overwrites the content at the filename
    """
    if os.path.exists(filename) and not overwrite:
        raise FileExistsError('The file "{}" already exists. Chose another filename or set overwrite=True'.format(filename))
    with open(filename, 'w') as f:
        nbformat.write(nb, f)


def nb_to_cells(nb):
    """converts the notebook object to a list of cells

    :param nb: notebook as loaded by nbformat.read
    :return: list of AbstractCells
    """
    cells = []
    for a in nb['cells']:
        section = a['metadata'].get('section', DEFAULT_SECTION)
        if a['cell_type'] == 'markdown':
            # TODO: Check this
            section = section.replace(r'\"\"\"', '"""')

        cell = CELL_TYPE_TO_TYPE[a['cell_type']](a['source'], section)
        cells.append(cell)
    return cells


def nb_file_to_cells(filename):
    """loads the notebook file and converts the json structure to a list of cells (i.e. AbstractCell)

    :param filename: file name of the notebook
    :return: list of AbstractCells
    """
    with open(filename) as f:
        nb = nbformat.read(f, as_version=4)
    return nb_to_cells(nb)


def diff_strings_pygment(string1, string2, typ='ndiff'):
    """compares the two string using pygment color syntax and python lexer/color scheme

    :param string1: first string to compare
    :param string2: second string to compare
    :param typ:
    :return: HTML code to be displayed in a notebook
    """
    assert pygments is not None, 'Please install the pygments package to used this function'
    assert typ in DIFFLIB_DIFFERENCE_TYPES, 'Unrecognized difference type. Allowed types are {}'.format(DIFFLIB_DIFFERENCE_TYPES)
    output = '<style>' + HtmlFormatter().get_style_defs('.highlight') + '</style>'
    diff_string = '\n'.join(getattr(difflib, typ)(string1.split('\n'), string2.split('\n')))
    output += pygments.highlight(diff_string, PythonLexer(), HtmlFormatter())
    return display.HTML(output)


def diff_strings_external(string1, string2, external_diff_command, pre_args=[]):
    """compares the two strings using an external program

    it is called as follows:
    <external_diff_command> <pre_args> file_for_string1 file_for_string_2

    WARNING: This code does not clean after itself as a lot of diff programs are non-blocking and don't send a
    signal when the comparison window is closed.

    :param string1: first string to compare
    :param string2: second string to compare
    :param external_diff_command: full path of the command to run
    :param pre_args: args to be passed after
    :return:
    """
    temp_dir = tempfile.mkdtemp()
    with open(os.path.join(temp_dir, 'nb1.ipynb'), 'w') as f1:
        f1.write(string1)
    with open(os.path.join(temp_dir, 'nb2.ipynb'), 'w') as f2:
        f2.write(string2)
    proc = subprocess.Popen([external_diff_command] + pre_args + [os.path.join(temp_dir, 'nb1.ipynb'), os.path.join(temp_dir, 'nb2.ipynb')], stdin=None, stdout=None, stderr=None, shell=False)
    proc.wait()
    # shutil.rmtree(temp_dir)


def compare_notebooks_code(nb1, nb2, external_diff_command=None, external_diff_args=[], use_html=True, typ='ndiff'):
    """compares the two notebooks files using either an external program or displaying the difference in the notebook.

    :param nb1: file name of the first notebook
    :param nb2: file name of the second notebook
    :param external_diff_command: full path of the diff program
    :param use_html: if true (and not using external_diff_command), returns the diff as HTML (intended for jupyter notebook display)
    :return: either the text representation of the difference, or call a program to display it.
    """
    nb1_code = cells_to_code(nb_file_to_cells(nb1))
    nb2_code = cells_to_code(nb_file_to_cells(nb2))
    if external_diff_command is not None:
        diff_strings_external(nb1_code, nb2_code, external_diff_command, pre_args=external_diff_args)
    elif use_html:
        return diff_strings_pygment(nb1_code, nb2_code, typ=typ)
    else:
        assert difflib is not None, 'Please install the difflib package to used this function with use_html=False'
        assert typ in DIFFLIB_DIFFERENCE_TYPES, 'Unrecognized difference type. Allowed types are {}'.format(
            DIFFLIB_DIFFERENCE_TYPES)
        for l in getattr(difflib, typ)(nb1_code.split('\n'), nb2_code.split('\n')):
            print(l)


def validate_notebook_translation(nb1):
    """This converts nb1 code, converts it back to a notebook and checks that the two are equivalent, up to
    empty cells

    :param nb1: notebook to check
    :return: True if the conversion and back gave the same notebook
    """
    code = cells_to_code(nb_to_cells(nb1))
    nb2 = cells_to_notebook(split_code_to_cells(code))

    cells1 = nb1['cells']
    cells2 = nb2['cells']

    i = 0
    j = 0
    EOF = object()

    while True:
        if i >= len(cells1) or j >= len(cells2):
            break
        c1 = cells1[i] if i < len(cells1) else EOF
        c2 = cells2[j] if j < len(cells2) else EOF
        src1 = c1.source.strip()
        src2 = c2.source.strip()
        if len(src1) == 0:
            i += 1
            continue
        if len(src2) == 0:
            j += 1
            continue

        if src1 == src2:
            i += 1
            j += 1
            continue
        else:
            return False

    rem_cells1 = cells1[i:]
    rem_cells2 = cells2[j:]
    return True
