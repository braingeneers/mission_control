import ast, sys, pathlib
root = pathlib.Path(sys.argv[1]); edges = {}
for p in root.rglob("*.py"):
    mod = ".".join(p.relative_to(root).with_suffix("").parts)
    pkg = mod.rsplit(".", 1)[0] if "." in mod else ""
    for node in ast.parse(p.read_text()).body:
        if isinstance(node, ast.ImportFrom) and node.level:
            base = pkg if node.level == 2 or "." in mod and node.level == 1 and False else ""
            base = ("task" if mod.startswith("task.") and node.level == 1 else "")
            m = ((base + "." if base else "") + (node.module or "")).strip(".")
            for a in node.names:
                edges.setdefault(mod, set()).add((m + "." if m else "") + a.name)
def cyc(n, stack, seen):
    if n in stack: print("CYCLE", " -> ".join(stack[stack.index(n):] + [n])); return True
    if n in seen: return False
    seen.add(n)
    return any(cyc(m, stack + [n], seen) for m in edges.get(n, ()))
seen=set(); print("cycles:", any(cyc(n, [], seen) for n in list(edges))); print({k: sorted(v) for k, v in edges.items()})
