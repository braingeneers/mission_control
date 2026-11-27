"""Hoist local package imports of the given leaf modules to the top of a module; drop unused stdlib imports."""
import ast, re, sys
p, leaves = sys.argv[1], sys.argv[2].split(",")
s = open(p).read()
pat = re.compile(r'\n    from (\.[a-z_.]*) import ([a-z_0-9]+) as (_m_[a-z_0-9]+)  # Local import breaks orchestration cycle; patches stay on the defining module\.')
found = {}
def sub(m):
    full = (m.group(1) + "." + m.group(2)).replace("..", ".") if m.group(1) != "." else "." + m.group(2)
    name = m.group(2)
    if name in leaves:
        found[name] = (m.group(1), m.group(3)); return ""
    return m.group(0)
s = pat.sub(sub, s)
tree = ast.parse(s)
used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
lines = s.split("\n")
out, body_started = [], False
for i, ln in enumerate(lines):
    m = re.match(r'^import ([a-z_.]+)$', ln) or re.match(r'^from (datetime|pathlib) import (.+)$', ln)
    if m and not body_started:
        if ln.startswith("import "):
            if m.group(1).split(".")[0] not in used: continue
        else:
            names = [x.strip() for x in m.group(2).split(",") if x.strip() in used]
            if not names: continue
            ln = "from %s import %s" % (m.group(1), ", ".join(names))
    if ln.startswith("def ") or ln.startswith("class "): body_started = True
    out.append(ln)
s = "\n".join(out)
groups = {}
for name, (frm, alias) in sorted(found.items()):
    groups.setdefault(frm, []).append("%s as %s" % (name, alias))
imp = "".join("from %s import %s\n" % (frm, ", ".join(v)) for frm, v in sorted(groups.items()))
# insert after last top-level stdlib import
ls = s.split("\n"); k = max(i for i, l in enumerate(ls[:60]) if l.startswith("import ") or l.startswith("from ")) if any(l.startswith(("import ","from ")) for l in ls[:60]) else 1
ls.insert(k + 1, "\n" + imp.rstrip("\n"))
s = "\n".join(ls)
s = re.sub(r"\n{4,}", "\n\n\n", s)
open(p, "w").write(s)
print(p, "hoisted", sorted(found))
