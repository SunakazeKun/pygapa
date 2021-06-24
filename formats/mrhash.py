import os

from formats import helper

# MR is Super Mario Galaxy (2)'s namespace. I use this name to refer to the hashes found specifically in those games,
# because other games using BCSV and JMap, for example Luigi's Mansion, use a different hashing algorithm. MR likely
# stands for "Mario Revolution".

__MR_HASH_LOOKUP_TABLE = dict()  # For each known hash value, this table stores a field name.


def calc_hash(field_name: str) -> int:
    """
    Calculates and returns the MR hash for the specified field name string. The resulting hash is a 32-bit value. The
    string will be encoded using shift_jisx0213 just like all strings in SMG1/2 are. This is necessary to generate valid
    hashes for any string outside the default ASCII range.

    :param field_name: the string to calculate the hash on
    :returns: the 32-bit MR hash value
    """
    field_hash = 0
    for ch in field_name.encode("shift_jisx0213"):
        field_hash *= 31
        field_hash += helper.try_sign8(ch)
    return field_hash & 0xFFFFFFFF


def find_name(field_hash: int) -> str:
    """
    Attempts to retrieve a known and valid field name for the specified MR hash. If the hash is not found in the lookup
    table, it generates and returns a hexadecimal string representation of the hash. For example, if the hash value
    0xDEADBEEF could not be found, this function returns "[DEADBEEF]".

    :param field_hash: the MR hash to find the field name for
    :returns: the field name if it exists, otherwise a hexadecimal string representation
    """
    if field_hash in __MR_HASH_LOOKUP_TABLE:
        return __MR_HASH_LOOKUP_TABLE[field_hash]
    else:
        return f"[{field_hash:08X}]"


def add_name(field_name: str) -> int:
    """
    Calculates the MR hash for the specified field name string. The hash and known field name will be added to the hash
    lookup table. The hash will be returned as well.

    :param field_name: the string to calculate the hash on
    :returns: the 32-bit MR hash value
    """
    field_hash = calc_hash(field_name)
    __MR_HASH_LOOKUP_TABLE[field_hash] = field_name
    return field_hash


# We have to populate the table of known hashes and their field names first. The field names are specified in a file
# called "mrfields.txt". This file needs to be present in the same folder as this script.
__FIELD_NAMES_FILE = os.path.join(os.path.dirname(__file__), "mrfields.txt")

if os.path.exists(__FIELD_NAMES_FILE):
    for field in open(__FIELD_NAMES_FILE, "r", encoding="utf-8").readlines():
        field = field.strip("\n")
        __MR_HASH_LOOKUP_TABLE[calc_hash(field)] = field
else:
    print("Warning! Could not populate known field names as the file \"mrfields.txt\" does not exist.")

# The file path to "bcsvnames.txt" is not required anymore, so we delete it here
del __FIELD_NAMES_FILE
