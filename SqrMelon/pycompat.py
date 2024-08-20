def execfile(path, globals=None, locals=None):
    exec(open(path).read(), globals or {}, locals or {})
