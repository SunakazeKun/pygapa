import pyaurum
import struct

from jsystem import mrhash

__all__ = [
    # Classes
    "JMapFieldType",
    "JMapField",
    "JMapInfo"
]


# BCSV or JMap is the most used serialized / binary data format used in SMG1/2. Some older GameCube titles, such as
# Luigi's Mansion and Donkey Kong Jungle Beat, use this data format as well. As the name suggests, BCSV is a binary
# variant of Comma-separated values (CSV). This means that the data is laid out in a table-like structure where each
# entry / row uses the same columns / fields. The column names are hashed for faster access. The data is flatbuffer-like
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
# One thing that is worth noting about existing BCSV libraries and tools is that *all* of them do not handle the saving
# of the fields properly. If we take a look at BCSV files in SMG1/2, we can see that the entry offsets do not match the
# order of the fields themselves. This is because Nintendo's tools calculated the offsets and total entry size by
# sorting the fields by field type. None of the existing and commonly used tools do that. This is not a big issue of
# course, but this is necessary for us to produce 1:1 matching files.


class JMapFieldType(pyaurum.ExtIntEnum):
    def __init__(self, index, size=0, mask=0, order=0, default=None):
        self.index = index
        self.size = size
        self.mask = mask
        self.order = order
        self.default = default

    LONG          = 0,  4, 0xFFFFFFFF,  2,   0
    STRING        = 1, 32, 0x00000000,  0,  ""
    FLOAT         = 2,  4, 0xFFFFFFFF,  1, 0.0
    LONG_2        = 3,  4, 0xFFFFFFFF,  3,   0
    SHORT         = 4,  2, 0x0000FFFF,  4,   0
    CHAR          = 5,  1, 0x000000FF,  5,   0
    STRING_OFFSET = 6,  4, 0xFFFFFFFF,  6,  ""
    INVALID       = 7,  0, 0x00000000, -1, None


class JMapField:
    _STRUCT_FIELD_ = struct.Struct(">2IH2B")

    def __init__(self, fname: str = None, ftype: JMapFieldType = JMapFieldType.INVALID, mask: int = -1, shift: int = 0):
        if fname is not None:
            self._hash_ = mrhash.calc_hash(fname)
            self._name_ = fname
        else:
            self._hash_ = 0
            self._name_ = None

        self._type_ = ftype
        self.offset = 0
        self.mask = mask & ftype.mask
        self.shift = shift

    def unpack(self, buffer: pyaurum.ByteBuffer, offset: int = 0):
        """
        Unpacks the field attributes from the buffer at the specified offset.

        :param buffer: a bytes-like buffer to retrieve the data from
        :param offset: the offset to read the data from
        """
        self._hash_, self.mask, self.offset, self.shift, field_type = buffer.read_from(JMapField._STRUCT_FIELD_, offset)
        self._type_ = JMapFieldType(field_type)
        self._name_ = mrhash.find_name(self._hash_)

    def pack(self, buffer: pyaurum.ByteBuffer, offset: int = 0):
        """
        Packs the current field into the buffer at the specified offset.

        :param buffer: a bytes-like buffer to write the data to
        :param offset: the offset at which to write the data
        """
        buffer.write_into(JMapField._STRUCT_FIELD_, offset, self._hash_, self.mask, self.offset, self.shift, self._type_.index)

    @property
    def name(self):
        return self._name_

    @property
    def hash(self) -> int:
        return self._hash_

    @property
    def field_type(self) -> JMapFieldType:
        return self._type_


