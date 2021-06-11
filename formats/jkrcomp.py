import os
import subprocess
from platform import system
from enum import IntEnum
from shutil import which

from formats import helper


class JKRCompressionType(IntEnum):
    NONE = 0  # Use no compression at all
    SZS = 1  # The compression format used by SMG1/2's ARC files and some others
    SZP = 2  # Not used in SMG1/2, but decoding this format is still supported by the game
    ASR = 3  # Used by Home Menu stuff. Kept here for documentation purposes


def check_compressed(buffer) -> JKRCompressionType:
    """
    This function checks the first three to four magic bytes of the input buffer to determine what algorithm was used
    to compress the buffer. The supported magic values are:
    - ``Yaz0``: Buffer is encoded using SZS compression
    - ``Yay0``: Buffer is encoded using SZP compression
    - ``ASR``: Buffer is encoded using ASR compression

    This function then returns a JKRCompressionType value that describes the used compression format.

    :param buffer: buffer to be checked
    :returns: the JKRCompressionType describing the compression format
    """
    # Magic is "Ya_0"
    if buffer[0] == 0x59 and buffer[1] == 0x61 and buffer[3] == 0x30:
        # Yaz0 -> decompress SZS
        if buffer[2] == 0x7A:
            return JKRCompressionType.SZS
        # Yay0 -> decompress SZP
        elif buffer[2] == 0x79:
            return JKRCompressionType.SZP
    # Magic is "ASR"
    elif buffer[0] == 0x41 and buffer[1] == 0x53 and buffer[2] == 0x52:
        return JKRCompressionType.ASR

    return JKRCompressionType.NONE


def decompress(buffer):
    """
    Decompresses a buffer that is encoded in a JKR compression format and returns the decoded data in a separate buffer.
    First, this function checks the first three to four magic bytes to determine which compression format to use. See
    ``check_compressed`` for details on that matter.

    ASR decompression is not implemented here since it is kept only for documentation purposes. Therefore, any attempt
    at decompressing an ASR-encoded buffer will yield a ``NotImplementedError``.

    If no JKR compression identifier was found, the input buffer is returned.

    :param buffer: buffer to be decompressed
    :returns: a buffer containing decompressed data or the input buffer if no compressed data was found.
    :raises NotImplementedError: raised on any attempt at decoding ASR data
    """
    compression_type = check_compressed(buffer)

    if compression_type == JKRCompressionType.SZS:
        return decompress_szs(buffer, False)
    elif compression_type == JKRCompressionType.SZP:
        return decompress_szp(buffer, False)
    elif compression_type == JKRCompressionType.ASR:
        raise NotImplementedError("ASR decompression is not supported.")

    # Return the input buffer if it does not contain compressed data
    return buffer


def decompress_szs(buffer, check: bool = True) -> bytearray:
    """
    Decompresses an SZS-encoded buffer and returns the decoded data in a separate bytearray buffer. If check is enabled,
    this function checks if the magic bytes are equal to "Yaz0" to ensure the buffer contains SZS data. The input buffer
    is returned in case this check fails. However, if this option is disabled, the decompression is forced. Checking
    should only be disabled when it is ensured that the buffer contains SZS-encoded data.

    :param buffer: buffer to be decompressed
    :param check: declares whether to check the magic bytes first (True) or force the decompression (False)
    :returns: a bytearray containing the decompressed data or the input buffer if no compressed data was found.
    """
    if check and helper.get_magic4(buffer) != "Yaz0":
        return buffer

    # Get decompressed size and prepare output buffer
    len_out = helper.get_s32(buffer, 0x4)
    buf_out = bytearray(len_out)

    off_in = 16  # Compressed data comes after header
    off_out = 0

    block = 0  # The control block that describes how to decompress data, 8-bit
    counter = 0  # Keeps track of the remaining bits to be checked for the current control block

    while off_out < len_out:
        # Get control block, which is a byte describing how to decompress data from the input buffer. The bits are read
        # starting from the most significant bit. If the bit is set, we copy the next byte. Otherwise, we read the next
        # two bytes that determine which decompressed bytes to copy into the output buffer.
        if counter == 0:
            block = buffer[off_in]
            counter = 8
            off_in += 1

        # Is the most significant bit set? If so, copy a plain byte into the output buffer.
        if block & 0x80:
            buf_out[off_out] = buffer[off_in]
            off_in += 1
            off_out += 1
        # Otherwise, read and copy decompressed data.
        else:
            # Read tokens
            b1 = buffer[off_in]
            b2 = buffer[off_in + 1]
            off_in += 2

            # Get copy offset and size
            dist = ((b1 & 0xF) << 8) | b2
            off_copy = off_out - dist - 1
            len_copy = b1 >> 4

            # Copy 18+ bytes?
            if len_copy == 0:
                len_copy = buffer[off_in] + 18
                off_in += 1
            # Copy up to 17 bytes
            else:
                len_copy += 2

            # Copy the actual data
            for _ in range(len_copy):
                buf_out[off_out] = buf_out[off_copy]
                off_out += 1
                off_copy += 1

        # Left-shift control block and decrement remaining bits to be checked
        block <<= 1
        counter -= 1

    return buf_out


