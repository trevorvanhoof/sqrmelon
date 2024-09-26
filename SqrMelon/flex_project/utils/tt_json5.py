from typing import *

JSON5_OBJECT_SUPPORT_IDENTIFIER_NAMES_KEYS = True  # Can nto implement correctly, matches any character until whitespace or : instead.
JSON5_OBJECT_SUPPORT_TRAILING_COMMA = True

JSON5_ARRAY_SUPPORT_TRAILING_COMMA = True

JSON5_STRING_SUPPORT_SINGLE_QUOTES = True  # Strings can be ' or ", must match the same closign quote, quote escapes are only valid for that quote.
JSON5_STRING_SUPPORT_ESCAPE_LINE_BREAKS = True  # Strings can contain a \ before a line break to ignore said line break.
JSON5_STRING_SUPPORT_HEX = True  # Strings can support \x escape codes instead of only \u escape codes.
JSON5_STRING_SUPPORT_CHARACTER_ESCAPES = True  # \ escapes the next character if it is not an escape code, as opposed to a small subset of legal characters.

JSON5_NUMBER_SUPPORT_HEX = True  # Support 0x0aF numbers with optional sign.
JSON5_NUMBER_SUPPPORT_FREE_DECIMAL = True  # .0 and 0. become valid floats.
JSON5_NUMBER_SUPPORT_INF_AND_NAN = True  # Keywords are: Infinity, -Infinity, +Infinity, NaN, case sensitive.
JSON5_NUMBER_SUPPORT_PLUS_SIGN = True  # Support optional + sign as well.

JSON5_SUPPORT_SINGLE_LINE_COMMENTS = True  # Support C-style // comments.
JSON5_SUPPORT_BLOCK_COMMENTS = True  # Support C-style */ comments.

JSON5_SUPPORT_MORE_WHITESPACE = False  # Not implemented yet, needs test cases to see where this is relevant. In my implementation this also relates to where comments may occur.

JsonValue = Optional[Union['JsonValue', int, float, str, bool, List['JsonValue'], Dict[str, 'JsonValue']]]


class AStream:
    def read(self, numBytes: int = 1) -> bytes:
        raise NotImplementedError

    def rewind(self, numBytes: int = 1) -> None:
        raise NotImplementedError

    def save(self) -> None:
        raise NotImplementedError

    def load(self) -> None:
        raise NotImplementedError

    def pop(self) -> None:
        raise NotImplementedError

    def err(self, msg: str = '') -> str:
        raise NotImplementedError


class ParseError(Exception):
    pass


class SStream(AStream):
    def __init__(self, text: bytes):
        self.__text: bytes = text
        self.__cursor: int = 0
        self.__stack = []

    def read(self, numBytes: int = 1) -> bytes:
        if numBytes == 1 and self.__cursor == len(self.__text):
            return b''
        result = self.__text[self.__cursor:self.__cursor + numBytes]
        if len(result) != numBytes:
            raise IOError
        self.__cursor += numBytes
        return result

    def rewind(self, numBytes: int = 1) -> None:
        self.__cursor -= numBytes

    def save(self) -> None:
        self.__stack.append(self.__cursor)

    def load(self) -> None:
        self.__cursor = self.__stack.pop(-1)

    def pop(self) -> None:
        self.__stack.pop(-1)

    def err(self, msg: str = '') -> str:
        c = self.__cursor - self.__text.rfind(b'\n', 0, self.__cursor)
        ln = self.__text.count(b'\n', 0, self.__cursor) + 1
        return f"{{'at': {self.__cursor}, 'lineNumber': {ln}, 'columnNumber': {c}, 'message': \"{msg}\"}}"


def parseComment(stream: AStream, b: bytes) -> bytes:
    if b != b'/' or not JSON5_SUPPORT_BLOCK_COMMENTS and not JSON5_SUPPORT_SINGLE_LINE_COMMENTS:
        return b
    b = stream.read()
    block = False
    if JSON5_SUPPORT_SINGLE_LINE_COMMENTS and b == b'/':
        search = b'\r\n'
    elif JSON5_SUPPORT_BLOCK_COMMENTS and b == b'*':
        search = b'*'
        block = True
    else:
        stream.rewind()
        return b
    # We are in a comment, process it before parsing more whitespace.
    b = stream.read()
    escape = False
    while True:
        if escape:
            escape = False
        else:
            if b == b'':
                if not block:
                    return b
                raise ParseError(stream.err())
            elif b == b'\\':
                escape = True
            elif b in search:
                # Close block comment edge case.
                if block:
                    b = stream.read()
                    if b == b'/':
                        break
                    else:
                        continue
                break
        b = stream.read()
    b = stream.read()
    return b


