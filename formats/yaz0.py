from formats.helper import *


def decompress(buf) -> bytearray:
    if get_magic4(buf) != "Yaz0":
        return buf

    len_in = len(buf)
    len_out = get_s32(buf, 0x4)
    buf_out = bytearray(len_out)

    off_in = 16  # Compressed data comes after header
    off_out = 0

    while off_out < len_out:
        block = get_u8(buf, off_in)
        off_in += 1

        for fi in range(8):
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
