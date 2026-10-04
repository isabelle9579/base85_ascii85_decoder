"""Core Ascii85 implementation for the Adobe / PostScript / PDF variant.

Ascii85 packs a 32-bit word into 5 base-85 digits. This module implements the
Adobe variant, which uses ``<~`` and ``~>`` delimiters in encoded blocks.

Design decisions:
    * ``decode`` accepts either ``str`` or ``bytes``. The standard-library
      ``base64.a85decode`` supports both, so matching that keeps the API
      familiar. Internally we normalize to ``bytes``.
    * ``encode`` always returns ``str``. The 85-symbol alphabet is printable
      ASCII; returning ``str`` keeps Python byte-string / text-string boundary
      confusion to a minimum and matches the most common library convention
      (`base64.a85encode` returns ``bytes``, but every Ascii85 reference we
      found in the wild treats the output as text).
    * The short-block tail of ``encode`` pads with zero bytes to a full
      32-bit word, encodes all 5 digits, then drops the surplus digits.
      This mirrors how PostScript defines the tail rather than how some
      other implementations fudge it, and round-trips cleanly with ``decode``
      because ``decode`` re-pads before unpacking.
"""

from __future__ import annotations

# Base-85 alphabet, ordered so that the digit value equals the index.
_ASCII85_ALPHABET = (
    '!' + '"' + '#' + '$' + '%' + '&' + "'" + '(' + ')' + '*' +
    '+' + ',' + '-' + '.' + '/' + '0' + '1' + '2' + '3' + '4' +
    '5' + '6' + '7' + '8' + '9' + ':' + ';' + '<' + '=' + '>' +
    '?' + '@' + 'A' + 'B' + 'C' + 'D' + 'E' + 'F' + 'G' + 'H' +
    'I' + 'J' + 'K' + 'L' + 'M' + 'N' + 'O' + 'P' + 'Q' + 'R' +
    'S' + 'T' + 'U' + 'V' + 'W' + 'X' + 'Y' + 'Z' + '[' + '\\' +
    ']' + '^' + '_' + '`' + 'a' + 'b' + 'c' + 'd' + 'e' + 'f' +
    'g' + 'h' + 'i' + 'j' + 'k' + 'l' + 'm' + 'n' + 'o' + 'p' +
    'q' + 'r' + 's' + 't' + 'u'
)
assert len(_ASCII85_ALPHABET) == 85

# Inverse map: byte value of the printable-ASCII character -> digit 0..84.
# Anything outside the printable range maps to -1 (invalid).
_DECODE_TABLE = [-1] * 256
for _i, _ch in enumerate(_ASCII85_ALPHABET):
    _DECODE_TABLE[ord(_ch)] = _i


class Ascii85DecodeError(ValueError):
    """Raised when an Ascii85 input cannot be decoded.

    Subclassing ValueError keeps compatibility with callers that catch
    ValueError broadly, while still letting decoder-specific handling target
    this class.
    """


def _normalize_input(data) -> bytes:
    """Coerce ``str`` or ``bytes`` to ``bytes``.

    Accepting both keeps the public API friendly; rejecting other types
    early gives a clear error instead of an AttributeError deep inside.
    """
    if isinstance(data, str):
        return data.encode('ascii')
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    raise TypeError(
        'decode expects str or bytes, got ' + type(data).__name__
    )


