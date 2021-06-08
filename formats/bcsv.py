import struct
from enum import IntEnum

from formats import helper, mrhash


STRUCT_HEADER = struct.Struct(">4I")
STRUCT_FIELD = struct.Struct(">2IH2B")


class JMapFieldType(IntEnum):
    LONG = 0
    STRING = 1  # Not supported in SMG1/2, found in Luigi's Mansion and probably other games using JMapInfo
    FLOAT = 2
    LONG_2 = 3
    SHORT = 4
    CHAR = 5
    STRING_OFFSET = 6

    def __len__(self):
        """
        Returns the entry size for this field type. Usually, fields occupy 4 bytes, but STRING, SHORT and CHAR use 32, 2
        and 1 byte(s), respectively.
        """
        if self == self.STRING:
            return 32
        elif self == self.SHORT:
            return 2
        elif self == self.CHAR:
            return 1
        return 4

    def mask(self):
        """
        Returns the entry mask for this field type. All field types use a 32-bit mask, but STRING does not have one,
        SHORT uses a 16-bit mask and CHAR uses an 8-bit mask.
        """
        if self == self.STRING:
            return 0
        elif self == self.SHORT:
            return 0xFFFF
        elif self == self.CHAR:
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
        return 12


class JMapInfo:
    def __init__(self):
        self.fields = dict()
        self.entries = list()
        self.__entry_size = -1  # Negative number forces recalculation of this value and field offsets

    def new_field(self, field_name, field_type: JMapFieldType, shift: int = 0):
        # Does a field with that name exist already?
        if field_name in self.fields:
            raise Exception(f"Field {field_name} already exists!")

        # Create new field
        field_hash = mrhash.calc_hash(field_name)
        mask = field_type.mask()
        self.fields[field_name] = JMapField(field_hash, mask, -1, shift, field_type, field_name)

        # Clear entry size
        self.__entry_size = -1

    def drop_field(self, field_name):
        self.fields.pop(field_name)

        for entry in self.entries:
            entry.pop(field_name)

        self.__entry_size = -1

    def unpack(self, buffer, offset: int = 0):
        self.fields.clear()
        self.entries.clear()

        # Read header and calculate offsets
        num_entries, num_fields, off_data, self.__entry_size = STRUCT_HEADER.unpack_from(buffer, offset)
        off_data += offset
        off_strings = off_data + (num_entries * self.__entry_size)

        # Read fields
        for i in range(num_fields):
            off_field = offset + 0x10 + i * 0xC

            field_hash, mask, entry_offset, shift, field_type = STRUCT_FIELD.unpack_from(buffer, off_field)
            field_type = JMapFieldType(field_type)
            field_name = mrhash.find_name(field_hash)

            self.fields[field_name] = JMapField(field_hash, mask, entry_offset, shift, field_type, field_name)

        # Read entries
        for i in range(num_entries):
            entry = dict()

            for f in self.fields.values():
                offset = off_data + i * self.__entry_size + f.offset
                val = None

                # Read long
                if f.type == JMapFieldType.LONG or f.type == JMapFieldType.LONG_2:
                    val = (helper.get_u32(buffer, offset) & f.mask) >> f.shift

                    # Make signed int
                    if val & 0x80000000:
                        val |= ~0xFFFFFFFF
                # Read string
                elif f.type == JMapFieldType.STRING:
                    val = helper.read_fixed_string(buffer, offset, 0x20, "shift_jisx0213")
                # Read float
                elif f.type == JMapFieldType.FLOAT:
                    val = round(helper.get_f32(buffer, offset), 7)
                # Read short
                elif f.type == JMapFieldType.SHORT:
                    val = (helper.get_u16(buffer, offset) & f.mask) >> f.shift

                    # Make signed short
                    if val & 0x8000:
                        val |= ~0xFFFF
                # Read char
                elif f.type == JMapFieldType.CHAR:
                    val = (buffer[offset] & f.mask) >> f.shift

                    # Make signed char
                    if val & 0x80:
                        val |= ~0xFF
                # Read string at offset
                elif f.type == JMapFieldType.STRING_OFFSET:
                    off_string = off_strings + helper.get_u32(buffer, offset)
                    val = helper.read_string(buffer, off_string, "shift_jisx0213")

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

        # Recalculate entry size and pack all fields
        if self.__entry_size < 0:
            len_data_entry = 0
            off_field = 0x10

            for field in self.fields.values():
                field_type = field.type

                # Calculate aligned entry offset
                if field_type <= JMapFieldType.LONG_2 or field_type >= JMapFieldType.STRING_OFFSET:
                    len_data_entry = (len_data_entry + 1) & ~3
                elif field_type == JMapFieldType.SHORT:
                    len_data_entry = (len_data_entry + 1) & ~1

                field.offset = len_data_entry  # Fix offset
                len_data_entry += len(field_type)

                STRUCT_FIELD.pack_into(buf_out, off_field, field.hash, field.mask, field.offset, field.shift, field_type)
                off_field += 0xC

            # Align entry size to 4 bytes
            self.__entry_size = (len_data_entry + 1) & ~3
        # Don't recalculate entry size and pack fields
        else:
            off_field = 0x10

            for field in self.fields.values():
                STRUCT_FIELD.pack_into(buf_out, off_field, field.hash, field.mask, field.offset, field.shift, field.type)
                off_field += 0xC

        # Pack header
        STRUCT_HEADER.pack_into(buf_out, 0x0, num_entries, num_fields, off_data, self.__entry_size)

        # Pack entries
        buf_out += bytearray(self.__entry_size * num_entries)
        off_entry = off_data

        # Prepare the string pool. Store only one instance of each string to prevent duplicates.
        off_strings = len(buf_out)
        string_offsets = dict()

        for entry in entries:
            for field in self.fields.values():
                off_val = off_entry + field.offset
                val = entry[field.name]

                # Pack long or unsigned long
                if field.type == JMapFieldType.LONG or field.type == JMapFieldType.LONG_2:
                    helper.U32.pack_into(buf_out, off_val, (val << field.shift) & field.mask)
                # Pack string
                elif field.type == JMapFieldType.STRING:
                    buf_out[off_val:off_val + 0x20] = helper.pack_fixed_string(val, 0x20, "shift_jisx0213")
                # Pack float
                elif field.type == JMapFieldType.FLOAT:
                    helper.F32.pack_into(buf_out, off_val, val)
                # Pack short
                elif field.type == JMapFieldType.SHORT:
                    helper.U16.pack_into(buf_out, off_val, (val << field.shift) & field.mask)
                # Pack char
                elif field.type == JMapFieldType.CHAR:
                    buf_out[off_val] = (val << field.shift) & field.mask
                # Pack string at offset
                elif field.type == JMapFieldType.STRING_OFFSET:
                    if val in string_offsets:
                        off_string = string_offsets[val]
                    else:
                        off_string = len(buf_out) - off_strings
                        string_offsets[val] = off_string
                        buf_out += helper.pack_string(val, "shift_jisx0213")
                    helper.U32.pack_into(buf_out, off_val, off_string)

            off_entry += self.__entry_size

        # Align output buffer to 32 bytes
        buf_out += helper.align32(buf_out, "@")

        return buf_out
