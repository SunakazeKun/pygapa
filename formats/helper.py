import json
import os
import struct


# unpack_from and pack shortcuts

def get_bool(buffer, offset: int = 0) -> bool:
    return struct.unpack_from("?", buffer, offset)[0]


def get_u8(b, o: int) -> int:
    return b[o]


def get_s8(b, o: int) -> int:
    val = b[o]
    if val & 0x80:
        val |= ~0xFF
    return val


def get_u16(b, o: int) -> int:
    return struct.unpack_from(">H", b, o)[0]


def get_s16(b, o: int) -> int:
    return struct.unpack_from(">h", b, o)[0]


def get_u32(b, o: int) -> int:
    return struct.unpack_from(">I", b, o)[0]


def get_s32(b, o: int) -> int:
    return struct.unpack_from(">i", b, o)[0]


def get_u64(b, o: int) -> int:
    return struct.unpack_from(">Q", b, o)[0]


def get_s64(b, o: int) -> int:
    return struct.unpack_from(">q", b, o)[0]


def get_f32(b, o: int) -> float:
    return struct.unpack_from(">f", b, o)[0]


def get_f64(b, o: int) -> float:
    return struct.unpack_from(">d", b, o)[0]


def get_magic4(buffer, offset: int = 0):
    return buffer[offset:offset+4].decode("ascii")


def get_magic8(buffer, offset: int = 0):
    return buffer[offset:offset+8].decode("ascii")


def pack_bool(val: bool) -> bytes:
    return pack_u8(1 if val else 0)


def pack_u8(v: int) -> bytes:
    return struct.pack("B", v)


def pack_s8(v: int) -> bytes:
    return struct.pack("b", v)


def pack_u16(v: int) -> bytes:
    return struct.pack(">H", v)


def pack_s16(v: int) -> bytes:
    return struct.pack(">h", v)


def pack_u32(v: int) -> bytes:
    return struct.pack(">I", v)


def pack_s32(v: int) -> bytes:
    return struct.pack(">i", v)


def pack_u64(v: int) -> bytes:
    return struct.pack(">Q", v)


def pack_s64(v: int) -> bytes:
    return struct.pack(">q", v)


def pack_f32(v: float) -> bytes:
    return struct.pack(">f", v)


def pack_f64(v: float) -> bytes:
    return struct.pack(">d", v)


def __pack_magic(val: str, size: int) -> bytes:
    magic = val.encode("ascii")
    real_size = len(magic)

    if real_size < size:
        return magic + bytes(size - real_size)
    elif real_size > size:
        return magic[:size]
    else:
        return magic


def pack_magic4(val: str) -> bytes:
    return __pack_magic(val, 4)


def pack_magic8(val: str) -> bytes:
    return __pack_magic(val, 8)


# String helper functions
def __read_string(charset: str, buffer, offset: int = 0) -> str:
    end = offset
    while end < len(buffer) - 1 and buffer[end] != 0:
        end += 1
    return buffer[offset:end + 1].decode(charset).strip("\0")


def __pack_string(charset: str, val: str) -> bytes:
    if not val.endswith("\0"):
        val += "\0"
    return val.encode(charset)


def read_ascii(buffer, offset: int = 0) -> str:
    """Decodes and returns the ASCII string at the buffer's specified offset."""
    return __read_string("ascii", buffer, offset)


def pack_ascii(val: str) -> bytes:
    """Encodes the string using ASCII and returns the packed bytes. Null-terminates the string if necessary"""
    return __pack_string("ascii", val)


def read_sjis(buffer, offset: int) -> str:
    """Decodes and returns the SJIS string at the buffer's specified offset."""
    return __read_string("shift_jisx0213", buffer, offset)


def pack_sjis(val: str) -> bytes:
    """Encodes the string using SJIS and returns the packed bytes. Null-terminates the string if necessary"""
    return __pack_string("shift_jisx0213", val)


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
