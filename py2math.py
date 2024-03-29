'''py2math: Convert Python objects to Latex math for use in jupyter notebooks.'''

import inspect
from lark.lexer import Token
from lark.lark import Lark
from lark.visitors import Interpreter
from lark.indenter import PythonIndenter


# import python grammar from lark
# https://github.com/lark-parser/lark/blob/master/lark/grammars/python.lark
parser = Lark.open_from_package(
    'lark',
    'python.lark',
    ['grammars'],
    parser='lalr',
    postlex=PythonIndenter(),
    start='file_input'
)


def py2math(obj, debug=False) -> 'Math':
    """Convert Python objects to Latex math e.g. for use in jupyter notebooks

    Args:
        obj (Any): function or code object which should be converted to latex math.
        debug (bool, optional): Whether to print debug info. Defaults to False.

    Returns:
        Math: The resulting latex math, as a subclass of `str`, which is displayed as math in jupyter notebooks.
    """
    if isinstance(obj, (list, tuple, set)):
        # parse nested code
        b1, b2 = {
            list: '[]',
            tuple: '()',
            set: '{}'
        }[type(obj)]
        # TODO: maybe add `,` in one-element tuples
        return Math(f'\\left{b1}' + ', '.join(py2math(x, debug=debug) for x in obj) + f'\\right{b2}')
    elif obj == ...:
        # convert Ellipses to dots
        return Math('...')
    else:
        try:
            # try to get the source code for the given object
            code = inspect.getsource(obj)
        except TypeError as err:
            # if `obj` isn't a function, class or similar object (which has code) print it directly
            return Math(str(obj))
        if debug: print('"' + code + '"')
        parse_tree = parser.parse(code)
        if debug: print(parse_tree.pretty())
        result = Math(Converter().visit(parser.parse(code)))
        if debug: print(result._repr_latex_())
        return result


class Math(str):
    '''Superclass of string which is printed as math in jupyter notebooks'''
    def _repr_latex_(self):
        return f'$$ {self} $$'


def bracketize(x : 'Token | str') -> 'Token | str':
    '''put brackets around non-trivial expressions (which are not of type str)'''
    # TODO: check if `isinstance(x, Token)` is reliable, or if elements of obj.children should be used here
    # TODO: maybe too many brackets
    return x if isinstance(x, Token) else f'\\left({x}\\right)'


