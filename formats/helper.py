import json
import os
import struct


# ----------------------------------------------------------------------------------------------------------------------
# Binary data helpers
# ----------------------------------------------------------------------------------------------------------------------
U8 = struct.Struct("B")
S8 = struct.Struct("b")
U16 = struct.Struct(">H")
S16 = struct.Struct(">h")
U32 = struct.Struct(">I")
S32 = struct.Struct(">i")
U64 = struct.Struct(">Q")
S64 = struct.Struct(">q")
F32 = struct.Struct(">f")
F64 = struct.Struct(">d")


def get_bool(buffer, offset: int = 0) -> bool:
    return buffer[offset] != 0


def get_u8(buffer, offset: int) -> int:
    return buffer[offset]


def get_s8(buffer, offset: int) -> int:
    return S8.unpack_from(buffer, offset)[0]


def get_u16(buffer, offset: int) -> int:
    return U16.unpack_from(buffer, offset)[0]


def get_s16(buffer, offset: int) -> int:
    return S16.unpack_from(buffer, offset)[0]


def get_u32(buffer, offset: int) -> int:
    return U32.unpack_from(buffer, offset)[0]


def get_s32(buffer, offset: int) -> int:
    return S32.unpack_from(buffer, offset)[0]


def get_u64(buffer, offset: int) -> int:
    return U64.unpack_from(buffer, offset)[0]


def get_s64(buffer, offset: int) -> int:
    return S64.unpack_from(buffer, offset)[0]


def get_f32(buffer, offset: int) -> int:
    return F32.unpack_from(buffer, offset)[0]


def get_f64(buffer, offset: int) -> int:
    return F64.unpack_from(buffer, offset)[0]


def pack_bool(val: bool) -> bytes:
    return pack_u8(1 if val else 0)


def pack_u8(val: int) -> bytes:
    return U8.pack(val)


def pack_s8(val: int) -> bytes:
    return S8.pack(val)


def pack_u16(val: int) -> bytes:
    return U16.pack(val)


def pack_s16(val: int) -> bytes:
    return S16.pack(val)


def pack_u32(val: int) -> bytes:
    return U32.pack(val)


def pack_s32(val: int) -> bytes:
    return S32.pack(val)


def pack_u64(val: int) -> bytes:
    return U64.pack(val)


def pack_s64(val: int) -> bytes:
    return S64.pack(val)


def pack_f32(val: float) -> bytes:
    return F32.pack(val)


def pack_f64(val: float) -> bytes:
    return F64.pack(val)


def try_sign8(val: int) -> int:
    if val & 0x80:
        return val | ~0x7F
    return val


def try_sign16(val: int) -> int:
    if val & 0x8000:
        return val | ~0x7FFF
    return val


def try_sign32(val: int) -> int:
    if val & 0x80000000:
        return val | ~0x7FFFFFFF
    return val


def try_sign64(val: int) -> int:
    if val & 0x8000000000000000:
        return val | ~0x7FFFFFFFFFFFFFFF
    return val


# ----------------------------------------------------------------------------------------------------------------------
# String reading & packing
# ----------------------------------------------------------------------------------------------------------------------
def read_string(buffer, offset: int, charset: str = "ascii") -> str:
    """
    Decodes and returns a null-terminated string at the buffer's specified offset. By default, the charset used is
    assumed to be "ascii".

    :param buffer: buffer containing data
    :param offset: offset of string
    :param charset: charset to decode string with, default is "ascii"
    :returns: the decoded string
    """
    end = offset
    while end < len(buffer) - 1 and buffer[end] != 0:
        end += 1
    return buffer[offset:end + 1].decode(charset).strip("\0")


def pack_string(val: str, charset: str = "ascii") -> bytes:
    """
    Encodes a string using the specified charset and returns the bytes.

    :param val: the string to be encoded
    :param charset: charset to encode string with, default is "ascii"
    :returns: the encoded string bytes
    """
    if not val.endswith("\0"):
        val += "\0"
    return val.encode(charset)


def read_fixed_string(buffer, offset: int, size: int, charset: str = "ascii") -> str:
    """
    Decodes and returns a fixed-length string at the buffer's specified offset. By default, the charset used is assumed
    to be "ascii".

    :param buffer: buffer containing data
    :param offset: offset of string
    :param size: size of string in bytes
    :param charset: charset to decode string with, default is "ascii"
    :returns: the decoded string
    """
    start = offset
    end = offset + size
    while offset < end:
        if buffer[offset] == 0:
            end = offset
            break
        offset += 1
    return buffer[start:end].decode(charset)


