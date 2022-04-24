'''py2math: convert python objects to latex math'''

import sys
import inspect
from lark.lark import Lark
from lark.visitors import Interpreter
from lark.indenter import PythonIndenter


grammar = r'''
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
            self.parser_obj = Lark(grammar, postlex=PythonIndenter(), start='file_input')
        return self.parser_obj

    def __call__(self, obj):
        code = inspect.getsource(obj)
        print(code)
        print(self.parser.parse(code).pretty())
        c = Converter()
        
        return Math(c.visit(self.parser.parse(code)))

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
        idk, = self.visit_children(tree)
        return idk

    def python__expr_stmt(self, tree):
        idk, = self.visit_children(tree)
        return idk

    def python__funcdef(self, tree):
        name, parameters, test, suite = self.visit_children(tree)
        return f'{name}({", ".join(x for x in parameters if x)}) = {suite}'

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
        idk, = self.visit_children(tree)
        return idk

    def python__lambdef(self, tree):
        idk, expr = self.visit_children(tree)
        return expr

    def python__testlist_tuple(self, tree):
        values = self.visit_children(tree)
        return f'({", ".join(values)})'

    def python__term(self, tree):
        a, value, b = self.visit_children(tree)
        # if value == '*':
        #     value = r'\cdot'  # `\` doesn't work yet, as it gets duplicated
        return a + value + b

    def python__var(self, tree):
        value, = tree.children
        return value

    def python__number(self, tree):
        value, = tree.children
        return value

    def python__arith_expr(self, tree):
        a, value, b = self.visit_children(tree)
        return a + value + b




sys.modules[__name__].__class__ = py2math  # make module import callable