def parseWhitespace(stream: AStream) -> None:
    b = stream.read()

    # Skip past comments
    b = parseComment(stream, b)

    # TODO: Include U+2028 and U+2029 here as well
    """
    Spec actually says all of these need to be included:

    U+0009	Horizontal tab
    U+000A	Line feed
    U+000B	Vertical tab
    U+000C	Form feed
    U+000D	Carriage return
    U+0020	Space
    U+00A0	Non-breaking space
    U+2028	Line separator
    U+2029	Paragraph separator
    U+FEFF	Byte order mark
    Unicode Zs category	Any other character in the Space Separator Unicode category
    """
    while b != b'' and b in b' \r\n\x0c':
        b = stream.read()
        # Skip past comments
        b = parseComment(stream, b)
    if b != b'':  # EOF
        stream.rewind()


def parseNumber(stream: AStream) -> Union[int, float]:
    if JSON5_NUMBER_SUPPORT_INF_AND_NAN:
        value, success = tryParse(stream, parseNaN)
        if success:
            return float('nan')

    b = stream.read()

    negative = b == b'-'
    if negative:
        b = stream.read()
    elif b == b'+' and JSON5_NUMBER_SUPPORT_PLUS_SIGN:
        b = stream.read()

    if JSON5_NUMBER_SUPPORT_INF_AND_NAN:
        stream.rewind()
        value, success = tryParse(stream, parseInfinity)
        if success:
            if negative:
                return -float('inf')
            return float('inf')
        b = stream.read()

    if JSON5_NUMBER_SUPPORT_HEX:
        if b == b'0':
            tmp = stream.read()
            if tmp not in b'xX':
                stream.rewind()
            else:
                h = b''
                while True:
                    try:
                        h += readHex(stream, 1)
                    except ParseError:
                        stream.rewind()
                        break
                if not h:
                    raise ParseError(stream.err())
                return int(h, 16)

    head = b''
    tail = b''
    exponent = b''
    exponentNegative = False

    mode = 0
    while True:
        if mode == 0:  # After sign
            # We can find 1 optional 1-9, or a 0
            if b in b'123456789':
                mode = 1
                head += b
            elif b == b'0':
                mode = 2
                head += b
            else:
                if JSON5_NUMBER_SUPPPORT_FREE_DECIMAL:
                    mode = 2
                    continue
                else:
                    raise SyntaxError(stream.err())
        elif mode == 1:  # After optional 1-9
            # We can find more optional digits, or move on
            if b in b'0123456789':
                head += b
            else:
                mode = 2
                continue
        elif mode == 2:  # After head
            # We can find an optional dot, or move on
            if b == b'.':
                mode = 3
            else:
                # End of number
                if not head:
                    raise SyntaxError(stream.err())
                mode = 4
                continue
        elif mode == 3:  # After .
            # We can find 1 or more digits, or move on
            if b in b'0123456789':
                tail += b
            else:
                if not tail and not JSON5_NUMBER_SUPPPORT_FREE_DECIMAL:
                    raise ParseError(stream.err())
                mode = 4
                continue
        elif mode == 4:  # After number
            # We can find an exponent, or we are done
            if b in b'eE':
                mode = 5
            else:
                break
        elif mode == 5:  # After eE
            # We can find an optional sign, and move on
            if b in b'+-':
                exponentNegative = b == b'-'
                b = stream.read()
            mode = 6
            continue
        elif mode == 6:  # After eE+-
            # We can find 1 or more digits, or move on
            if b == b'.':
                raise ParseError(stream.err())
            if b in b'0123456789':
                exponent += b
            else:
                if not exponent:
                    raise ParseError(stream.err())
                mode = 7
                break

        # Get next byte
        b = stream.read()
        if b == b'':  # EOF
            break

    stream.rewind()

    if not JSON5_NUMBER_SUPPPORT_FREE_DECIMAL:
        if not head or (mode == 3 and not tail) or (mode == 6 and not exponent):
            raise ParseError(stream.err())
    else:
        if (not head and not tail) or (mode == 6 and not exponent):
            raise ParseError(stream.err())

    if negative:
        head = b'-' + head
    if tail:
        head += b'.'
        head += tail
    if exponent:
        head += b'e'
        if exponentNegative:
            head += b'-'
        head += exponent
    if not tail and not exponent and mode != 3:
        return int(head.decode('utf8'))
    return float(head.decode('utf8'))


