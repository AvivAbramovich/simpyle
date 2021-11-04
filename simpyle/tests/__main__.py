import sys
import ast

from simpyle import SimpyleExecutor
import simpyle.locals


def import_test(test_module_content):
    l = {}
    exec(test_module_content, {}, l)
    return l['tests']


if __name__ == '__main__':
    import argparse
    arg_parser = argparse.ArgumentParser(__package__)
    arg_parser.add_argument('script', type=argparse.FileType('r'))
    arg_parser.add_argument('test', type=argparse.FileType('r'))
    arg_parser.add_argument('--indent', type=int, default=4, help='supported in python3.9+')
    arg_parser.add_argument('--print-ast', action='store_true')
    args = arg_parser.parse_args()

    code = args.script.read()
    t = ast.parse(code)

    if args.print_ast:
        kwargs = {}
        if sys.version_info.major == 3 and sys.version_info.minor >= 9:
            kwargs['indent'] = args.indent
        print(ast.dump(t, **kwargs))

    tests = import_test(args.test.read())
    print(f'run {len(tests)} test(s):')
    for i, test in enumerate(tests, 1):
        print(f'test {i}:')
        v = {'fv': test.src_fv, 'alert': test.alert}
        simpyle.locals.fv = test.src_fv
        simpyle.locals.alert = test.alert
        print(f'before script: fv={test.src_fv}, alert={test.alert}')
        # v.update(add_supported_variables())
        print(f'expected result: fv={test.dst_fv}')
        SimpyleExecutor().execute(t, v)
        # remove_functions(v)
        print(f'after script: fv={v["fv"]}')
        assert v['fv'] == test.dst_fv
