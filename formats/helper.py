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
def __read_string(chset: str, buffer, offset: int = 0) -> str:
    end = offset
    while end < len(buffer) - 1 and buffer[end] != 0:
        end += 1
    return buffer[offset:end + 1].decode(chset).strip("\0")


def __pack_string(chset: str, val: str) -> bytes:
    if not val.endswith("\0"):
        val += "\0"
    return val.encode(chset)


def read_ascii_string(buffer, offset: int = 0) -> str:
    """Decodes and returns the ASCII string at the buffer's specified offset."""
    return __read_string("ascii", buffer, offset)


def pack_ascii_string(val: str) -> bytes:
    """Encodes the string using ASCII and returns the packed bytes. Null-terminates the string if necessary"""
    return __pack_string("ascii", val)


def read_sjis_string(buffer, offset: int) -> str:
    """Decodes and returns the SJIS string at the buffer's specified offset."""
    return __read_string("shift_jisx0213", buffer, offset)


def pack_sjis_string(val: str) -> bytes:
    """Encodes the string using SJIS and returns the packed bytes. Null-terminates the string if necessary"""
    return __pack_string("shift_jisx0213", val)


def get_filename(val: str) -> str:
    """Extracts the filename without extension from the specified file path."""
    return os.path.splitext(os.path.basename(val))[0]


# File I/O functions

def read_file(fp) -> bytearray:
    """Reads the binary data from the specified file and returns it as a bytearray."""
    with open(fp, "rb") as f:
        ret = f.read()
    return bytearray(ret)


def write_file(fp, buf):
    """Writes the contents of a bytes-like object to the specified file."""
    with open(fp, "wb") as f:
        f.write(buf)
        f.flush()


def read_json_file(fp):
    """Reads the JSON data from the specified file using UTF-8 encoding."""
    with open(fp, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def write_json_file(fp: str, data):
    """Writes the JSON data to the specified file using UTF-8 encoding."""
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.flush()


# Buffer alignment functions

def __align(buffer, size, padchr):
    """Returns the padding bytes required to align the buffer to the specified size."""
    padlen = len(buffer) & (size - 1)
    if padlen != 0:
        return bytearray([ord(padchr)] * (size - padlen))
    return bytearray()


def align4(buffer, padchr="\0"):
    """Returns the padding bytes required to align the specified buffer to 4 bytes."""
    return __align(buffer, 4, padchr)


def align8(buffer, padchr="\0"):
    """Returns the padding bytes required to align the specified buffer to 8 bytes."""
    return __align(buffer, 8, padchr)


def align16(buffer, padchr="\0"):
    """Returns the padding bytes required to align the specified buffer to 16 bytes."""
    return __align(buffer, 16, padchr)


def align32(buffer, padchr="\0"):
    """Returns the padding bytes required to align the specified buffer to 32 bytes."""
    return __align(buffer, 32, padchr)
