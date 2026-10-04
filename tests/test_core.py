import unittest

from base85_ascii85_decoder import decode, encode, Ascii85DecodeError


class DecodeRoundTripTests(unittest.TestCase):

    def test_empty_input_returns_empty_bytes(self):
        self.assertEqual(decode(b''), b'')

    def test_empty_input_str_returns_empty_bytes(self):
        self.assertEqual(decode(''), b'')

    def test_single_byte(self):
        # The shortest non-empty encoding: a 1-byte input produces 2 chars.
        self.assertEqual(decode(b'!!'), b'\x00')

    def test_two_bytes(self):
        self.assertEqual(decode(b'!!!'), b'\x00\x00')

    def test_three_bytes(self):
        self.assertEqual(decode(b'!!!!'), b'\x00\x00\x00')

    def test_full_word_all_zero(self):
        # Four zero bytes encode to '!!!!!' (no z shorthand here).
        self.assertEqual(decode(b'!!!!!'), b'\x00\x00\x00\x00')

    def test_known_vector_man(self):
        # Classic reference vector: the first 4 bytes of
        # "Man is distinguished" -> <~9jqo^BlbD-BT...~> are "Man ".
        self.assertEqual(decode(b'9jqo^'), b'Man ')

    def test_known_vector_with_delimiters(self):
        self.assertEqual(decode('<~9jqo^~>'), b'Man ')

    def test_round_trip_various_lengths(self):
        for payload in (
            b'',
            b'\x00',
            b'\x01\x02',
            b'Man',
            b'\x00\x00\x00\x00',
            b'\xff\xff\xff\xff',
            b'four',
            b'five\x00',
            b'six bytes here',
            bytes(range(256)),
        ):
            with self.subTest(payload=payload):
                self.assertEqual(decode(encode(payload)), payload)

    def test_whitespace_is_ignored(self):
        self.assertEqual(decode(b'\t9jqo^\n'), b'Man ')

    def test_invalid_character_raises(self):
        with self.assertRaises(Ascii85DecodeError):
            decode(b'9jqo~')

    def test_value_above_2_pow_32_raises(self):
        with self.assertRaises(Ascii85DecodeError):
            decode(b't!!!!')


class EncodeTests(unittest.TestCase):

    def test_encode_empty(self):
        self.assertEqual(encode(b''), '<~~>')

    def test_encode_known_vector(self):
        self.assertEqual(encode(b'Man'), '<~9jqo~>')

    def test_encode_rejects_str(self):
        with self.assertRaises(TypeError):
            encode('Man')


class TypeHandlingTests(unittest.TestCase):

    def test_decode_accepts_bytearray(self):
        self.assertEqual(decode(bytearray(b'9jqo^')), b'Man ')

    def test_decode_rejects_int(self):
        with self.assertRaises(TypeError):
            decode(123)

    def test_decode_rejects_none(self):
        with self.assertRaises(TypeError):
            decode(None)


if __name__ == '__main__':
    unittest.main()
