from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FunctionElement


class coalesce(FunctionElement):
    name = 'coalesce'


@compiles(coalesce, 'postgresql')
def compile(element, compiler, **kw):
    return "coalesce(%s)" % compiler.process(element.clauses)
