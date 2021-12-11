import enum
import json
import os
import struct


# ----------------------------------------------------------------------------------------------------------------------
# Indexed enumeration type
# ----------------------------------------------------------------------------------------------------------------------
class ExtIntEnumMeta(enum.EnumMeta):
    def __call__(cls, value, **kwargs):
        if cls._value2member_map_ and type(value) == int:
            for k, v in cls._value2member_map_.items():
                if k[0] == value:
                    return v
        else:
            super(ExtIntEnumMeta, cls).__call__(value, kwargs)


class ExtIntEnum(enum.Enum, metaclass=ExtIntEnumMeta):
    def __int__(self):
        return self.index


# ----------------------------------------------------------------------------------------------------------------------
# String helpers
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
# String pool writer
# ----------------------------------------------------------------------------------------------------------------------
class StringPoolFormat(enum.IntEnum):
    NOT_TERMINATED = 0
    NULL_TERMINATED = 1


class StringPool:
    def __init__(self, encoding: str = "ascii", format: StringPoolFormat = StringPoolFormat.NULL_TERMINATED):
        self._encoding_ = encoding
        self._format_ = format
        self._buffer_ = bytearray()
        self._offsets_ = dict()
        self._lookup_ = True

    def _pack_string_(self, string: str):
        if self._format_ == StringPoolFormat.NULL_TERMINATED:
            string += "\0"
        return string.encode(self._encoding_)

    def write(self, string: str) -> int:
        if self._lookup_ and string in self._offsets_:
            offset = self._offsets_[string]
        else:
            offset = len(self._buffer_)
            self._offsets_[string] = offset
            self._buffer_ += self._pack_string_(string)
        return offset

    def find(self, string: str) -> int:
        if string in self._offsets_:
            return self._offsets_[string]
        else:
            return -1

    def toggle_lookup(self):
        self._lookup_ = not self._lookup_

    def align32(self):
        pad_len = len(self._buffer_) & 31

        if pad_len != 0:
            self._buffer_.extend(bytearray(32 - pad_len))

    def get_bytes(self):
        return bytes(self._buffer_)

    def __len__(self):
        return len(self._buffer_)


# ----------------------------------------------------------------------------------------------------------------------
# Binary helpers
# ----------------------------------------------------------------------------------------------------------------------
def alignsize32(val: int) -> int:
    a = val & 31
    if a:
        return val + (32 - a)
    return val


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


# ----------------------------------------------------------------------------------------------------------------------
# ByteBuffer
# ----------------------------------------------------------------------------------------------------------------------
class ByteBuffer(bytearray):
    @staticmethod
    def __try_struct(structure) -> struct.Struct:
        if structure is None:
            raise ValueError("Structure not specified!")

        if type(structure) == str:
            structure = struct.Struct(structure)
        elif type(structure) != struct.Struct:
            raise ValueError("Invalid structure provided!")

        return structure

    def __init__(self, *args, **kwargs):
        super(ByteBuffer, self).__init__(*args, *kwargs)
        self._position_ = 0

    def _try_set_position_(self, pos: int) -> None:
        if 0 <= pos:
            self._position_ = pos
        else:
            raise ValueError("Index out of bounds")

    def get_position(self) -> int:
        return self._position_

    def set_position(self, index: int) -> None:
        self._try_set_position_(index)

    def skip(self, val: int):
        self._try_set_position_(self._position_ + val)

    def read(self, structure):
        structure = ByteBuffer.__try_struct(structure)
        ret = structure.unpack_from(self, self._position_)
        self._position_ += structure.size
        return ret

    def read_from(self, structure, offset: int):
        self._try_set_position_(offset)
        return self.read(structure)

    def write(self, structure, *values):
        structure = ByteBuffer.__try_struct(structure)

        # Extend the buffer if necessary
        end_pos = self._position_ + structure.size
        total_size = len(self)

        if end_pos > total_size:
            self.extend(bytearray(end_pos - total_size))

        structure.pack_into(self, self._position_, *values)
        self._position_ = end_pos

    def write_into(self, structure, offset: int, *values):
        self._try_set_position_(offset)
        self.write(structure, *values)

    def _align_(self, size, pad_chr):
        pad_len = len(self) & (size - 1)
        pad_chr = ord(pad_chr)

        if pad_len != 0:
            self.extend([pad_chr] * (size - pad_len))

    def align4(self, pad_chr="\0"):
        """
        Aligns the buffer to 4 bytes if necessary.

        :param pad_chr: ASCII character to pad aligned space with
        """
        self._align_(4, pad_chr)

    def align8(self, pad_chr="\0"):
        """
        Aligns the buffer to 8 bytes if necessary.

        :param pad_chr: ASCII character to pad aligned space with
        """
        self._align_(8, pad_chr)

    def align16(self, pad_chr="\0"):
        """
        Aligns the buffer to 16 bytes if necessary.

        :param pad_chr: ASCII character to pad aligned space with
        """
        self._align_(16, pad_chr)

    def align32(self, pad_chr="\0"):
        """
        Aligns the buffer to 32 bytes if necessary.

        :param pad_chr: ASCII character to pad aligned space with
        """
        self._align_(32, pad_chr)


# ----------------------------------------------------------------------------------------------------------------------
# File helpers
# ----------------------------------------------------------------------------------------------------------------------
def get_filename(file_path: str) -> str:
    """
    Extracts the filename without extension from the specified file path.

    :param file_path: the file path to extract the basename from
    :returns: basename of the specified path without extension
    """
    return os.path.splitext(os.path.basename(file_path))[0]


def read_bin_file(file_path: str) -> ByteBuffer:
    """
    Reads the binary data from the specified file and returns the contents as a bytearray.

    :param file_path: the file path to read the contents from
    :returns: a bytebuffer containing the file's contents
    """
    with open(file_path, "rb") as f:
        ret = f.read()
    return ByteBuffer(ret)


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
# Deprecated, to be removed
# ----------------------------------------------------------------------------------------------------------------------
def __align(buffer, size, pad_chr):
    pad_len = len(buffer) & (size - 1)
    pad_chr = ord(pad_chr)
    if pad_len != 0:
        return bytearray([pad_chr] * (size - pad_len))
    return bytearray()


def align4(buffer, pad_chr="\0"):
    """
    Generate the padding bytes required to align the specified buffer to 4 bytes. The returned buffer consists of 0 to
    3 bytes, depending on the input buffer's current size. NULL (0) is used to pad out the space, but the padding char
    can be specified.

    :param buffer: the buffer to generate the alignment for
    :param pad_chr: ASCII character to pad aligned space with
    :returns: bytearray containing alignment padding
    """
    return __align(buffer, 4, pad_chr)


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
