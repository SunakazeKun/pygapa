from helper import *

# Hash and field name helpers
HASHED_FIELD_NAMES = dict()
__FIELD_NAMES = [
    "name", "id", "No", "GroupName", "AnimName", "ContinueAnimEnd", "UniqueName", "EffectName", "ParentName",
    "JointName", "OffsetX", "OffsetY", "OffsetZ", "StartFrame", "EndFrame", "Affect", "Follow", "ScaleValue",
    "RateValue", "PrmColor", "EnvColor", "LightAffectValue", "DrawOrder"
]


def field_name_to_hash(fname: str) -> int:
    fhash = 0
    for c in fname:
        fhash *= 31
        fhash += ord(c)
    return fhash & 0xFFFFFFFF


def hash_to_field_name(fhash: int) -> str:
    if fhash in HASHED_FIELD_NAMES:
        return HASHED_FIELD_NAMES[fhash]
    else:
        return f"[{fhash:08X}]"


# Populate hashed field names
for field in __FIELD_NAMES:
    HASHED_FIELD_NAMES[field_name_to_hash(field)] = field


# Field type identifiers
FIELD_TYPE_S32 = 0
FIELD_TYPE_F32 = 2
FIELD_TYPE_S32_2 = 3
FIELD_TYPE_S16 = 4
FIELD_TYPE_U8 = 5
FIELD_TYPE_STRING = 6
FIELD_SIZES = [4, -1, 4, 4, 2, 1, 4]


def is_valid_field(ftype: int):
    if ftype == 1 or ftype < FIELD_TYPE_S32 or ftype > FIELD_TYPE_STRING:
        raise Exception(f"Unknown field type 0x{ftype:02X}")


class Field:
    def __init__(self, fhash, mask, offset, shift, ftype, name):
        self.hash = fhash
        self.mask = mask
        self.offset = offset
        self.shift = shift
        self.type = ftype
        self.name = name


class Bcsv:
    def __init__(self):
        self.fields = dict()
        self.entries = list()

    def new_field(self, fname, ftype):
        is_valid_field(ftype)

        if fname in self.fields:
            raise Exception(f"Field {fname} already exists!")

        if ftype == FIELD_TYPE_S16:
            mask = 0xFFFF
        elif ftype == FIELD_TYPE_U8:
            mask = 0xFF
        else:
            mask = 0xFFFFFFFF

        offset = 0
        for f in self.fields.values():
            offset += FIELD_SIZES[f.type]

        self.fields[fname] = Field(field_name_to_hash(fname), mask, offset, 0, ftype, fname)

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

            fhash, mask, entry_offset, shift, ftype = struct.unpack_from(">IIHBB", buffer, off_field)
            is_valid_field(ftype)
            fname = hash_to_field_name(fhash)

            self.fields[fname] = Field(fhash, mask, entry_offset, shift, ftype, fname)

        # Read entries
        for i in range(num_entries):
            entry = dict()

            for f in self.fields.values():
                offset = off_data + i * len_data_entry + f.offset
                val = None

                if f.type == FIELD_TYPE_S32 or f.type == FIELD_TYPE_S32_2:
                    val = (get_s32(buffer, offset) & f.mask) >> f.shift

                    if val & (1 << 31) != 0:  # make signed int
                        val |= ~0xFFFFFFFF
                elif f.type == FIELD_TYPE_F32:
                    val = round(get_f32(buffer, offset), 7)
                elif f.type == FIELD_TYPE_S16:
                    val = (get_s16(buffer, offset) & f.mask) >> f.shift

                    if val & (1 << 15) != 0:  # make signed short
                        val |= ~0xFFFF
                elif f.type == FIELD_TYPE_U8:
                    val = (get_u8(buffer, offset) & f.mask) >> f.shift
                elif f.type == FIELD_TYPE_STRING:
                    off_string = off_strings + get_s32(buffer, offset)
                    val = read_sjis_string(buffer, off_string)

                entry[f.name] = val

            self.entries.append(entry)

    def pack(self, sort_by_field: str = None) -> bytearray:
        buf_out = bytearray()

        # Sort entries by field if specified
        if sort_by_field is not None:
            entries = sorted(self.entries, key=lambda k: k[sort_by_field])
        else:
            entries = self.entries

        # Pack fields and calculate entry length
        len_data_entry = 0

        for f in self.fields.values():
            is_valid_field(f.type)
            len_data_entry += FIELD_SIZES[f.type]

            buf_out += struct.pack(">IIHBB", f.hash, f.mask, f.offset, f.shift, f.type)

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
                        buf_strings += pack_sjis_string(val)
                    buf_out += struct.pack(">i", off)

        # Join output with strings and align to 32 bytes
        buf_out += buf_strings
        buf_out += align32(buf_out, "@")
        return buf_out