QUOTES = b'"\'' if JSON5_STRING_SUPPORT_SINGLE_QUOTES else b'"'


def readHex(stream: AStream, count: int) -> bytes:
    h = stream.read(count)
    if len(h) != count:
        raise ParseError(stream.err())
    for character in h:
        if character not in b'0123456789abcdefABCDEF':
            raise ParseError(stream.err())
    return h


def parseHex(stream: AStream, count: int) -> int:
    h = readHex(stream, count)
    return int(h, 16)


def parseHexInString(stream: AStream) -> bytearray:
    r = bytearray()
    r.append(parseHex(stream, 2))
    while True:
        a = stream.read()
        b = stream.read()
        if a + b == b'\\x':
            r.append(parseHex(stream, 2))
        else:
            if b:
                stream.rewind()
            if a:
                stream.rewind()
            break
    return r


def parseKey(stream: AStream) -> str:
    return parseString(stream, True)


def parseString(stream: AStream, isKey: bool = False) -> str:
    b = stream.read()
    q = b
    r = b''
    if b not in QUOTES:
        if isKey and JSON5_OBJECT_SUPPORT_IDENTIFIER_NAMES_KEYS:
            # As part of json5 support, we must match valid ECMAScript5.1 identifiers
            # These kinda follow this regex for the first char:
            # re.compile(r'\$|_|\w|\\u[0-9a-fA-F]{4}', re.UNICODE)
            # And for the rest of the chars:
            # re.compile(r'\$|_|\w|\\u[0-9a-fA-F]{4}|\d|_＿﹍-﹏︳︴ ‿ ⁔ ⁀', re.UNICODE)
            # With python this matches everything except the UnicodeCombiningMark, which as I understand it contains suffixes that place accents on top of letters.
            # for some sad reason an A with a tilde, like 'A\u0300', is not matched by \w
            # Hoewever, it may be easier to just look for the character that can legally follow in
            # the json5 object case, which should be any whitespace or :
            # TODO: Include U+2028 and U+2029 here as well
            q = b' \r\n\t:},'
            if b in q:
                stream.rewind()
                raise SyntaxError(stream.err())
            r = b
        else:
            stream.rewind()
            raise SyntaxError(stream.err())
    b = stream.read()
    escape = False
    while True:
        if not escape:
            if b == b'\\':
                escape = True
            elif b in q:
                break
            else:
                if b in b'\r\n':
                    raise ParseError(stream.err())
                r += b
        elif b == b'u':
            r += chr(parseHex(stream, 4)).encode('utf8')
            escape = False
        elif b in b'xX' and JSON5_STRING_SUPPORT_HEX:
            a = parseHexInString(stream)
            r += a
            escape = False
        # TODO: Include U+2028 and U+2029 here as well
        elif b in b'\r\n' and JSON5_STRING_SUPPORT_ESCAPE_LINE_BREAKS:
            # Escape \r\n as well as just \r or just \n
            if b == b'\r':  # Windows
                b = stream.read()
                if b != b'\n':
                    stream.rewind()
            escape = False
        else:
            if b not in b'\\/bfnrt' and b != q and not JSON5_STRING_SUPPORT_CHARACTER_ESCAPES:
                raise ParseError(stream.err())
            r += b'\\' + b
            escape = False
        b = stream.read()
        if b == b'':  # EOF
            raise ParseError(stream.err())
    assert b in q
    # if b in q:
    if q not in QUOTES:
        stream.rewind()
    return r.decode('utf8')
    # raise ParseError(stream.err())


