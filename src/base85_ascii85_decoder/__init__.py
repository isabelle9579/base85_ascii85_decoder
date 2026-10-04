"""Ascii85 (Adobe variant) encoder and decoder."""

from base85_ascii85_decoder.core import (
    Ascii85DecodeError,
    decode,
    encode,
)

__all__ = [
    "Ascii85DecodeError",
    "decode",
    "encode",
]
