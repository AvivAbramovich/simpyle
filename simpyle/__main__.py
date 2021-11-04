import sys
import ast

from simpyle import SimpyleExecutor


def add_local_variable(variable_raw: str):
    import simpyle.locals
    try:
        assign_index = variable_raw.index('=')
    except ValueError:
        raise ValueError(f'no "=" in variable "{variable_raw}"')

    name = variable_raw[:assign_index]
    value_raw = variable_raw[assign_index+1:]
    value = eval(value_raw)
    setattr(simpyle.locals, name, value)


if __name__ == '__main__':
    import argparse
    arg_parser = argparse.ArgumentParser(__package__)
    arg_parser.add_argument('script', type=argparse.FileType('r'))
    arg_parser.add_argument('--print-locals', action='store_true')
    arg_parser.add_argument('-l', nargs='+', help='local variable ( examples: a=5, b="hello", d={"a":[1,2,3]}} )')
    args = arg_parser.parse_args()

    code = args.script.read()
    t = ast.parse(code)

    for local_variable in args.l:
        add_local_variable(local_variable)

    e = SimpyleExecutor()
    e.execute(t)

    if args.print_locals:
        print(e.variables)