def parseInfinity(stream: AStream) -> bool:
    try:
        v = stream.read(8)
    except IOError:
        raise SyntaxError(stream.err())
    if v != b'Infinity':
        raise SyntaxError(stream.err())
    return True


def parseNaN(stream: AStream) -> bool:
    try:
        v = stream.read(3)
    except IOError:
        raise SyntaxError(stream.err())
    if v != b'NaN':
        raise SyntaxError(stream.err())
    return True


def parseTrue(stream: AStream) -> bool:
    try:
        v = stream.read(4)
    except IOError:
        raise SyntaxError(stream.err())
    if v != b'true':
        raise SyntaxError(stream.err())
    return True


def parseFalse(stream: AStream) -> bool:
    try:
        v = stream.read(5)
    except IOError:
        raise SyntaxError(stream.err())
    if v != b'false':
        raise SyntaxError(stream.err())
    return False


def parseNull(stream: AStream) -> None:
    try:
        v = stream.read(4)
    except IOError:
        raise SyntaxError(stream.err())
    if v != b'null':
        raise SyntaxError(stream.err())
    return None


def tryParse(stream: AStream, function: Callable[[AStream], JsonValue]) -> JsonValue:
    try:
        stream.save()
        result = function(stream), True
    except SyntaxError:
        result = None, False
        stream.load()
    else:
        stream.pop()
    return result


def parseValue(stream):
    parseWhitespace(stream)

    b = stream.read()
    if b == b'':
        raise SyntaxError(stream.err('Unexpected EOF'))
    stream.rewind()

    value, success = tryParse(stream, parseString)
    if not success:
        value, success = tryParse(stream, parseNumber)
    if not success:
        value, success = tryParse(stream, parseObject)
    if not success:
        value, success = tryParse(stream, parseArray)
    if not success:
        value, success = tryParse(stream, parseTrue)
    if not success:
        value, success = tryParse(stream, parseFalse)
    if not success:
        value, success = tryParse(stream, parseNull)
    if not success:
        raise SyntaxError(stream.err())
    parseWhitespace(stream)
    return value


def parseObject(stream):
    b = stream.read()
    if b != b'{':
        raise SyntaxError(stream.err())
    parseWhitespace(stream)
    result = {}
    while True:
        key, success = tryParse(stream, parseKey)
        if not success:
            if JSON5_OBJECT_SUPPORT_TRAILING_COMMA and b == b',' and result:
                parseWhitespace(stream)
                break
            break
        parseWhitespace(stream)
        b = stream.read()
        if b != b':':
            raise ParseError(stream.err())
        result[key] = parseValue(stream)
        b = stream.read()
        if b != b',':
            if b != b'}':
                raise ParseError(stream.err())
            return result
        parseWhitespace(stream)
    if JSON5_OBJECT_SUPPORT_TRAILING_COMMA and result:
        b = stream.read()
        if b == b',':
            parseWhitespace(stream)
        else:
            stream.rewind()
    b = stream.read()
    if b != b'}':
        raise ParseError(stream.err())
    return result


def parseArray(stream):
    b = stream.read()
    if b != b'[':
        raise SyntaxError(stream.err())
    parseWhitespace(stream)
    result = []
    while True:
        value, success = tryParse(stream, parseValue)
        if not success:
            if JSON5_ARRAY_SUPPORT_TRAILING_COMMA and b == b',' and result:
                parseWhitespace(stream)
                break
            break
        result.append(value)
        b = stream.read()
        if b != b',':
            if b != b']':
                raise ParseError(stream.err())
            return result
    if JSON5_ARRAY_SUPPORT_TRAILING_COMMA and result:
        b = stream.read()
        if b == b',':
            parseWhitespace(stream)
        else:
            stream.rewind()
    b = stream.read()
    if b != b']':
        raise ParseError(stream.err())
    return result


def parse(stream):
    try:
        value = parseValue(stream)
    except SyntaxError as e:
        raise ParseError(e)

    parseWhitespace(stream)
    if stream.read() != b'':
        raise ParseError(stream.err('End of file not reached after parsing finished.'))

    return value
