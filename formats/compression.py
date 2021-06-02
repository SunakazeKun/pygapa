import subprocess
from enum import IntEnum

from formats.helper import *


class JKRCompressionType(IntEnum):
    NONE = 0
    YAZ0 = 1
    YAY0 = 2
    ASR = 3


def decompress(buffer):
    # Magic is "Ya_0"
    if buffer[0] == 0x59 and buffer[1] == 0x61 and buffer[3] == 0x30:
        # Yaz0
        if buffer[2] == 0x7A:
            return decompress_szs(buffer, False)
        # Yay0
        elif buffer[2] == 0x79:
            return decompress_szp(buffer, False)
    # Magic is "ASR"
    elif buffer[0] == 0x41 and buffer[1] == 0x53 and buffer[2] == 0x52:
        raise Exception("ASR compression is not supported")
    return buffer


def decompress_szs(buf, check: True):
    if check and get_magic4(buf) != "Yaz0":
        return buf

    len_in = len(buf)
    len_out = get_s32(buf, 0x4)
    buf_out = bytearray(len_out)

    off_in = 16  # Compressed data comes after header
    off_out = 0

    while off_out < len_out:
        block = buf[off_in]
        off_in += 1

        for _ in range(8):
            # Read plain byte
            if block & 0x80:
                buf_out[off_out] = buf[off_in]
                off_in += 1
                off_out += 1
            # Read and copy decompressed data
            else:
                # Read tokens
                b1 = buf[off_in]
                b2 = buf[off_in + 1]
                off_in += 2

                # Get copy offset and size
                dist = ((b1 & 0xF) << 8) | b2
                off_copy = off_out - dist - 1
                len_copy = b1 >> 4

                if len_copy == 0:
                    len_copy = buf[off_in] + 0x12
                    off_in += 1
                else:
                    len_copy += 2

                for i in range(len_copy):
                    buf_out[off_out] = buf_out[off_copy]
                    off_out += 1
                    off_copy += 1

            block <<= 1

            if off_out >= len_out or off_in >= len_in:
                break

    return buf_out


def decompress_szp(buf, check: True):
    raise Exception("SZP compression is not supported")


def try_compress_szs_external(file_path: str, buffer):
    if file_path.find("/") != -1:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

    try:
        write_file(file_path, buffer)

        subprocess.run(["yaz0enc", file_path])

        os.remove(file_path)
        os.rename(file_path + ".yaz0", file_path)
    except subprocess.CalledProcessError:
        print("Couldn't compress the file. Does yaz0enc exist?")

