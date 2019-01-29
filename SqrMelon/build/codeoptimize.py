import re

# text parser statemachine states
gOPEN = 0
gMACRO = 1
gLINE = 2
gBLOCK = 3


def previewCode(programStitchIds, stitches):
    shaderCode = []
    for i in range(len(programStitchIds)):
        shaderCode.append(stitches[programStitchIds[i]])
    return ''.join(shaderCode)


def _findUnusedFunctions(frameBuffer, stitches):
    flatCode = previewCode(frameBuffer, stitches)

    # find words and usage count
    words = {}
    for match in re.finditer(r'\w+', flatCode):
        word = match.group()
        if word in words:
            words[word] += 1
        else:
            words[word] = 1

    # find unused top level blocks (functions & structs)
    blocks = []
    depth = 0
    state = gOPEN
    start = None
    for i in range(len(flatCode)):
        if state == gOPEN:
            if flatCode[i:i + 7] == '#define':
                start = i
                state = gMACRO
                continue
            if flatCode[i] == '{':
                if depth == 0:
                    start = i
                depth += 1
                continue
            elif flatCode[i] == '}':
                depth -= 1
                if depth == 0:
                    blocks.append((start, i + 1))
                continue
        elif state == gMACRO:
            if flatCode[i] == '\n' and flatCode[i - 1] != '\\':
                state = gOPEN
                continue

    state = gOPEN
    for start, end in blocks:
        cursor = start
        name = None
        for i in range(start - 1, -1, -1):
            if state == gOPEN:
                if flatCode[i] == ')':
                    state = gBLOCK
                    continue
                elif not re.match('\w', flatCode[i]):
                    if name is None:
                        name = flatCode[i + 1:cursor]
                        if name == 'main':
                            name = None
                            break
                    else:
                        cursor = i + 1
                        break
            elif state == gBLOCK:
                if flatCode[i] == '(':
                    state = gOPEN
                    cursor = i
                    continue
        if name is not None and words[name] == 1:
            yield name, flatCode[cursor:end]


def removeUnusedFunctions(stack, stitches):
    # for each framebuffer identify unused functions
    # functions not used by any framebuffer can be removed
    unusedSet = None
    functionBodies = {}
    for entry in stack:
        unused = set()
        for name, body in _findUnusedFunctions(entry, stitches):
            functionBodies[name] = body
            unused.add(name)
        if unusedSet is None:
            unusedSet = unused
        else:
            unusedSet &= unused

    # now removed the unused functions remaining
    for name in unusedSet:
        for i, entry in enumerate(stitches):
            stitches[i] = entry.replace(functionBodies[name], '')
    return stitches


def _unifyLineBreaks(text):
    # remove windows newlines
    return text.replace('\r', '\n')


def _stripLines(text):
    # remove trailing and leading whitespace
    text = re.sub('^[ \t]', '', text, re.MULTILINE)
    return re.sub('[ \t]$', '', text, re.MULTILINE)


def _stripWhitespace(text):
    text = text.strip('\n')

    # remove indentation to make macro & newline matching easier
    text = re.sub(r'[ \t]*([\n])[ \t]*', r'\1', text)
    # because the newline removal doesnt remove the first newline after an else, make sure we pre-emptively remove those when unnecessary (directly followed by a {)
    text = re.sub(r'(else)\n+({)', r'\1\2', text)

    text = text.strip('\n')

    # remove newlines apart from the ones at macros or after else statements
    strip = []
    state = gOPEN
    for i in range(len(text)):
        if state == gOPEN:
            if text[i:i + 7] == '#define' or text[i:i + 8] == '#version' or text[i:i + 6] == '#ifdef' or text[i:i + 3] == '#if' or text[i:i + 5] == '#else' or text[i:i + 6] == '#endif' or text[i:i + 6] == '#undef':
                state = gMACRO
                continue
            elif text[i:i + 4] == 'else':
                state = gBLOCK
                continue
            elif text[i] == '\n' and text[i + 1] != '#':
                strip.append((i, i + 1))
        elif state == gMACRO:
            if text[i] == '\n' and text[i - 1] != '\\':
                state = gOPEN
                continue
        elif state == gBLOCK:
            if text[i] == '{' or text[i] == '\n' and text[i - 1] != '\\':
                state = gOPEN
                continue

    for i in range(len(strip) - 1, -1, -1):
        text = text[:strip[i][0]] + text[strip[i][1]:]

    # flatten multiple newlines
    text = re.sub('\n+', '\n', text)

    # remove redundant spaces and tabs around operators and newlines
    text = re.sub(r'[ \t]*([=+\-*/<>{},;])[ \t]*', r'\1', text)
    # TODO: removing spaces around groups breaks macros that start with a ( but do not have arguments like #define TAU (PI+PI) --> #define TAU(PI+PI) suddently has an arglist instead of a meaning
    # text = re.sub(r'[ \t]*([=+\-*/<>{}\(\),;])[ \t]*', r'\1', text)

    # substitute tabs for spaces
    text = re.sub('\t', ' ', text)

    # remove multiple spaces (to catch eg. "struct   Test")
    text = re.sub(' +', ' ', text)

    return text