class Converter(Interpreter):

    def file_input(self, tree):
        idk, = self.visit_children(tree)
        return idk

    def eval_input(self, tree):
        # TODO: maybe remove, if e.g. file_input is made the default
        idk, = self.visit_children(tree)
        return idk

    def expr_stmt(self, tree):
        idk, = self.visit_children(tree)
        return idk

    def funcdef(self, tree):
        name, parameters, return_type, suite = self.visit_children(tree)
        # TODO: handle return type
        return f'{name}({", ".join(x for x in parameters if x)}) = {suite}'

    def paramvalue(self, tree):
        typedparam, default_val = self.visit_children(tree)
        # TODO: handle the default value of the parameter
        return typedparam

    def typedparam(self, tree):
        name, param_type = self.visit_children(tree)
        # TODO: handle the type of the parameter
        return name

    def assign_stmt(self, tree):
        idk, = self.visit_children(tree)
        return idk

    def assign(self, tree):
        name, value = self.visit_children(tree)
        # TODO: convert lambda to normal function or add variable definition to "with" section
        return f'{name} = {value}'

    def suite(self, tree):
        lines = self.visit_children(tree)
        assert tree.children[-1].data == 'return_stmt', f'the last statement has to be a return, not `{tree.children[-1].data}`'
        assert all(x.data == 'assign_stmt' for x in tree.children[:-1]), f'only assignments are supported before the return, but got {[f"{x.data}" for x in tree.children[:-1]]}'
        # TODO: extend translation capabilities and remove above constraint
        if len(lines) == 1:
            return lines[0]
        else:
            return (
                lines[-1] +
                '\\\\\n\\text{where}\\\\\n' +
                '\\\\\n'.join(lines[:-1])
            )

    def return_stmt(self, tree):
        value, = self.visit_children(tree)
        return value

    def test(self, tree):
        option_a, condition, option_b = self.visit_children(tree)
        return (
            '\n'
            '\\begin{cases}\n'
            f'  {option_a} & \\text{{if }} {condition} \\\\\n'
            f'  {option_b} & \\text{{otherwise}}\n'
            '\\end{cases}\n'
        )

    def funccall(self, tree):
        var, args = self.visit_children(tree)
        return f'{var}({args})'

    def arguments(self, tree):
        args = self.visit_children(tree)
        return ',\\ '.join(args)

    def argvalue(self, tree):
        argname, value = self.visit_children(tree)
        # TODO: handle argmane
        return value

    def lambdef(self, tree):
        params, expr = self.visit_children(tree)
        ps = ",\\ ".join(filter(lambda x:x, params))
        return f'({ps}) \\rightarrow {expr}'

    def testlist_tuple(self, tree):
        values = self.visit_children(tree)
        if len(values) == 1:
            # TODO: is this actually desired?
            return f'\\left({values[0]},\\right)'
        else:
            return '\\left(' + ',\\ '.join(values) + '\\right)'

    def tuple(self, tree):
        values = self.visit_children(tree)
        if len(values) == 1:
            return f'\\left({values[0]},\\right)'
        else:
            return '\\left(' + ',\\ '.join(values) + '\\right)'

    def set(self, tree):
        elements = self.visit_children(tree)
        # TODO: test star expressions
        return '\\left\\{' + ',\\ '.join(elements) + '\\right\\}'

    def term(self, tree):
        dividend = []
        divisor = []
        dividing = False
        for i, (x, x_obj) in enumerate(zip(self.visit_children(tree), tree.children)):
            if i % 2 == 0:  # operand
                if dividing:
                    divisor += [x]
                else:
                    dividend += [x]
            else:  # operator: *, /, @, %, //
                if x in '*/':
                    dividing = x == '/'
                else:
                    # TODO: implement other operators
                    raise NotImplementedError(f'{x}')
        if len(dividend) > 1:
            dividend = [(bracketize(x)) for x in dividend]
        dividend_str = ' \\cdot '.join(dividend)
        if divisor:
            if len(divisor) > 1:
                divisor = [(bracketize(x)) for x in divisor]
            # TODO: use `\\cdot` or `\\times`?
            #   `\\cdot` might clash with matrix multiplication, but `\\times` might be visually disturbing
            divisor_str = ' \\cdot '.join(divisor)
            return f'\\frac{{{dividend_str}}}{{{divisor_str}}}'
        else:
            return dividend_str

    def arith_expr(self, tree):
        result = ''
        for i, (x, x_obj) in enumerate(zip(self.visit_children(tree), tree.children)):
            if i % 2 == 0:  # operand
                result += bracketize(x)
            else:  # operator: +, -
                result += x
        return result

    def power(self, tree):
        base, exponent = self.visit_children(tree)
        return f'{{{bracketize(base)}}}^{{{exponent}}}'

    def shift_expr(self, tree):
        # TODO
        return '[shift_expr]'

    def comparison(self, tree):
        result = ''
        for i, (x, x_obj) in enumerate(zip(self.visit_children(tree), tree.children)):
            if i % 2 == 0:  # operand
                result += bracketize(x)
            else:  # operator: <, >, ==, >=, <=, <>, !=, in, not in, is, is not
                result += {
                    '<': ' < ',
                    '>': ' > ',
                    '==': ' = ',
                    '>=': ' \\geq ',
                    '<=': ' \\leq ',
                    # '<>': '',  # not really valid, see PEP 401
                    '!=': ' \\neq ',
                    'in': ' \\in ',
                    'not in': ' \\notin ',
                    'is': ' \\equiv ',
                    'is not': ' \\not\\equiv ',
                }[' '.join(x)]
        return result

    def ellipsis(self, tree):
        return '...'

    def var(self, tree):
        value, = tree.children
        return value

    def number(self, tree):
        value, = tree.children
        return value

    def string(self, tree):
        value, = tree.children
        return f'\\text{{{value}}}'