def decode(data) -> bytes:
    """Decode an Adobe-Ascii85-encoded sequence into raw bytes.

    If the input contains ``<~`` / ``~>`` delimiters, only the text between
    them is decoded; everything outside is ignored, matching the behavior
    of the PostScript / PDF convention. If delimiters are absent, the whole
    input (minus whitespace, which is ignored everywhere) is decoded.

    Partial trailing groups are supported: a group of length ``n`` (1 <= n <= 4)
    encodes ``n - 1`` output bytes, exactly as the format specifies.

    Raises:
        Ascii85DecodeError: if the input contains invalid characters, a
            digit out of the 0..84 range, or the all-zero word encoded
            explicitly (which would overflow 32 bits when recombined).
        TypeError: if ``data`` is neither ``str`` nor ``bytes``.
    """
    raw = _normalize_input(data)

    # Strip delimiters if present. We only honour the first ``<~`` and the
    # last ``~>``; content between multiple delimiter pairs is not a case the
    # format defines, so we do not invent semantics for it.
    start = raw.find(b'<~')
    if start != -1:
        end = raw.rfind(b'~>')
        if end == -1 or end < start:
            raise Ascii85DecodeError('opening <~ without matching ~>')
        raw = raw[start + 2:end]

    # Whitespace inside the encoded stream is always ignored.
    body = bytes(b for b in raw if not _is_whitespace(b))

    out = bytearray()
    i = 0
    n = len(body)
    while i < n:
        chunk = body[i:i + 5]
        i += 5
        clen = len(chunk)
        if clen == 5:
            # Validate characters before using them so invalid inputs raise
            # instead of producing silently wrong output.
            for c in chunk:
                if _DECODE_TABLE[c] < 0:
                    raise Ascii85DecodeError('invalid character: ' + chr(c))
            # Fast path: a full group. Inline the powers to avoid a loop and
            # because it reads as the definition of base-85.
            v = (
                _DECODE_TABLE[chunk[0]] * 85 ** 4 +
                _DECODE_TABLE[chunk[1]] * 85 ** 3 +
                _DECODE_TABLE[chunk[2]] * 85 ** 2 +
                _DECODE_TABLE[chunk[3]] * 85 +
                _DECODE_TABLE[chunk[4]]
            )
            if v >= 2 ** 32:
                raise Ascii85DecodeError(
                    'encoded value exceeds 32-bit range'
                )
            out.extend(v.to_bytes(4, 'big'))
        else:
            # Partial tail. Per the spec, pad with the highest digit ('u',
            # value 84), recombine, take the first clen-1 bytes. This lets a
            # short input encode deterministically and round-trip.
            padded = chunk + b'u' * (5 - clen)
            v = 0
            for c in padded:
                d = _DECODE_TABLE[c]
                if d < 0:
                    raise Ascii85DecodeError(
                        'invalid character in tail: ' + chr(c)
                    )
                v = v * 85 + d
            if v >= 2 ** 32:
                raise Ascii85DecodeError(
                    'tail value exceeds 32-bit range'
                )
            out.extend(v.to_bytes(4, 'big')[:clen - 1])
            break

    return bytes(out)


def _is_whitespace(b: int) -> bool:
    """True for ASCII whitespace bytes that Ascii85 ignores."""
    return b in (0x20, 0x09, 0x0A, 0x0C, 0x0D)


def encode(data) -> str:
    """Encode raw bytes into Adobe-Ascii85 text wrapped in ``<~`` / ``~>``.

    The output is always five characters per 32-bit word. A trailing partial
    word (1, 2, or 3 bytes) is padded with zero bytes to a full word, encoded
    as five digits, and then the surplus digits are dropped so that a decoder
    can recover the exact original length. No zero-compression (``z``)
    shorthand is emitted; this keeps the format unambiguous and ensures a
    trivial round-trip with :func:`decode`.

    Args:
        data: ``bytes`` (or ``bytearray``) to encode.

    Returns:
        The encoded ``str``, including delimiters.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError(
            'encode expects bytes, got ' + type(data).__name__
        )
    b = bytes(data)
    out = ['<~']
    for i in range(0, len(b), 4):
        word = b[i:i + 4]
        wl = len(word)
        if wl == 4:
            v = int.from_bytes(word, 'big')
            digits = _encode_word(v)
        else:
            # Pad short tail with zeros to a full 32-bit word, then encode
            # normally. We drop the surplus trailing digits afterwards so
            # the decoder, which pads with 'u' (84), can recover the length.
            v = int.from_bytes(word + b'\x00' * (4 - wl), 'big')
            digits = _encode_word(v)[:wl + 1]
        out.append(digits)
    out.append('~>')
    return ''.join(out)


def _encode_word(v: int) -> str:
    """Turn a 32-bit integer into 5 Ascii85 characters."""
    d0 = v // (85 ** 4) % 85
    d1 = v // (85 ** 3) % 85
    d2 = v // (85 ** 2) % 85
    d3 = v // 85 % 85
    d4 = v % 85
    return (
        _ASCII85_ALPHABET[d0] +
        _ASCII85_ALPHABET[d1] +
        _ASCII85_ALPHABET[d2] +
        _ASCII85_ALPHABET[d3] +
        _ASCII85_ALPHABET[d4]
    )
