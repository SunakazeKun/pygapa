import struct
from enum import IntEnum

from formats import helper, mrhash

# BCSV or JMap is the most used serialized / binary data format used in SMG1/2. Some older GameCube titles, such as
# Luigi's Mansion and Donkey Kong Jungle Beat, use this data format as well. As the name suggests, BCSV is a binary
# variant of Comma-separated values (CSV). This means that the data is laid out in a table-like structure where each
# entry / row uses the same columns / fields. The column names are hashed for faster access. The data is a flatbuffer
# and is loaded directly into memory, meaning that it does not have to be deserialized first. Unlike CSV, cells are not
# limited to strings only, hence the name Binary CSV. The game supports reading the data as signed and unsigned integers
# (8, 16 and 32 bit), single-precision floats and strings.
#
# However, the usage of the field types may be inconsistent and imprecise. For 99% of the time, we are never going to
# face these situations, especially when dealing with the particle BCSV files. Still, I want my modules to stick to the
# original format as close as I can. As you can see below, integer numbers are interpreted as signed values since this
# is used most of the time. When we take a look at the game's functions, we can see that the function to read unsigned
# integers is compatible with types 0, 3, 4 and 5. This begs the question how we are supposed to differentiate the field
# types. For example, the CHAR type (5) can be read as signed or unsigned data. It depends on the game's function
# calls, there is no information on this property. I thought about this problem for a while and drew the conclusion to
# just use the signed data types when reading the values. However, we can simply use bit-masking if we really want to
# use the unsigned data. In fact, I believe the terms BYTE, WORD and DWORD may be more appropriate for these fields.
#
# tl;dr Integer types can be interpreted as signed and unsigned. This module parses signed integers only, but if we need
# to, we can use bit-masks (0xFF, 0xFFFF and 0xFFFFFFFF) to retrieve the unsigned data.
#
# Another interesting aspect of JMap field types are strings. In SMG1/2, BCSV files use a string pool consisting of all
# strings. For each string, only one instance is kept to reduce space. The actual entries store an offset to the
# respective string in the string pool. However, in older titles using JMap, strings had a fixed size of 32 bytes and
# were stored inside the entry. Obviously, this causes a huge waste of space since all duplicates are kept and the
# strings are padded with zeros to fill the remaining space. This old format uses JMap field type ID 1 in games. On the
# other hand, the offset string type (ID 6) was added in later games. It always confused me that no file in SMG1/2 uses
# field type 1, so I began researching this matter. I recently discovered that the function to read strings from BCSV
# files still supports this. While I discourage its use, it is still fully functional.
#
# tl;dr String type 1 is supported in SMG1/2, but offset strings (type 6) should always be used for efficiency reasons.
#
# One thing that is worth noting about existing BCSV libraries and tools is that *all* of them do not handle the saving
# of the fields properly. If we take a look at BCSV files in SMG1/2, we can see that the entry offsets do not match the
# order of the fields themselves. This is because Nintendo's tools calculated the offsets and total entry size by
# filtering the fields by field type. None of the existing and commonly used tools do that. This is not a big issue of
# course, but this is necessary for us to write 1:1 matching files.


STRUCT_HEADER = struct.Struct(">4I")
STRUCT_FIELD = struct.Struct(">2IH2B")

_FIELD_SIZES = (4, 32, 4, 4, 2, 1, 4, 0)
_FIELD_MASKS = (0xFFFFFFFF, 0, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFF, 0xFF, 0xFFFFFFFF, 0)
_FIELD_ORDER = (2, 0, 1, 3, 4, 5, 6, -1)
_FIELD_DEFAULTS = (0, "", 0.0, 0, 0, 0, "", None)


class JMapFieldType(IntEnum):
    LONG = 0
    STRING = 1  # Unused in SMG1/2, used in Luigi's Mansion and probably other games using JMapInfo
    FLOAT = 2
    LONG_2 = 3
    SHORT = 4
    CHAR = 5
    STRING_OFFSET = 6
    INVALID = 7  # Identifies non-existent fields. Do not use this in actual files

    def __len__(self):
        """
        Returns the entry size for this field type. The data sizes are as follows:
        LONG, LONG_2, FLOAT, STRING_OFFSET -> 4
        SHORT -> 2
        CHAR -> 1
        STRING -> 32
        INVALID -> 0
        """
        return _FIELD_SIZES[self]

    def mask(self):
        """
        Returns the entry mask for this field type. The bit-masks are as follows:
        LONG, LONG_2, FLOAT, STRING_OFFSET -> 0xFFFFFFFF
        SHORT -> 0xFFFF
        CHAR -> 0xFF
        STRING, INVALID -> 0
        """
        return _FIELD_MASKS[self]

    def order(self):
        """
        Returns the packing order of this field type. The order is as follows:
        INVALID > FLOAT > STRING > LONG > LONG_2 > SHORT > CHAR > STRING_OFFSET
        """
        return _FIELD_ORDER[self]

    def default(self):
        """
        Returns the default value for this field type. The default values are as follows:
        LONG, LONG_2, SHORT, CHAR -> 0
        FLOAT -> 0.0
        STRING, STRING_OFFSET -> ""
        INVALID -> None
        """
        return _FIELD_DEFAULTS[self]


