import ast
import inspect
from types import ModuleType, SimpleNamespace
from typing import Optional, Dict, List
from enum import Enum


class SimpyleExecutor:
    ALLOWED_MODULES = [f'{__package__}.{m}' for m in ['locals', '_types', 'functions', 'exceptions']]

    class Ctx(Enum):
        Load = 1
        Store = 2

    class Return(BaseException):
        def __init__(self, value=None):
            self.value = value

    class Break(BaseException):
        pass

    def __init__(self):
        self.scope_stack: List[Dict] = []

    def execute(self, root: ast.Module, local_variables: Dict = None):
        self.scope_stack = [local_variables or {}]
        self.run_statement(root.body)

    def get_variable(self, key, throw=True):
        for scope in self.scope_stack:
            if key in scope:
                return scope[key]
        if throw:
            raise NameError(key)

    def set_variable(self, key, val):
        self.scope_stack[0][key] = val

    def _set_new_scope(self):
        self.scope_stack.insert(0, {})

    def _pop_scope(self):
        self.scope_stack.pop(0)

    def handle_constant(self, node: ast.Constant or ast.NameConstant):
        return node.value

    def handle_num(self, node: ast.Num):
        return node.n

    def handle_str(self, node: ast.Str):
        return node.s

    def handle_expr(self, node: ast.Expr):
        return self.run_statement(node.value)

    def handle_list(self, l: list):
        for stmt in l:
            self.run_statement(stmt)

    def handle_if(self, node: ast.If or ast.IfExp):
        if self.run_statement(node.test, self.Ctx.Load):
            return self.run_statement(node.body)
        elif node.orelse:
            return self.run_statement(node.orelse)

    def handle_call(self, node: ast.Call):
        f = self.run_statement(node.func, self.Ctx.Load)
        f_args = [self.run_statement(a, self.Ctx.Load) for a in node.args]
        return f(*f_args)

    def handle_name(self, node: ast.Name or str, ctx: Ctx=None):
        id = node.id if isinstance(node, ast.Name) else node
        if ctx == self.Ctx.Load:
            return self.get_variable(id)
        elif ctx == self.Ctx.Store:
            def store(val):
                self.set_variable(id, val)
            return store

    def handle_subscript(self, node: ast.Subscript, ctx: Ctx):
        value = self.run_statement(node.value, self.Ctx.Load)
        slice = self.run_statement(node.slice, self.Ctx.Load)
        if ctx == self.Ctx.Load:
            return value[slice]
        elif ctx == self.Ctx.Store:
            def store(_val):
                value[slice] = _val
            return store
        raise ValueError(ctx)

    def handle_attribute(self, node: ast.Attribute, ctx: Ctx):
        value = self.run_statement(node.value, self.Ctx.Load)
        if ctx == self.Ctx.Load:
            return getattr(value, node.attr)
        else:
            def store(_val):
                setattr(value, node.attr, _val)
            return store

    def handle_assign(self, node: ast.Assign):
        val = self.run_statement(node.value, self.Ctx.Load)
        target = node.targets[0]  # not supporting multiple variables assign
        store = self.run_statement(target, self.Ctx.Store)
        store(val)

    def handle_aug_assign(self, node: ast.AugAssign):
        val = self.run_statement(node.value, self.Ctx.Load)
        curr_val = self.run_statement(node.target, self.Ctx.Load)
        f = self.BIN_OP_MAP.get(type(node.op))
        if f is None:
            raise TypeError(type(node.op))
        res_val = f(val, curr_val)
        store = self.run_statement(node.target, self.Ctx.Store)
        store(res_val)

    def handle_unary_op(self, node: ast.UnaryOp, ctx: Ctx):
        if isinstance(node.op, ast.Not):
            return not self.run_statement(node.operand, ctx)
        else:
            raise TypeError(node.op)

    BIN_OP_MAP = {
        ast.Or: lambda a, b: a or b,
        ast.And: lambda a, b: a and b,
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b
    }

    def handle_binary_op(self, node: ast.BinOp or ast.BoolOp):
        values = node.values if type(node) == ast.BoolOp else [node.left, node.right]
        a, b = [self.run_statement(stmt, self.Ctx.Load) for stmt in values]
        op = getattr(node, 'op') or node.ops[0]
        f = self.BIN_OP_MAP.get(type(op))
        if f is None:
            raise TypeError(type(op))
        return f(a, b)

    COMPARE_OPERATIONS_MAP = {
        ast.Eq: lambda a, b: a == b,
        ast.NotEq: lambda a, b: a != b,
        ast.Is: lambda a, b: a is b,
        ast.IsNot: lambda a, b: a is not b,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
        ast.Lt: lambda a, b: a < b,
        ast.LtE: lambda a, b: a <= b,
        ast.Gt: lambda a, b: a > b,
        ast.GtE: lambda a, b: a <= b
    }

    def handle_compare(self, node: ast.Compare):
        left = self.run_statement(node.left, self.Ctx.Load)
        comparator = self.run_statement(node.comparators[0], self.Ctx.Load)
        op = node.ops[0]
        f = self.COMPARE_OPERATIONS_MAP.get(type(op))
        if f is None:
            raise TypeError(type(op))
        return f(left, comparator)

    def handle_dict(self, node: ast.Dict):
        return {
            self.run_statement(key, self.Ctx.Load): self.run_statement(val, self.Ctx.Load)
            for key, val in zip(node.keys, node.values)
        }

    def handle_joined_str(self, node: ast.JoinedStr):
        values = [str(self.run_statement(value, self.Ctx.Load)) for value in node.values]
        return ''.join(values)

    def handle_index(self, node: ast.Index or ast.FormattedValue):
        return self.run_statement(node.value, self.Ctx.Load)

    def handle_list_elements(self, node: ast.List):
        return [self.run_statement(elt, self.Ctx.Load) for elt in node.elts]

    def handle_list_comp(self, node: ast.ListComp or ast.GeneratorExp):
        res = []
        for generator in node.generators:
            for item in self.run_statement(generator, self.Ctx.Load):
                self.run_statement(generator.target, self.Ctx.Store)(item)
                res.append(self.run_statement(node.elt, self.Ctx.Load))
        return res

    def handle_comprehension(self, node: ast.comprehension, ctx: Ctx):
        return self.run_statement(node.iter, ctx)

    def handle_raise(self, node: ast.Raise):
        raise self.run_statement(node.exc)

    def handle_try(self, node: ast.Try, ctx: Ctx):
        try:
            res = self.run_statement(node.body, ctx)
        except Exception as e:
            for handler in node.handlers:
                if handler.type is None or \
                        isinstance(e, self.run_statement(handler.type, self.Ctx.Load)):
                    if handler.name:
                        self.run_statement(handler.name, self.Ctx.Store)(e)
                    res = self.run_statement(handler.body, ctx)
                    break
            else:
                raise e
        else:
            if node.orelse:
                _res = self.run_statement(node.orelse, ctx)
                if _res is not None:
                    # override return value
                    res = _res
        finally:
            if node.finalbody:
                _res = self.run_statement(node.finalbody, ctx)
                if _res is not None:
                    # override return value
                    res = _res
        return res

    def handle_import(self, node: ast.Import):
        for alias in node.names:
            self._import_modules(alias.name, alias)

    def handle_import_from(self, node: ast.ImportFrom):
        self._import_modules(node.module, *node.names)

    def handle_while(self, node: ast.While):
        while self.run_statement(node.test, self.Ctx.Load):
            res = self.run_statement(node.body)
            if res is not None:
                return res
        else:
            if node.orelse:
                return self.run_statement(node.orelse)

    def handle_for(self, node: ast.For):
        iter = self.run_statement(node.iter, self.Ctx.Load)
        store = self.run_statement(node.target, self.Ctx.Store)
        for i in iter:
            store(i)
            try:
                self.run_statement(node.body)
            except self.Break:
                break
        else:
            if node.orelse:
                return self.run_statement(node.orelse)

    def handle_break(self):
        raise SimpyleExecutor.Break()

    # TODO: scope
    def handle_function_def(self, node: ast.FunctionDef):
        def func(*args, **kwargs):
            self._set_new_scope()
            try:
                for arg_obj, arg_val in zip(node.args.args, args):
                    self.set_variable(arg_obj.arg, arg_val)
                self.run_statement(node.body)
            except self.Return as _return:
                return _return.value
            finally:
                self._pop_scope()
        self.set_variable(node.name, func)

    def handle_return(self, node: ast.Return):
        value = self.run_statement(node.value)
        raise self.Return(value)

    TYPES_MAP = {
        ast.Constant: handle_constant,
        ast.NameConstant: handle_constant,
        ast.Num: handle_num,
        ast.Str: handle_str,
        ast.Expr: handle_expr,
        ast.If: handle_if,
        ast.IfExp: handle_if,
        ast.Call: handle_call,
        ast.Name: handle_name,
        str: handle_name,
        list: handle_list,
        ast.Subscript: handle_subscript,
        ast.Attribute: handle_attribute,
        ast.Assign: handle_assign,
        ast.AugAssign: handle_aug_assign,
        ast.UnaryOp: handle_unary_op,
        ast.BinOp: handle_binary_op,
        ast.BoolOp: handle_binary_op,
        ast.Compare: handle_compare,
        ast.Dict: handle_dict,
        ast.JoinedStr: handle_joined_str,
        ast.FormattedValue: handle_index,
        ast.Index: handle_index,
        ast.List: handle_list_elements,
        ast.ListComp: handle_list_comp,
        ast.GeneratorExp: handle_list_comp,
        ast.comprehension: handle_comprehension,
        ast.Raise: handle_raise,
        ast.Try: handle_try,
        ast.Import: handle_import,
        ast.ImportFrom: handle_import_from,
        ast.While: handle_while,
        ast.For: handle_for,
        ast.Break: handle_break,
        ast.FunctionDef: handle_function_def,
        ast.Return: handle_return
    }

    def run_statement(self, node, ctx: Optional[Ctx] = None):
        f = self.TYPES_MAP.get(type(node))
        if f is None:
            raise Exception(f'Not supported ast node "{type(node)}"')

        args = [self, node, ctx]
        args = args[:len(inspect.signature(f).parameters)]
        return f(*args)

    def _import_modules(self, module_path: str, *aliases: ast.alias):
        if module_path in self.ALLOWED_MODULES:
            m = __import__(module_path)
            for alias in aliases:
                obj = self._import_name(m, module_path, alias.name)
                if isinstance(obj, ModuleType):
                    obj = self._module_to_ns(obj)
                self._add_import_to_variables(obj, alias.asname or alias.name)
        else:
            raise Exception(f'Not allowed module "{module_path}"')

    @staticmethod
    def _import_name(module, path, name):
        keys = path.split('.')[1:]
        if name != path:  # from a.b.c import d, so add 'd' to path
            keys.append(name)
        obj = module
        for key in keys:
            obj = getattr(obj, key)
        return obj

    def _add_import_to_variables(self, value, module_path):
        keys = module_path.split('.')
        if len(keys) == 1:
            self.set_variable(keys[0], value)
        else:
            root_key = keys[0]
            root_object = self.get_variable(root_key, throw=False) or SimpleNamespace()
            obj = root_object
            for key in keys[1:-1]:
                obj = getattr(obj, key)
            setattr(obj, keys[-1], value)
            self.set_variable(root_key, root_object)

    @staticmethod
    def _module_to_ns(obj: ModuleType):
        keys = [key for key in dir(obj) if not key.startswith('__')]
        return SimpleNamespace(**{k: getattr(obj, k) for k in keys})