'''py2math: convert python objects to latex math for use in ipython notebooks'''

import sys
import inspect
from lark import Token
from lark.lark import Lark
from lark.visitors import Interpreter
from lark.indenter import PythonIndenter


# import python grammar from lark
GRAMMAR = r'''
%import python (file_input, COMMENT)
%ignore /[\t \f]+/  // WS
%ignore /\\[\t \f]*\r?\n/   // LINE_CONT
%ignore COMMENT
'''


class py2math(sys.modules[__name__].__class__):
    parser_obj = None
    '''main class replacing the module, making the imported name callable'''

    @property
    def parser(self):
        if not self.parser_obj:
            self.parser_obj = Lark(GRAMMAR, postlex=PythonIndenter(), start='file_input')
        return self.parser_obj

    def __call__(self, obj):
        try:
            code = inspect.getsource(obj)
        except TypeError as err:
            # if `obj` isn't a function, class or similar object (which has code) print it directly
            return Math(str(obj))
        print(code)  # debug
        print(self.parser.parse(code).pretty())  # debug
        return Math(Converter().visit(self.parser.parse(code)))

class Math(object):
    def __init__(self, latex):
        self.latex = f'$$ {latex} $$'

    def _repr_latex_(self):
        print(self.latex)
        return self.latex


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
        name, parameters, test, suite = self.visit_children(tree)
        return f'{name}({", ".join(x for x in parameters if x)}) = {suite}'

    def python__paramvalue(self, tree):
        typedparam, test = self.visit_children(tree)
        # TODO: handle `test`, i.e. the default value of the parameter
        return typedparam

    def python__typedparam(self, tree):
        name, test = self.visit_children(tree)
        # TODO: handle `test`, i.e. the type of the parameter
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
        return ',\\ '.join(values)

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
            else:  # operator
                if x in '*/':
                    dividing = x == '/'
                else:
                    raise NotImplementedError(f'x')
        if len(dividend) > 1:
            # put brackets around non-trivial expressions (which are of type str)
            # TODO: maybe switch to x_obj for checking (from above loop)
            dividend = [(x if isinstance(x, Token) else f'({x})') for x in dividend]
        dividend_str = ' \\cdot '.join(dividend)
        if divisor:
            if len(divisor) > 1:
                divisor = [(x if isinstance(x, Token) else f'({x})') for x in divisor]
            divisor_str = ' \\cdot '.join(divisor)
            return f'\\frac{{{dividend_str}}}{{{divisor_str}}}'
        else:
            return dividend_str

    def python__arith_expr(self, tree):
        result = ''
        for i, (x, x_obj) in enumerate(zip(self.visit_children(tree), tree.children)):
            if i % 2 == 0:  # operand
                # put brackets around non-trivial expressions (which are of type str)
                # TODO: maybe switch to x_obj for checking
                # TODO: maybe too many brackets
                result += x if isinstance(x, Token) else f'({x})'
            else:  # operator
                result += x
        return result

    def python__var(self, tree):
        value, = tree.children
        return value

    def python__number(self, tree):
        value, = tree.children
        return value



# make module import callable
sys.modules[__name__].__class__ = py2math