def decompress_szp(buffer, check: bool = True) -> bytearray:
    """
    Decompresses an SZP-encoded buffer and returns the decoded data in a separate bytearray buffer. If check is enabled,
    this function checks if the magic bytes are equal to "Yay0" to ensure the buffer contains SZP data. The input buffer
    is returned in case this check fails. However, if this option is disabled, the decompression is forced. Checking
    should only be disabled when it is ensured that the buffer contains SZP-encoded data.

    :param buffer: buffer to be decompressed
    :param check: declares whether to check the magic bytes first (True) or force the decompression (False)
    :returns: a bytearray containing the decompressed data or the input buffer if no compressed data was found.
    """
    if check and helper.get_magic4(buffer) != "Yay0":
        return buffer

    # Parse header and prepare output buffer
    len_out, off_copy_table, off_chunks = helper.struct.unpack_from(">3I", buffer, 0x4)
    buf_out = bytearray(len_out)

    off_in = 16  # Compressed data comes after header
    off_out = 0

    block = 0  # The control block that describes how to decompress data, 32-bit
    counter = 0  # Keeps track of the remaining bits to be checked for the current control block

    while off_out < len_out:
        # Get control block, which is a 32-bit word describing how to decompress data from the input buffer. Like SZS,
        # the bits are read starting from the most significant bit. If the bit is set, we copy the next byte in the byte
        # chunk table. Otherwise, we read information from the copy table to determine which decompressed bytes to copy
        # into the output buffer.
        if counter == 0:
            block = helper.get_u32(buffer, off_in)
            counter = 32
            off_in += 4

        # Is the most significant bit set? If so, copy a plain byte into the output buffer.
        if block & 0x80000000:
            buf_out[off_out] = buffer[off_chunks]
            off_chunks += 1
            off_out += 1
        # Otherwise, read and copy decompressed data.
        else:
            # Read tokens
            b1 = buffer[off_copy_table]
            b2 = buffer[off_copy_table + 1]
            off_copy_table += 2

            # Get copy offset and size
            dist = ((b1 & 0xF) << 8) | b2
            off_copy = off_out - dist - 1
            len_copy = b1 >> 4

            # Copy 18+ bytes?
            if len_copy == 0:
                len_copy = buffer[off_chunks] + 18
                off_chunks += 1
            # Copy up to 17 bytes
            else:
                len_copy += 2

            # Copy the actual data
            for _ in range(len_copy):
                buf_out[off_out] = buf_out[off_copy]
                off_out += 1
                off_copy += 1

        # Left-shift control block and decrement remaining bits to be checked
        block <<= 1
        counter -= 1

    return buf_out


def write_file_try_szs_external(file_path: str, buffer, compression_level: str = "ULTRA") -> bool:
    """
    Writes the buffer's contents to the specified file (see ``helper.write_file``). Using third-party tools, this will
    attempt to encode the file using the SZS compression format. If the file was successfully compressed, this function
    returns True, otherwise False.
    First, it will attempt to use Wiimm's SZS Tool (WSZST) to compress the file using the specified compression level.
    If the tool fails, for example when it cannot be found on the system at all, and if the user is running on a Windows
    system, it will try to use yaz0enc to compress the file. WSZST has a higher priority since it is more efficient,
    both in terms of compression rate and speed.

    :param file_path: file to write the buffer into
    :param buffer: buffer to be exported
    :param compression_level: WSZST compression level to be used, default is 10 (best)
    :returns: True if compression was successful, False if compression failed
    """
    # Write buffered data to file, then we try to apply external SZS compressors on it
    helper.write_file(file_path, buffer)

    # Try to compress with WSZST if it exists in PATH
    if which("wszst") is not None:
        try:
            # Run wszst with the specified compression level
            subprocess.run(["wszst", "compress", file_path, "--compr", compression_level])

            return True
        except subprocess.CalledProcessError:
            print("Couldn't compress the file using wszst.")

    # Try to compress with yaz0enc if WSZST failed and if running on a Windows OS
    if system() == "Windows" and os.path.exists("yaz0enc.exe"):
        try:
            # Run yaz0enc on the file
            subprocess.run(["yaz0enc", file_path])

            # Remove *.arc file
            os.remove(file_path)

            # Rename *.arc.yaz0 file to *.arc
            os.rename(file_path + ".yaz0", file_path)

            return True
        except subprocess.CalledProcessError:
            print("Couldn't compress the file using yaz0enc.")

    return False