class JMapInfo:
    _STRUCT_HEADER_ = struct.Struct(">4I")

    def __init__(self):
        self.entries = list()
        self._fields_ = dict()
        self._entry_size_ = -1  # Negative number forces recalculation of this value and field offsets

    @property
    def fields(self):
        return self._fields_

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
        if field_name in self._fields_:
            raise Exception(f"Field {field_name} already exists!")

        # Create new field
        self._fields_[field_name] = JMapField(fname=field_name, ftype=field_type, mask=mask, shift=shift)

        # Populate entries with default values
        for entry in self.entries:
            entry[field_name] = field_type.default()

        # Clear entry size
        self._entry_size_ = -1

    def drop_field(self, field_name: str):
        """
        Removes the field specified by the given name. All entry values for that field will be removed as well.

        :param field_name: the field name
        """
        self._fields_.pop(field_name)

        for entry in self.entries:
            entry.pop(field_name)

        self._entry_size_ = -1

    def unpack(self, buffer: pyaurum.ByteBuffer):
        self.entries.clear()
        self._fields_.clear()

        # Read header and calculate offsets
        num_entries, num_fields, off_data, self._entry_size_ = buffer.read_from(JMapInfo._STRUCT_HEADER_, 0)
        off_strings = off_data + (num_entries * self._entry_size_)

        # Read fields
        for i in range(num_fields):
            off_field = 0x10 + i * 0xC
            field = JMapField()
            field.unpack(buffer, off_field)
            self._fields_[field.name] = field

        # Read entries
        for i in range(num_entries):
            entry = dict()

            for field in self._fields_.values():
                offset = off_data + i * self._entry_size_ + field.offset
                field_type = field.field_type
                val = None

                # Read long
                if field_type == JMapFieldType.LONG or field_type == JMapFieldType.LONG_2:
                    val = (buffer.read_from(">I", offset)[0] & field.mask) >> field.shift
                    val = pyaurum.try_sign32(val)
                # Read string
                elif field_type == JMapFieldType.STRING:
                    val = pyaurum.read_fixed_string(buffer, offset, 0x20, "shift_jisx0213")
                # Read float
                elif field_type == JMapFieldType.FLOAT:
                    val = buffer.read_from(">f", offset)[0]
                    val = round(val, 7)
                # Read short
                elif field_type == JMapFieldType.SHORT:
                    val = (buffer.read_from(">H", offset)[0] & field.mask) >> field.shift
                    val = pyaurum.try_sign16(val)
                # Read char
                elif field_type == JMapFieldType.CHAR:
                    val = (buffer[offset] & field.mask) >> field.shift
                    val = pyaurum.try_sign8(val)
                # Read string at offset
                elif field_type == JMapFieldType.STRING_OFFSET:
                    off_string = off_strings + buffer.read_from(">I", offset)[0]
                    val = pyaurum.read_string(buffer, off_string, "shift_jisx0213")

                entry[field.name] = val

            self.entries.append(entry)

    def pack(self, sort_by_field: str = None):
        # Sort entries by field name if specified
        if sort_by_field is not None:
            entries = sorted(self.entries, key=lambda k: k[sort_by_field])
        else:
            entries = self.entries

        # Fetch header information
        num_entries = len(self.entries)
        num_fields = len(self._fields_)
        off_data = 0x10 + num_fields * 0xC

        # Calculate entry size and field offsets
        if self._entry_size_ < 0:
            len_data_entry = 0
            is_first_string_offset = True

            for field in sorted(self._fields_.values(), key=lambda k: k.field_type.order):
                field_type = field.field_type

                # String offsets are the last field type in the writing order. It can occur that the previous field type
                # caused the entry size to be unaligned to 4 bytes. Thus, we have to fix this here.
                if field_type == JMapFieldType.STRING_OFFSET and is_first_string_offset:
                    len_data_entry = (len_data_entry + 1) & ~3
                    is_first_string_offset = False

                field.offset = len_data_entry
                len_data_entry += field_type.size

            # Align total entry size to 4 bytes
            self._entry_size_ = (len_data_entry + 3) & ~3

        # Prepare output buffer and pack header
        buffer = pyaurum.ByteBuffer(off_data + num_entries * self._entry_size_)
        buffer.write_into(JMapInfo._STRUCT_HEADER_, 0, num_entries, num_fields, off_data, self._entry_size_)

        # Pack fields
        offset = 0x10

        for field in self._fields_.values():
            field.pack(buffer, offset)
            offset += 0xC

        # Pack entries and prepare the string pool. Store only one instance of each string to prevent duplicates.
        off_strings = len(buffer)
        string_offsets = dict()

        for entry in entries:
            for field in self._fields_.values():
                off_val = offset + field.offset
                field_type = field.field_type
                val = entry[field.name]

                # Pack long or unsigned long
                if field_type == JMapFieldType.LONG or field_type == JMapFieldType.LONG_2:
                    buffer.write_into(">I", off_val, (val << field.shift) & field.mask)
                # Pack string
                elif field_type == JMapFieldType.STRING:
                    buffer[off_val:off_val + 0x20] = pyaurum.pack_fixed_string(val, 0x20, "shift_jisx0213")
                # Pack float
                elif field_type == JMapFieldType.FLOAT:
                    buffer.write_into(">f", off_val, val)
                # Pack short
                elif field_type == JMapFieldType.SHORT:
                    buffer.write_into(">H", off_val, (val << field.shift) & field.mask)
                # Pack char
                elif field_type == JMapFieldType.CHAR:
                    buffer[off_val] = (val << field.shift) & field.mask
                # Pack string at offset
                elif field_type == JMapFieldType.STRING_OFFSET:
                    if val in string_offsets:
                        off_string = string_offsets[val]
                    else:
                        off_string = len(buffer) - off_strings
                        string_offsets[val] = off_string
                        buffer += pyaurum.pack_string(val, "shift_jisx0213")

                    buffer.write_into(">I", off_val, off_string)

            offset += self._entry_size_

        # Align output buffer to 32 bytes
        buffer.align32("@")

        return buffer
