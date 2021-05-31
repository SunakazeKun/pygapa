from formats.helper import *

# Hash and field name helpers
HASHED_FIELD_NAMES = dict()


def field_name_to_hash(field_name: str) -> int:
    """Calculates the 32-bit lookup hash for the specified SJIS field name string."""
    field_hash = 0
    for ch in field_name.encode("shift_jisx0213"):
        field_hash *= 31
        field_hash += ch
    return field_hash & 0xFFFFFFFF


def hash_to_field_name(field_hash: int) -> str:
    """Attempts to retrieve a known and valid field name for the specified field hash."""
    if field_hash in HASHED_FIELD_NAMES:
        return HASHED_FIELD_NAMES[field_hash]
    else:
        return f"[{field_hash:08X}]"


# Populate known field names and their hashes
__FIELD_NAMES = [
    "name", "id", "No", "GroupName", "AnimName", "ContinueAnimEnd", "UniqueName", "EffectName", "ParentName",
    "JointName", "OffsetX", "OffsetY", "OffsetZ", "StartFrame", "EndFrame", "Affect", "Follow", "ScaleValue",
    "RateValue", "PrmColor", "EnvColor", "LightAffectValue", "DrawOrder"
]

for field in __FIELD_NAMES:
    HASHED_FIELD_NAMES[field_name_to_hash(field)] = field

# We don't need the list of field names anymore
__FIELD_NAMES.clear()
del __FIELD_NAMES


# Field type identifiers
FIELD_TYPE_S32 = 0
FIELD_TYPE_F32 = 2
FIELD_TYPE_S32_2 = 3
FIELD_TYPE_S16 = 4
FIELD_TYPE_U8 = 5
FIELD_TYPE_STRING = 6
FIELD_SIZES = [4, -1, 4, 4, 2, 1, 4]
FIELD_MASKS = [0xFFFFFFFF, -1, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFF, 0xFF, 0xFFFFFFFF]


def is_valid_field(field_type: int):
    if field_type == 1 or field_type < FIELD_TYPE_S32 or field_type > FIELD_TYPE_STRING:
        raise Exception(f"Unknown field type 0x{field_type:02X}")


class Field:
    def __init__(self, field_hash, mask, offset, shift, field_type, field_name):
        self.hash = field_hash
        self.mask = mask
        self.offset = offset
        self.shift = shift
        self.type = field_type
        self.name = field_name


class Bcsv:
    def __init__(self):
        self.fields = dict()
        self.entries = list()

    def new_field(self, field_name, field_type):
        # Does a field with that name exist already?
        if field_name in self.fields:
            raise Exception(f"Field {field_name} already exists!")

        is_valid_field(field_type)

        # Create new field
        field_hash = field_name_to_hash(field_name)
        mask = FIELD_MASKS[field_type]
        self.fields[field_name] = Field(field_hash, mask, -1, 0, field_type, field_name)

    def unpack(self, buffer, offset: int = 0):
        self.fields.clear()
        self.entries.clear()

        # Read header and calculate offsets
        num_entries, num_fields, off_data, len_data_entry = struct.unpack_from(">4i", buffer, offset)
        off_data += offset
        off_strings = off_data + (num_entries * len_data_entry)

        # Read fields
        for i in range(num_fields):
            off_field = offset + 0x10 + i * 0xC

            field_hash, mask, entry_offset, shift, field_type = struct.unpack_from(">IIHBB", buffer, off_field)
            is_valid_field(field_type)
            field_name = hash_to_field_name(field_hash)

            self.fields[field_name] = Field(field_hash, mask, entry_offset, shift, field_type, field_name)

        # Read entries
        for i in range(num_entries):
            entry = dict()

            for f in self.fields.values():
                offset = off_data + i * len_data_entry + f.offset
                val = None

                if f.type == FIELD_TYPE_S32 or f.type == FIELD_TYPE_S32_2:
                    val = (get_s32(buffer, offset) & f.mask) >> f.shift

                    # Make signed int
                    if val & (1 << 31) != 0:
                        val |= ~0xFFFFFFFF
                elif f.type == FIELD_TYPE_F32:
                    val = round(get_f32(buffer, offset), 7)
                elif f.type == FIELD_TYPE_S16:
                    val = (get_s16(buffer, offset) & f.mask) >> f.shift

                    # Make signed short
                    if val & (1 << 15) != 0:
                        val |= ~0xFFFF
                elif f.type == FIELD_TYPE_U8:
                    val = (get_u8(buffer, offset) & f.mask) >> f.shift
                elif f.type == FIELD_TYPE_STRING:
                    off_string = off_strings + get_s32(buffer, offset)
                    val = read_sjis(buffer, off_string)

                entry[f.name] = val

            self.entries.append(entry)

    def pack(self, sort_by_field: str = None):
        buf_out = bytearray()

        # Sort entries by field if specified
        if sort_by_field is not None:
            entries = sorted(self.entries, key=lambda k: k[sort_by_field])
        else:
            entries = self.entries

        # Pack fields and calculate entry length
        len_data_entry = 0

        for f in self.fields.values():
            f.offset = len_data_entry  # Fix offset
            len_data_entry += FIELD_SIZES[f.type]

            buf_out += struct.pack(">IIHBB", f.hash, f.mask, f.offset, f.shift, f.type)

        # Align entry length to 4 bytes
        len_data_entry = (len_data_entry + 1) & ~3

        # Write header and calculate data offset
        num_entries = len(self.entries)
        num_fields = len(self.fields)
        off_data = 0x10 + num_fields * 0xC

        buf_out = struct.pack(">4i", num_entries, num_fields, off_data, len_data_entry) + buf_out

        # Pack entries
        buf_strings = bytearray()
        string_offsets = dict()

        for entry in entries:
            for ffield in sorted(self.fields.values(), key=lambda k: k.offset):
                val = entry[ffield.name]

                if ffield.type == FIELD_TYPE_S32 or ffield.type == FIELD_TYPE_S32_2:
                    buf_out += pack_u32((val << ffield.shift) & ffield.mask)
                elif ffield.type == FIELD_TYPE_F32:
                    buf_out += pack_f32(val)
                elif ffield.type == FIELD_TYPE_S16:
                    buf_out += pack_u16((val << ffield.shift) & ffield.mask)
                elif ffield.type == FIELD_TYPE_U8:
                    buf_out += pack_u8((val << ffield.shift) & ffield.mask)
                elif ffield.type == FIELD_TYPE_STRING:
                    if val in string_offsets:
                        off = string_offsets[val]
                    else:
                        off = len(buf_strings)
                        string_offsets[val] = off
                        buf_strings += pack_sjis(val)
                    buf_out += struct.pack(">i", off)

            buf_out += align4(buf_out)

        # Join output and string pool and align it to 32 bytes
        buf_out += buf_strings
        buf_out += align32(buf_out, "@")
        return buf_out
