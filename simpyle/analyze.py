import ast
import sys


if __name__ == '__main__':
    import argparse
    arg_parser = argparse.ArgumentParser(__package__)
    arg_parser.add_argument('script', type=argparse.FileType('r'))
    arg_parser.add_argument('--indent', type=int, default=4, help='supported in python3.9+')
    arg_parser.add_argument('--print-locals', action='store_true')
    arg_parser.add_argument('-p', help='path inside AST', default=None)
    arg_parser.add_argument('-l', nargs='+', help='local variable ( examples: a=5, b="hello", d={"a":[1,2,3]}} )')
    args = arg_parser.parse_args()

    code = args.script.read()
    nodes = [ast.parse(code)]

    if args.p:
        attributes = args.p.split('.')
        for attr in attributes:
            new_nodes = []
            for node in nodes:
                tmp = getattr(node, attr, None)
                if isinstance(tmp, list):
                    new_nodes += tmp
                elif tmp is not None:
                    new_nodes.append(tmp)
            nodes = new_nodes

    kwargs = {}
    if sys.version_info.major == 3 and sys.version_info.minor >= 9:
        kwargs['indent'] = args.indent

    for node in nodes:
        print(ast.dump(node, **kwargs))
