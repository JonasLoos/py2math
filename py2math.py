'''py2math: convert python objects to latex math for use in ipython notebooks

signature: `py2math(obj, debug : bool = False) -> Math`

where `obj` is the function or code object which should be converted to latex math
'''

import sys
import inspect
from lark import Token
from lark.lark import Lark
from lark.visitors import Interpreter
from lark.indenter import PythonIndenter


# import python grammar from lark
# https://github.com/lark-parser/lark/blob/master/lark/grammars/python.lark
GRAMMAR = r'''
%import python (file_input, COMMENT)
%ignore /[\t \f]+/  // WS
%ignore /\\[\t \f]*\r?\n/   // LINE_CONT
%ignore COMMENT
'''

parser = Lark(GRAMMAR, postlex=PythonIndenter(), start='file_input')


def py2math(obj, debug=False) -> 'Math':
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
            code = inspect.getsource(obj)
        except TypeError as err:
            # if `obj` isn't a function, class or similar object (which has code) print it directly
            return Math(str(obj))
        if debug:
            print(code)
            print(parser.parse(code).pretty())
        return Math(Converter().visit(parser.parse(code)))


class Math(str):
    '''Superclass of string which is printed as math in jupyter notebooks'''
    def _repr_latex_(self):
        return f'$$ {self} $$'


def bracketize(x):
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

    def python__expr_stmt(self, tree):
        idk, = self.visit_children(tree)
        return idk

    def python__funcdef(self, tree):
        name, parameters, return_type, suite = self.visit_children(tree)
        # TODO: handle return type
        return f'{name}({", ".join(x for x in parameters if x)}) = {suite}'

    def python__paramvalue(self, tree):
        typedparam, default_val = self.visit_children(tree)
        # TODO: handle the default value of the parameter
        return typedparam

    def python__typedparam(self, tree):
        name, param_type = self.visit_children(tree)
        # TODO: handle the type of the parameter
        return name

    def python__assign_stmt(self, tree):
        idk, = self.visit_children(tree)
        return idk

    def python__assign(self, tree):
        var, value = self.visit_children(tree)
        # TODO: convert lambda to normal function or add variable definition to "with" section
        return value

    def python__suite(self, tree):
        value, = self.visit_children(tree)
        return value

    def python__return_stmt(self, tree):
        value, = self.visit_children(tree)
        return value

    def python__test(self, tree):
        option_a, condition, option_b = self.visit_children(tree)
        return (
            '\n'
            '\\begin{cases}\n'
            f'  {option_a} & \\text{{if }} {condition} \\\\\n'
            f'  {option_b} & \\text{{otherwise}}\n'
            '\\end{cases}\n'
        )

    def python__funccall(self, tree):
        var, args = self.visit_children(tree)
        return f'{var}({args})'

    def python__arguments(self, tree):
        args = self.visit_children(tree)
        return ',\\ '.join(args)

    def python__argvalue(self, tree):
        argname, value = self.visit_children(tree)
        # TODO: handle argmane
        return value

    def python__lambdef(self, tree):
        idk, expr = self.visit_children(tree)
        return expr

    def python__testlist_tuple(self, tree):
        values = self.visit_children(tree)
        if len(values) == 1:
            # TODO: is this actually desired?
            return f'\\left({values[0]},\\right)'
        else:
            return '\\left(' + ',\\ '.join(values) + '\\right)'

    def python__tuple(self, tree):
        values = self.visit_children(tree)
        if len(values) == 1:
            return f'\\left({values[0]},\\right)'
        else:
            return '\\left(' + ',\\ '.join(values) + '\\right)'

    def python__set(self, tree):
        elements = self.visit_children(tree)
        # TODO: test star expressions
        return '\\left\\{' + ',\\ '.join(elements) + '\\right\\}'

    def python__term(self, tree):
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

    def python__arith_expr(self, tree):
        result = ''
        for i, (x, x_obj) in enumerate(zip(self.visit_children(tree), tree.children)):
            if i % 2 == 0:  # operand
                result += bracketize(x)
            else:  # operator: +, -
                result += x
        return result

    def python__power(self, tree):
        base, exponent = self.visit_children(tree)
        return f'{{{bracketize(base)}}}^{{{exponent}}}'

    def python__shift_expr(self, tree):
        # TODO
        return '[shift_expr]'

    def python__comparison(self, tree):
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

    def python__var(self, tree):
        value, = tree.children
        return value

    def python__number(self, tree):
        value, = tree.children
        return value

    def python__string(self, tree):
        value, = tree.children
        return f'\\text{{{value}}}'