def _stripComments(text):
    assert '\r' not in text, 'Comment removal relies on escaped newlines and does not support windows-style line breaks. Please use _unifyLineBreaks() first.'

    # strip comments
    strip = []
    start = 0
    state = gOPEN
    for i in range(len(text)):
        if state == gOPEN:
            if text[i:i + 2] == '/*':
                start = i
                state = gBLOCK
                continue
            if text[i:i + 2] == '//':
                start = i
                state = gLINE
                continue
            if text[i:i + 7] == '#define':
                start = i
                state = gMACRO
                continue
        elif state == gMACRO:
            if text[i] == '\n' and text[i - 1] != '\\':
                state = gOPEN
                continue
        elif state == gLINE:
            if text[i] == '\n':
                strip.append((start, i))
                state = gOPEN
                continue
        elif state == gBLOCK:
            if text[i:i + 2] == '*/':
                strip.append((start, i + 2))
                state = gOPEN
                continue

    for i in range(len(strip) - 1, -1, -1):
        text = text[:strip[i][0]] + text[strip[i][1]:]

    return text


def _truncateFloats(text):
    # TODO: instead of boldly truncating all numbers we have to look at function usage, certain overloads like clamp(i,f,f) don't exist. Hence we should figure out what function call & what parameter index the float is and match it against an "exclusion" map
    replace = []
    n = len(text)
    i = 0
    while i < n:
        if re.match('[a-zA-Z0-9_+-]', text[i]):
            i += 1
            continue
        match = re.match(r'[+-]?([0-9]+)\.?([0-9]*)([eE][-+]?[0-9]+)?', text[i + 1:])
        if not match:
            i += 1
            continue
        i += 1
        if float(match.group()) == 0:
            replace.append((i + match.start(), i + match.end(), '0'))
        elif match.group(2) and float(match.group(2)) == 0:
            replace.append((i + match.start(2) - 1, i + match.end(2), ''))
        elif match.group(1) and int(match.group(1)) == 0:
            replace.append((i + match.start(1), i + match.end(1), ''))
        i += match.end()

    for start, end, txt in reversed(replace):
        text = text[:start] + txt + text[end:]

    return text


def optimizeText(text):
    # remove windows newlines
    text = _unifyLineBreaks(text)
    # strip comments
    text = _stripComments(text)
    # remove trailing and leading whitespace
    text = _stripLines(text)
    # remove whitespace
    text = _stripWhitespace(text)
    # truncate numbers
    # text = _truncateFloats(text)
    return text.strip()


def optimizeCode(programStitchIds, stitches):
    for i, text in enumerate(stitches):
        # remove windows newlines
        text = _unifyLineBreaks(text)
        # strip comments
        text = _stripComments(text)
        # remove trailing and leading whitespace
        text = _stripLines(text)
        # remove whitespace
        text = _stripWhitespace(text)
        # truncate numbers
        text = _truncateFloats(text)
        stitches[i] = text.strip()

    return removeUnusedFunctions(programStitchIds, stitches)
