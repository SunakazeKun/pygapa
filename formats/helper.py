import json
import os
import struct


# unpack_from and pack shortcuts

def get_bool(buffer, offset: int = 0) -> bool:
    return struct.unpack_from("?", buffer, offset)[0]


def get_u8(b, o: int) -> int:
    return b[o] & 0xFF


def get_s8(b, o: int) -> int:
    return struct.unpack_from("b", b, o)[0]


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


def get_filename(val: str) -> str:
    """Extracts the filename without extension from the specified file path."""
    return os.path.splitext(os.path.basename(val))[0]


# File I/O functions

def read_file(file_path) -> bytearray:
    """Reads the binary data from the specified file and returns it as a bytearray."""
    with open(file_path, "rb") as f:
        ret = f.read()
    return bytearray(ret)


def write_file(file_path, buffer):
    """Writes the contents of a bytes-like object to the specified file."""
    with open(file_path, "wb") as f:
        f.write(buffer)
        f.flush()


def read_json_file(file_path):
    """Reads the JSON data from the specified file. This assumes that the file uses UTF-8 encoding."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def write_json_file(file_path: str, data):
    """Writes the JSON data to the specified file using UTF-8 encoding. Each level/node is indented by four spaces."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.flush()


# Buffer alignment functions

def __align(buffer, size, pad_chr):
    """Returns the padding bytes required to align the buffer to the specified size."""
    pad_len = len(buffer) & (size - 1)
    if pad_len != 0:
        return bytearray([ord(pad_chr)] * (size - pad_len))
    return bytearray()


def align4(buffer, pad_chr="\0"):
    """Returns the padding bytes required to align the specified buffer to 4 bytes."""
    return __align(buffer, 4, pad_chr)


def align8(buffer, pad_chr="\0"):
    """Returns the padding bytes required to align the specified buffer to 8 bytes."""
    return __align(buffer, 8, pad_chr)


def align16(buffer, pad_chr="\0"):
    """Returns the padding bytes required to align the specified buffer to 16 bytes."""
    return __align(buffer, 16, pad_chr)


def align32(buffer, pad_chr="\0"):
    """Returns the padding bytes required to align the specified buffer to 32 bytes."""
    return __align(buffer, 32, pad_chr)


# Bit functions

def test_bit(val: int, flag: int) -> bool:
    return (val >> flag) & 1 == 1
