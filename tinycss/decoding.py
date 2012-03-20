# coding: utf8
"""
    tinycss.decoding
    ----------------

    Decoding stylesheets from bytes to Unicode.
    http://www.w3.org/TR/CSS21/syndata.html#charset

    :copyright: (c) 2010 by Simon Sapin.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import unicode_literals

from binascii import unhexlify
import operator
import re


__all__ = ['decode']  # Everything else is implementation detail


def decode(css_bytes, protocol_encoding=None,
           linking_encoding=None, document_encoding=None):
    """
    Determine the character encoding from the passed metadata and the
    ``@charset`` rule in the stylesheet (if any); and decode accordingly.

    :param css_bytes:
        a CSS stylesheet as a byte string
    :param protocol_encoding:
        The "charset" parameter of a "Content-Type" HTTP header (if any),
        or similar metadata for other protocols.
    :param linking_encoding:
        ``<link charset="">`` or other metadata from the linking mechanism
        (if any)
    :param document_encoding:
        Encoding of the referring style sheet or document (if any)
    :raises:
        :class:`UnicodeDecodeError` if decoding failed
    :return:
        Unicode string, with any BOM removed

    """
    if protocol_encoding:
        css_unicode = try_encoding(css_bytes, protocol_encoding)
        if css_unicode is not None:
            return css_unicode
    for bom_size, encoding, pattern in ENCODING_MAGIC_NUMBERS:
        match = pattern(css_bytes)
        if match:
            has_at_charset = isinstance(encoding, tuple)
            if has_at_charset:
                extract, endianness = encoding
                encoding = extract(match.group(1)).decode('ascii', 'replace')
                if encoding.replace('-', '').replace('_', '').lower() in [
                        'utf16', 'utf32']:
                    encoding += endianness
            css_unicode = try_encoding(css_bytes, encoding)
            if css_unicode and not (has_at_charset and not
                                    css_unicode.startswith('@charset "')):
                return css_unicode
            break
    for encoding in [linking_encoding, document_encoding]:
        if encoding:
            css_unicode = try_encoding(css_bytes, encoding)
            if css_unicode is not None:
                return css_unicode
    return try_encoding(css_bytes, 'utf8', fallback=False)


def try_encoding(css_bytes, encoding, fallback=True):
    try:
        css_unicode = css_bytes.decode(encoding)
    # LookupEror means unknown encoding
    except (UnicodeDecodeError, LookupError):
        if not fallback:
            raise
        return None
    if css_unicode[0] == '\ufeff':
        # Remove any Byte Order Mark
        css_unicode = css_unicode[1:]
    return css_unicode


def hex2re(hex_data):
    return re.escape(unhexlify(hex_data.replace(' ', '').encode('ascii')))


class Slicer(object):
    """Slice()[start:stop:end] == slice(start, stop, end)"""
    def __getitem__(self, slice_):
        return operator.itemgetter(slice_)

Slice = Slicer()


# List of (bom_size, encoding, pattern)
#   bom_size is in bytes and can be zero
#   encoding is a string or (slice_, endianness) for "as specified"
#   slice_ is a slice object.How to extract the specified

ENCODING_MAGIC_NUMBERS = [
    (3, (Slice[:], ''), re.compile(
        hex2re('EF BB BF 40 63 68 61 72 73 65 74 20 22')
        + b'([^\x22]*?)'
        + hex2re('22 3B')).match),

    (3, 'UTF-8', re.compile(
        hex2re('EF BB BF')).match),

    (0, (Slice[:], ''), re.compile(
        hex2re('40 63 68 61 72 73 65 74 20 22')
        + b'([^\x22]*?)'
        + hex2re('22 3B')).match),

    (2, (Slice[1::2], '-BE'), re.compile(
        hex2re('FE FF 00 40 00 63 00 68 00 61 00 72 00 73 00 65 00'
               '74 00 20 00 22')
        + b'((\x00[^\x22])*?)'
        + hex2re('00 22 00 3B')).match),

    (0, (Slice[1::2], '-BE'), re.compile(
        hex2re('00 40 00 63 00 68 00 61 00 72 00 73 00 65 00 74 00'
               '20 00 22')
        + b'((\x00[^\x22])*?)'
        + hex2re('00 22 00 3B')).match),

    (2, (Slice[::2], '-LE'), re.compile(
        hex2re('FF FE 40 00 63 00 68 00 61 00 72 00 73 00 65 00 74'
               '00 20 00 22 00')
        + b'(([^\x22]\x00)*?)'
        + hex2re('22 00 3B 00')).match),

    (0, (Slice[::2], '-LE'), re.compile(
        hex2re('40 00 63 00 68 00 61 00 72 00 73 00 65 00 74 00 20'
               '00 22 00')
        + b'(([^\x22]\x00)*?)'
        + hex2re('22 00 3B 00')).match),

    (4, (Slice[3::4], '-BE'), re.compile(
        hex2re('00 00 FE FF 00 00 00 40 00 00 00 63 00 00 00 68 00'
               '00 00 61 00 00 00 72 00 00 00 73 00 00 00 65 00 00'
               '00 74 00 00 00 20 00 00 00 22')
        + b'((\x00\x00\x00[^\x22])*?)'
        + hex2re('00 00 00 22 00 00 00 3B')).match),

    (0, (Slice[3::4], '-BE'), re.compile(
        hex2re('00 00 00 40 00 00 00 63 00 00 00 68 00 00 00 61 00'
               '00 00 72 00 00 00 73 00 00 00 65 00 00 00 74 00 00'
               '00 20 00 00 00 22')
        + b'((\x00\x00\x00[^\x22])*?)'
        + hex2re('00 00 00 22 00 00 00 3B')).match),


# Python does not support 2143 or 3412 endianness, AFAIK.
# I guess we could fix it up ourselves but meh. Patches welcome.

#    (4, (Slice[2::4], '-2143'), re.compile(
#        hex2re('00 00 FF FE 00 00 40 00 00 00 63 00 00 00 68 00 00'
#               '00 61 00 00 00 72 00 00 00 73 00 00 00 65 00 00 00'
#               '74 00 00 00 20 00 00 00 22 00')
#        + b'((\x00\x00[^\x22]\x00)*?)'
#        + hex2re('00 00 22 00 00 00 3B 00')).match),

#    (0, (Slice[2::4], '-2143'), re.compile(
#        hex2re('00 00 40 00 00 00 63 00 00 00 68 00 00 00 61 00 00'
#               '00 72 00 00 00 73 00 00 00 65 00 00 00 74 00 00 00'
#               '20 00 00 00 22 00')
#        + b'((\x00\x00[^\x22]\x00)*?)'
#        + hex2re('00 00 22 00 00 00 3B 00')).match),

#    (4, (Slice[1::4], '-3412'), re.compile(
#        hex2re('FE FF 00 00 00 40 00 00 00 63 00 00 00 68 00 00 00'
#               '61 00 00 00 72 00 00 00 73 00 00 00 65 00 00 00 74'
#               '00 00 00 20 00 00 00 22 00 00')
#        + b'((\x00[^\x22]\x00\x00)*?)'
#        + hex2re('00 22 00 00 00 3B 00 00')).match),

#    (0, (Slice[1::4], '-3412'), re.compile(
#        hex2re('00 40 00 00 00 63 00 00 00 68 00 00 00 61 00 00 00'
#               '72 00 00 00 73 00 00 00 65 00 00 00 74 00 00 00 20'
#               '00 00 00 22 00 00')
#        + b'((\x00[^\x22]\x00\x00)*?)'
#        + hex2re('00 22 00 00 00 3B 00 00')).match),

    (4, (Slice[::4], '-LE'), re.compile(
        hex2re('FF FE 00 00 40 00 00 00 63 00 00 00 68 00 00 00 61'
               '00 00 00 72 00 00 00 73 00 00 00 65 00 00 00 74 00'
               '00 00 20 00 00 00 22 00 00 00')
        + b'(([^\x22]\x00\x00\x00)*?)'
        + hex2re('22 00 00 00 3B 00 00 00')).match),

    (0, (Slice[::4], '-LE'), re.compile(
        hex2re('40 00 00 00 63 00 00 00 68 00 00 00 61 00 00 00 72'
               '00 00 00 73 00 00 00 65 00 00 00 74 00 00 00 20 00'
               '00 00 22 00 00 00')
        + b'(([^\x22]\x00\x00\x00)*?)'
        + hex2re('22 00 00 00 3B 00 00 00')).match),

    (4, 'UTF-32-BE', re.compile(
        hex2re('00 00 FE FF')).match),

    (4, 'UTF-32-LE', re.compile(
        hex2re('FF FE 00 00')).match),

#    (4, 'UTF-32-2143', re.compile(
#        hex2re('00 00 FF FE')).match),

#    (4, 'UTF-32-3412', re.compile(
#        hex2re('FE FF 00 00')).match),

    (2, 'UTF-16-BE', re.compile(
        hex2re('FE FF')).match),

    (2, 'UTF-16-LE', re.compile(
        hex2re('FF FE')).match),


# Some of there are supported by Python, but I didn’t bother.
# You know the story with patches ...

#    # as specified, transcoded from EBCDIC to ASCII
#    (0, 'as_specified-EBCDIC', re.compile(
#        hex2re('7C 83 88 81 99 A2 85 A3 40 7F')
#        + b'([^\x7F]*?)'
#        + hex2re('7F 5E')).match),

#    # as specified, transcoded from IBM1026 to ASCII
#    (0, 'as_specified-IBM1026', re.compile(
#        hex2re('AE 83 88 81 99 A2 85 A3 40 FC')
#        + b'([^\xFC]*?)'
#        + hex2re('FC 5E')).match),

#    # as specified, transcoded from GSM 03.38 to ASCII
#    (0, 'as_specified-GSM_03.38', re.compile(
#        hex2re('00 63 68 61 72 73 65 74 20 22')
#        + b'([^\x22]*?)'
#        + hex2re('22 3B')).match),
]