base85_ascii85_decoder — Adobe-Ascii85 (PostScript/PDF) encode/decode

Encode and decode the Ascii85 variant used by Adobe PostScript and PDF. Two
delimited forms are supported on decode: a bare stream of digits, or a stream
wrapped in `<~` ... `~>`. Whitespace inside the stream is ignored.

```python
from base85_ascii85_decoder import decode, encode

assert decode(b'<~9jqo^~>') == b'Man '
assert encode(b'Man') == '<~9jqo~>'
```

`decode` accepts `str`, `bytes`, or `bytearray` and returns `bytes`. `encode`
accepts `bytes`/`bytearray` and returns `str`. An invalid character, a value
that exceeds the 32-bit range, or a missing closing `~>` raises
`Ascii85DecodeError` (a subclass of `ValueError`).

Why this exists
---------------
Python's standard library ships `base64.a85decode`/`a85encode`, which cover the
same format. This library exists for callers who want a tiny, dependency-free
module with a narrow, explicit surface: `decode`, `encode`, and a dedicated
exception type. The trade-off is that `base64` also handles btoa-style variants
and the `z` zero-compression shorthand; this library intentionally does not
emit `z` on encode (to keep round-trips trivial) and only recognizes the Adobe
delimited form on decode. Pick one variant, implement it honestly.

Awkward edge
------------
A trailing partial word (1, 2, or 3 bytes) is padded with zero bytes to a
full 32-bit word for encoding, and the surplus digits are dropped. On decode,
the short tail is padded with the highest digit (`u`, value 84) before
recombination, per the Adobe spec. Callers that mix this library's output with
encoders or decoders that use a different tail convention (some pad with `u`
on encode, others with `!`) may see mismatches on inputs whose length is not a
multiple of four. This library is internally consistent: `decode(encode(x)) ==
x` for every `bytes` input.
