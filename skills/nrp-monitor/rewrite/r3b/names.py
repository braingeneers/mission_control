import ast, builtins, sys
for p in sys.argv[1:]:
    tree = ast.parse(open(p).read())
    g = set(dir(builtins))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)): g.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names: g.add((a.asname or a.name).split('.')[0])
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store): g.add(node.id)
        elif isinstance(node, ast.arg): g.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name: g.add(node.name)
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    miss = used - g
    imported = set()
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names: imported.add((a.asname or a.name).split('.')[0])
    unused = {i for i in imported if i not in used and not any(isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == i for n in ast.walk(tree))}
    if miss or unused: print(p, "UNDEFINED:", sorted(miss), "UNUSED-TOP:", sorted(unused))