class JMapField:
    def __init__(self):
        self._hash = 0
        self.mask = 0
        self.offset = 0
        self.shift = 0
        self._type = JMapFieldType.INVALID
        self._name = None

    @classmethod
    def new_named(cls, field_name: str, field_type: JMapFieldType, mask: int = -1, offset: int = -1, shift: int = 0):
        """
        Creates a new field with the specified field name and attributes. The hash is calculated automatically.

        :param field_name: the field name
        :param field_type: the field data type
        :param mask: the bit-mask to be used
        :param offset: the entry data offset
        :param shift: the amount of bits to be shifted
        """
        instance = cls()
        instance._name = field_name
        instance._hash = mrhash.calc_hash(field_name)
        instance._type = field_type
        instance.mask = mask & field_type.mask()
        instance.offset = offset
        instance.shift = shift
        return instance

    @classmethod
    def new_hashed(cls, field_hash: int, field_type: JMapFieldType, mask: int = -1, offset: int = -1, shift: int = 0):
        """
        Creates a new field with the specified field hash and attributes. The name is retrieved automatically.

        :param field_hash: the 32-bit hash
        :param field_type: the field data type
        :param mask: the bit-mask to be used
        :param offset: the entry data offset
        :param shift: the amount of bits to be shifted
        """
        instance = cls()
        instance._name = mrhash.find_name(field_hash)
        instance._hash = field_hash
        instance._type = field_type
        instance.mask = mask & field_type.mask()
        instance.offset = offset
        instance.shift = shift
        return instance

    def __len__(self):
        """Returns the field structure size. This is always 12 bytes."""
        return 12

    def unpack(self, buffer, offset: int = 0):
        """
        Unpacks the field attributes from the buffer at the specified offset.

        :param buffer: a bytes-like buffer to retrieve the data from
        :param offset: the offset to read the data from
        """
        self._hash, self.mask, self.offset, self.shift, field_type = STRUCT_FIELD.unpack_from(buffer, offset)
        self._type = JMapFieldType(field_type)
        self._name = mrhash.find_name(self._hash)

    def pack(self, buffer, offset: int = 0):
        """
        Packs the current field into the buffer at the specified offset.

        :param buffer: a bytes-like buffer to write the data to
        :param offset: the offset at which to write the data"""
        STRUCT_FIELD.pack_into(buffer, offset, self._hash, self.mask, self.offset, self.shift, self._type)

    def __str__(self):
        """Returns the field's name."""
        return self._name

    def get_hash(self) -> int:
        """Returns the field's 32-bit hash."""
        return self._hash

    def get_type(self) -> JMapFieldType:
        """Returns the field's JMapFieldType."""
        return self._type