def pack_fixed_string(val: str, size: int, charset: str = "ascii"):
    """
    Encodes a string using the specified charset and returns the bytes. The size of the returned bytes matches the size
    parameter. If the size of the encoded bytes is less than the specified size, the bytes are padded to match the
    expected size. In case the size of the encoded string is larger than the specified size, the encoded bytes are
    truncated which causes data loss.

    :param val: the string to be encoded
    :param size: max number of encoded bytes
    :param charset: charset to encode string with, default is "ascii"
    :returns: the encoded string bytes
    """
    encoded = bytearray(val.encode(charset))
    enc_size = len(encoded)

    if enc_size < size:
        encoded += bytearray(size - enc_size)
    elif enc_size > size:
        encoded = encoded[:size]
    return encoded


def get_magic4(buffer, offset: int = 0):
    return read_fixed_string(buffer, offset, 4)


def get_magic8(buffer, offset: int = 0):
    return read_fixed_string(buffer, offset, 8)


def pack_magic4(val: str) -> bytes:
    return pack_fixed_string(val, 4)


def pack_magic8(val: str) -> bytes:
    return pack_fixed_string(val, 8)


# ----------------------------------------------------------------------------------------------------------------------
# File I/O helpers
# ----------------------------------------------------------------------------------------------------------------------
def get_filename(file_path: str) -> str:
    """
    Extracts the filename without extension from the specified file path.

    :param file_path: the file path to extract the basename from
    :returns: basename of the specified path without extension
    """
    return os.path.splitext(os.path.basename(file_path))[0]


def read_bin_file(file_path: str) -> bytearray:
    """
    Reads the binary data from the specified file and returns the contents as a bytearray.

    :param file_path: the file path to read the contents from
    :returns: a bytebuffer containing the file's contents
    """
    with open(file_path, "rb") as f:
        ret = f.read()
    return bytearray(ret)


def write_file(file_path: str, buffer):
    """
    Writes the contents of a bytes-like buffer to the specified file. If the parent directories do not exist, they will
    be created.

    :param file_path: the file to write the data into
    :param buffer: the data to write to the file
    :raises ValueError: when buffer is None
    """
    if buffer is None:
        raise ValueError("Tried to write non-existent data to file.")

    # Try to create parent directories if necessary
    if file_path.find("/") != -1:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "wb") as f:
        f.write(buffer)
        f.flush()


def read_json_file(file_path: str):
    """
    Reads the JSON data from the specified file. This assumes that the file uses UTF-8 encoding.

    :param file_path: the file path to load the JSON data from
    :returns: a list or dictionary containing JSON data
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def write_json_file(file_path: str, data):
    """
    Writes the JSON data to the specified file using UTF-8 encoding. Each level/node is indented by four spaces. If the
    parent directories do not exist, they will be created.

    :param file_path: the file to write the data into
    :param data: the JSON data to write to the file
    """
    # Try to create parent directories if necessary
    if file_path.find("/") != -1:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.flush()


# ----------------------------------------------------------------------------------------------------------------------
# Buffer alignment helpers
# ----------------------------------------------------------------------------------------------------------------------
def __align(buffer, size, pad_chr):
    pad_len = len(buffer) & (size - 1)
    pad_chr = ord(pad_chr)
    if pad_len != 0:
        return bytearray([pad_chr] * (size - pad_len))
    return bytearray()


def align4(buffer, pad_chr="\0"):
    """
    Generate the padding bytes required to align the specified buffer to 4 bytes. The returned buffer consists of 0 to 3
    bytes, depending on the input buffer's current size. NULL (0) is used to pad out the space, but the padding char
    can be specified.

    :param buffer: the buffer to generate the alignment for
    :param pad_chr: ASCII character to pad aligned space with
    :returns: bytearray containing alignment padding
    """
    return __align(buffer, 4, pad_chr)


def align8(buffer, pad_chr="\0"):
    """
    Generate the padding bytes required to align the specified buffer to 8 bytes. The returned buffer consists of 0 to 7
    bytes, depending on the input buffer's current size. NULL (0) is used to pad out the space, but the padding char
    can be specified.

    :param buffer: the buffer to generate the alignment for
    :param pad_chr: ASCII character to pad aligned space with
    :returns: bytearray containing alignment padding
    """
    return __align(buffer, 8, pad_chr)


def align16(buffer, pad_chr="\0"):
    """
    Generate the padding bytes required to align the specified buffer to 16 bytes. The returned buffer consists of 0 to
    15 bytes, depending on the input buffer's current size. NULL (0) is used to pad out the space, but the padding char
    can be specified.

    :param buffer: the buffer to generate the alignment for
    :param pad_chr: ASCII character to pad aligned space with
    :returns: bytearray containing alignment padding
    """
    return __align(buffer, 16, pad_chr)


def align32(buffer, pad_chr="\0"):
    """
    Generate the padding bytes required to align the specified buffer to 32 bytes. The returned buffer consists of 0 to
    31 bytes, depending on the input buffer's current size. NULL (0) is used to pad out the space, but the padding char
    can be specified.

    :param buffer: the buffer to generate the alignment for
    :param pad_chr: ASCII character to pad aligned space with
    :returns: bytearray containing alignment padding
    """
    return __align(buffer, 32, pad_chr)
