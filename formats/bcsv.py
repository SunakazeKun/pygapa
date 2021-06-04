import struct
from enum import IntEnum

from formats import helper, mrhash


class JMapFieldType(IntEnum):
    LONG = 0
    # According to noclip.website, type 1 is a non-SJIS string, however, couldn't find anything in SMG1/2 about it yet.
    # It is possible that this type is only found in Luigi's Mansion and/or Donkey Kong Jungle Beat, two GameCube games
    # that also use the JMap library.
    FLOAT = 2
    UNSIGNED_LONG = 3
    SHORT = 4
    UNSIGNED_CHAR = 5
    STRING = 6

    def size(self):
        """
        Returns the entry size for this field type. All field types occupy 4 bytes, but SHORT and UNSIGNED_CHAR use 2
        and 1 byte(s), respectively.
        """
        if self == self.SHORT:
            return 2
        elif self == self.UNSIGNED_CHAR:
            return 1
        return 4

    def mask(self):
        """
        Returns the entry mask for this field type. All field types use a 32-bit mask, but SHORT uses a 16-bit mask and
        UNSIGNED_CHAR uses an 8-bit mask.
        """
        if self == self.SHORT:
            return 0xFFFF
        elif self == self.UNSIGNED_CHAR:
            return 0xFF
        return 0xFFFFFFFF


class JMapField:
    def __init__(self, field_hash: int, mask: int, offset: int, shift: int, field_type: JMapFieldType, field_name: str):
        self.hash = field_hash
        self.mask = mask
        self.offset = offset
        self.shift = shift
        self.type = field_type
        self.name = field_name

    def __str__(self):
        return self.name

    def __len__(self):
        return self.type.size()


class JMapInfo:
    def __init__(self):
        self.fields = dict()
        self.entries = list()

    def new_field(self, field_name, field_type: JMapFieldType, shift: int = 0):
        # Does a field with that name exist already?
        if field_name in self.fields:
            raise Exception(f"Field {field_name} already exists!")

        # Create new field
        field_hash = mrhash.calc_hash(field_name)
        mask = field_type.mask()
        self.fields[field_name] = JMapField(field_hash, mask, -1, shift, field_type, field_name)

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
            field_name = mrhash.find_name(field_hash)

            self.fields[field_name] = JMapField(field_hash, mask, entry_offset, shift, field_type, field_name)

        # Read entries
        for i in range(num_entries):
            entry = dict()

            for f in self.fields.values():
                offset = off_data + i * len_data_entry + f.offset
                val = None

                # Read long
                if f.type == JMapFieldType.LONG:
                    val = (helper.get_s32(buffer, offset) & f.mask) >> f.shift

                    # Make signed int
                    if val & 0x80000000:
                        val |= ~0xFFFFFFFF
                # Read float
                elif f.type == JMapFieldType.FLOAT:
                    val = round(helper.get_f32(buffer, offset), 7)
                # Read unsigned long
                elif f.type == JMapFieldType.UNSIGNED_LONG:
                    val = (helper.get_u32(buffer, offset) & f.mask) >> f.shift
                # Read short
                elif f.type == JMapFieldType.SHORT:
                    val = (helper.get_s16(buffer, offset) & f.mask) >> f.shift

                    # Make signed short
                    if val & 0x8000:
                        val |= ~0xFFFF
                # Read unsigned char
                elif f.type == JMapFieldType.UNSIGNED_CHAR:
                    val = (buffer[offset] & f.mask) >> f.shift
                # Read string
                elif f.type == JMapFieldType.STRING:
                    off_string = off_strings + helper.get_s32(buffer, offset)
                    val = helper.read_sjis(buffer, off_string)

                entry[f.name] = val

            self.entries.append(entry)

    def pack(self, sort_by_field: str = None):
        # Sort entries by field name if specified
        if sort_by_field is not None:
            entries = sorted(self.entries, key=lambda k: k[sort_by_field])
        else:
            entries = self.entries

        # Fetch information about the contents and allocate output buffer
        num_entries = len(self.entries)
        num_fields = len(self.fields)
        off_data = 0x10 + num_fields * 0xC

        buf_out = bytearray(off_data)

        # Calculate entry length, fix field offsets and pack fields
        len_data_entry = 0
        off_field = 0x10

        for field in self.fields.values():
            len_field = len(field)

            # Calculate aligned entry offset
            if len_field & 1 == 0:  # even field size?
                len_data_entry = (len_data_entry + 1) & ~(len_field - 1)

            field.offset = len_data_entry  # Fix offset
            len_data_entry += len_field

            struct.pack_into(">2IH2B", buf_out, off_field, field.hash, field.mask, field.offset, field.shift, field.type)
            off_field += 0xC

        # Align entry size to 4 bytes
        len_data_entry = (len_data_entry + 1) & ~3

        # Pack header
        struct.pack_into(">4i", buf_out, 0x0, num_entries, num_fields, off_data, len_data_entry)

        # Pack entries
        buf_out += bytearray(len_data_entry * num_entries)
        off_entry = off_data
        off_strings = len(buf_out)
        string_offsets = dict()

        for entry in entries:
            for field in self.fields.values():
                off_val = off_entry + field.offset
                val = entry[field.name]

                # Pack long or unsigned long
                if field.type == JMapFieldType.LONG or field.type == JMapFieldType.UNSIGNED_LONG:
                    struct.pack_into(">I", buf_out, off_val, (val << field.shift) & field.mask)
                # Pack float
                elif field.type == JMapFieldType.FLOAT:
                    struct.pack_into(">f", buf_out, off_val, val)
                # Pack short
                elif field.type == JMapFieldType.SHORT:
                    struct.pack_into(">H", buf_out, off_val, (val << field.shift) & field.mask)
                # Pack unsigned char
                elif field.type == JMapFieldType.UNSIGNED_CHAR:
                    buf_out[off_val] = (val << field.shift) & field.mask
                # Pack string
                elif field.type == JMapFieldType.STRING:
                    if val in string_offsets:
                        off_string = string_offsets[val]
                    else:
                        off_string = len(buf_out) - off_strings
                        string_offsets[val] = off_string
                        buf_out += helper.pack_sjis(val)
                    struct.pack_into(">i", buf_out, off_val, off_string)

            off_entry += len_data_entry

        # Align output buffer to 32 bytes
        buf_out += helper.align32(buf_out, "@")

        return buf_out