class JMapInfo:
    def __init__(self):
        self.fields = dict()
        self.entries = list()
        self.entry_size = -1  # Negative number forces recalculation of this value and field offsets

    def new_field(self, field_name: str, field_type: JMapFieldType, mask: int = -1, shift: int = 0):
        """
        Creates a new field in this JMapInfo container with the specified attributes. If the field already exists, an
        exception is raised. All existing entries will be populated with a default value for the newly added field.

        :param field_name: the field name
        :param field_type: the field data type
        :param mask: the bit-mask to be used
        :param shift: the amount of bits to be shifted
        :raises Exception: raised when a field by that name already exists
        """
        # Does a field with that name exist already?
        if field_name in self.fields:
            raise Exception(f"Field {field_name} already exists!")

        # Create new field
        self.fields[field_name] = JMapField.new_named(field_name, field_type, mask=mask, shift=shift)

        # Populate entries with default values
        for entry in self.entries:
            entry[field_name] = field_type.default()

        # Clear entry size
        self.entry_size = -1

    def drop_field(self, field_name: str):
        """
        Removes the field specified by the given name. All entry values for that field will be removed as well.

        :param field_name: the field name
        """
        self.fields.pop(field_name)

        for entry in self.entries:
            entry.pop(field_name)

        self.entry_size = -1

    def unpack(self, buffer, offset: int = 0):
        self.fields.clear()
        self.entries.clear()

        # Read header and calculate offsets
        num_entries, num_fields, off_data, self.entry_size = STRUCT_HEADER.unpack_from(buffer, offset)
        off_data += offset
        off_strings = off_data + (num_entries * self.entry_size)

        # Read fields
        for i in range(num_fields):
            off_field = offset + 0x10 + i * 0xC
            field = JMapField()
            field.unpack(buffer, off_field)
            self.fields[str(field)] = field

        # Read entries
        for i in range(num_entries):
            entry = dict()

            for field in self.fields.values():
                offset = off_data + i * self.entry_size + field.offset
                field_type = field.get_type()
                val = None

                # Read long
                if field_type == JMapFieldType.LONG or field_type == JMapFieldType.LONG_2:
                    val = helper.try_sign32((helper.get_u32(buffer, offset) & field.mask) >> field.shift)
                # Read string
                elif field_type == JMapFieldType.STRING:
                    val = helper.read_fixed_string(buffer, offset, 0x20, "shift_jisx0213")
                # Read float
                elif field_type == JMapFieldType.FLOAT:
                    val = round(helper.get_f32(buffer, offset), 7)
                # Read short
                elif field_type == JMapFieldType.SHORT:
                    val = helper.try_sign16((helper.get_u16(buffer, offset) & field.mask) >> field.shift)
                # Read char
                elif field_type == JMapFieldType.CHAR:
                    val = helper.try_sign8((buffer[offset] & field.mask) >> field.shift)
                # Read string at offset
                elif field_type == JMapFieldType.STRING_OFFSET:
                    off_string = off_strings + helper.get_u32(buffer, offset)
                    val = helper.read_string(buffer, off_string, "shift_jisx0213")

                entry[str(field)] = val

            self.entries.append(entry)

    def pack(self, sort_by_field: str = None):
        # Sort entries by field name if specified
        if sort_by_field is not None:
            entries = sorted(self.entries, key=lambda k: k[sort_by_field])
        else:
            entries = self.entries

        # Fetch header information
        num_entries = len(self.entries)
        num_fields = len(self.fields)
        off_data = 0x10 + num_fields * 0xC

        # Calculate entry size and field offsets
        if self.entry_size < 0:
            len_data_entry = 0
            is_first_string_offset = True

            for field in sorted(self.fields.values(), key=lambda k: k.get_type().order()):
                field_type = field.get_type()

                # String offsets are the last field type in the writing order. It can occur that the previous field type
                # caused the entry size to be unaligned to 4 bytes. Thus, we have to fix this here.
                if field_type == JMapFieldType.STRING_OFFSET and is_first_string_offset:
                    len_data_entry = (len_data_entry + 1) & ~3
                    is_first_string_offset = False

                field.offset = len_data_entry
                len_data_entry += len(field_type)

            # Align total entry size to 4 bytes
            self.entry_size = (len_data_entry + 3) & ~3

        # Prepare output buffer and pack header
        buf_out = bytearray(off_data + num_entries * self.entry_size)
        STRUCT_HEADER.pack_into(buf_out, 0x0, num_entries, num_fields, off_data, self.entry_size)

        # Pack fields
        off_field = 0x10

        for field in self.fields.values():
            field.pack(buf_out, off_field)
            off_field += 0xC

        # Pack entries and prepare the string pool. Store only one instance of each string to prevent duplicates.
        off_entry = off_data
        off_strings = len(buf_out)
        string_offsets = dict()

        for entry in entries:
            for field in self.fields.values():
                off_val = off_entry + field.offset
                field_type = field.get_type()
                val = entry[str(field)]

                # Pack long or unsigned long
                if field_type == JMapFieldType.LONG or field_type == JMapFieldType.LONG_2:
                    helper.U32.pack_into(buf_out, off_val, (val << field.shift) & field.mask)
                # Pack string
                elif field_type == JMapFieldType.STRING:
                    buf_out[off_val:off_val + 0x20] = helper.pack_fixed_string(val, 0x20, "shift_jisx0213")
                # Pack float
                elif field_type == JMapFieldType.FLOAT:
                    helper.F32.pack_into(buf_out, off_val, val)
                # Pack short
                elif field_type == JMapFieldType.SHORT:
                    helper.U16.pack_into(buf_out, off_val, (val << field.shift) & field.mask)
                # Pack char
                elif field_type == JMapFieldType.CHAR:
                    buf_out[off_val] = (val << field.shift) & field.mask
                # Pack string at offset
                elif field_type == JMapFieldType.STRING_OFFSET:
                    if val in string_offsets:
                        off_string = string_offsets[val]
                    else:
                        off_string = len(buf_out) - off_strings
                        string_offsets[val] = off_string
                        buf_out += helper.pack_string(val, "shift_jisx0213")
                    helper.U32.pack_into(buf_out, off_val, off_string)

            off_entry += self.entry_size

        # Align output buffer to 32 bytes
        buf_out += helper.align32(buf_out, "@")

        return buf_out
