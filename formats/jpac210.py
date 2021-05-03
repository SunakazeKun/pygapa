from helper import *


class JPATexture:
    def __init__(self):
        self.file_name = ""          # Texture file name
        self.bti_data = bytearray()  # BTI texture data
        self.total_size = 0          # Total size in bytes, set when (un)packing

    def unpack(self, buffer, offset: int = 0):
        self.total_size = get_s32(buffer, offset + 0x4)
        self.file_name = read_sjis_string(buffer, offset + 0xC)
        self.bti_data = buffer[offset + 0x20:offset + self.total_size]

    def pack(self) -> bytes:
        out_name = pack_sjis_string(self.file_name)

        # Calculate and create padding bytes
        pad_name = 0x14 - len(out_name)
        if pad_name < 0:
            raise Exception(f"File name {self.file_name} is too long to pack!")
        out_pad_name = bytes(pad_name)
        out_pad_bti = align32(self.bti_data)

        # Calculate total size; 0x20 = header and name size
        self.total_size = 0x20 + len(self.bti_data) + len(out_pad_bti)

        # Assemble output
        out_packed = "TEX1".encode("ascii") + struct.pack(">2i", self.total_size, 0)
        out_packed += out_name + out_pad_name + self.bti_data + out_pad_bti

        return out_packed


class JPAChunk:
    def unpack(self, buffer, offset: int = 0):
        pass

    def unpack_json(self, entry):
        pass

    def pack(self) -> bytes:
        pass

    def pack_json(self):
        pass


class JPADynamicsBlock(JPAChunk):
    def __init__(self):
        self.binary_data = None

    def unpack(self, buffer, offset: int = 0):
        size = get_s32(buffer, offset + 0x4) - 8
        offset += 0x8
        self.binary_data = buffer[offset:offset + size]

    def unpack_json(self, entry):
        self.binary_data = bytes.fromhex(entry)

    def pack(self) -> bytes:
        out_data = self.binary_data + align4(self.binary_data)
        return "BEM1".encode("ascii") + pack_s32(8 + len(out_data)) + out_data

    def pack_json(self):
        return self.binary_data.hex()


class JPAFieldBlock(JPAChunk):
    def __init__(self):
        self.binary_data = None

    def unpack(self, buffer, offset: int = 0):
        size = get_s32(buffer, offset + 0x4) - 8
        offset += 0x8
        self.binary_data = buffer[offset:offset + size]

    def unpack_json(self, entry):
        self.binary_data = bytes.fromhex(entry)

    def pack(self) -> bytes:
        out_data = self.binary_data + align4(self.binary_data)
        return "FLD1".encode("ascii") + pack_s32(8 + len(out_data)) + out_data

    def pack_json(self):
        return self.binary_data.hex()


class JPAKeyBlock(JPAChunk):
    def __init__(self):
        self.binary_data = None

    def unpack(self, buffer, offset: int = 0):
        size = get_s32(buffer, offset + 0x4) - 8
        offset += 0x8
        self.binary_data = buffer[offset:offset + size]

    def unpack_json(self, entry):
        self.binary_data = bytes.fromhex(entry)

    def pack(self) -> bytes:
        out_data = self.binary_data + align4(self.binary_data)
        return "KFA1".encode("ascii") + pack_s32(8 + len(out_data)) + out_data

    def pack_json(self):
        return self.binary_data.hex()


class JPABaseShape(JPAChunk):
    def __init__(self):
        self.binary_data = None

    def unpack(self, buffer, offset: int = 0):
        size = get_s32(buffer, offset + 0x4) - 8
        offset += 0x8
        self.binary_data = buffer[offset:offset + size]

    def unpack_json(self, entry):
        self.binary_data = bytes.fromhex(entry)

    def pack(self) -> bytes:
        out_data = self.binary_data + align4(self.binary_data)
        return "BSP1".encode("ascii") + pack_s32(8 + len(out_data)) + out_data

    def pack_json(self):
        return self.binary_data.hex()


class JPAExtraShape(JPAChunk):
    def __init__(self):
        self.binary_data = None

    def unpack(self, buffer, offset: int = 0):
        size = get_s32(buffer, offset + 0x4) - 8
        offset += 0x8
        self.binary_data = buffer[offset:offset + size]

    def unpack_json(self, entry):
        self.binary_data = bytes.fromhex(entry)

    def pack(self) -> bytes:
        out_data = self.binary_data + align4(self.binary_data)
        return "ESP1".encode("ascii") + pack_s32(8 + len(out_data)) + out_data

    def pack_json(self):
        return self.binary_data.hex()


class JPAChildShape(JPAChunk):
    def __init__(self):
        self.binary_data = None

    def unpack(self, buffer, offset: int = 0):
        size = get_s32(buffer, offset + 0x4) - 8
        offset += 0x8
        self.binary_data = buffer[offset:offset + size]

    def unpack_json(self, entry):
        self.binary_data = bytes.fromhex(entry)

    def pack(self) -> bytes:
        out_data = self.binary_data + align4(self.binary_data)
        return "SSP1".encode("ascii") + pack_s32(8 + len(out_data)) + out_data

    def pack_json(self):
        return self.binary_data.hex()


class JPAExTexShape(JPAChunk):
    def __init__(self):
        self.binary_data = None

    def unpack(self, buffer, offset: int = 0):
        size = get_s32(buffer, offset + 0x4) - 8
        offset += 0x8
        self.binary_data = buffer[offset:offset + size]

    def unpack_json(self, entry):
        self.binary_data = bytes.fromhex(entry)

    def pack(self) -> bytes:
        out_data = self.binary_data + align4(self.binary_data)
        return "ETX1".encode("ascii") + pack_s32(8 + len(out_data)) + out_data

    def pack_json(self):
        return self.binary_data.hex()


class JPAResource:
    def __init__(self):
        self.dynamics_block = None   # JPADynamicsBlock
        self.field_blocks = list()   # list of JPAFieldBlock
        self.key_blocks = list()     # list of JPAKeyBlock
        self.base_shape = None       # JPABaseShape
        self.extra_shape = None      # JPAExtraShape
        self.child_shape = None      # JPAChildShape
        self.ex_tex_shape = None     # JPAExTexShape
        self.texture_ids = list()    # List of texture IDs
        self.texture_names = list()  # List of texture file names, will be populated later on

        self.index = 0               # The particles index inside the container
        self.unk4 = 0                # Unknown as of now, may be two separate bytes
        self.unk6 = 0                # Unknown as of now, may be two separate bytes
        self.total_size = 0          # Total size in bytes, set when (un)packing

    def unpack(self, buffer, offset: int = 0):
        # Setup members
        self.dynamics_block = None
        self.field_blocks.clear()
        self.key_blocks.clear()
        self.base_shape = None
        self.extra_shape = None
        self.child_shape = None
        self.ex_tex_shape = None
        self.texture_ids.clear()
        self.texture_names.clear()
        self.total_size = 8  # In SMG, the first 8 bytes are the header for JPAResource

        # Parse header
        self.index, num_sections, self.unk4, self.unk6 = struct.unpack_from(">4h", buffer, offset)
        offset += self.total_size

        # Go through all available sections
        for i in range(num_sections):
            # Parse block header and extract block
            magic = buffer[offset:offset + 0x4].decode("ascii")
            size = get_s32(buffer, offset + 0x4)
            block = buffer[offset:offset + size]

            # Parse JPADynamicsBlock
            if magic == "BEM1":
                self.dynamics_block = JPADynamicsBlock()
                self.dynamics_block.unpack(buffer, offset)
            # Parse JPAFieldBlock entries
            elif magic == "FLD1":
                field_block = JPAFieldBlock()
                field_block.unpack(buffer, offset)
                self.field_blocks.append(field_block)
            # Parse JPAKeyBlock entries
            elif magic == "KFA1":
                key_block = JPAKeyBlock()
                key_block.unpack(buffer, offset)
                self.key_blocks.append(key_block)
            # Parse JPABaseShape
            elif magic == "BSP1":
                self.base_shape = JPABaseShape()
                self.base_shape.unpack(buffer, offset)
            # Parse JPAExtraShape
            elif magic == "ESP1":
                self.extra_shape = JPAExtraShape()
                self.extra_shape.unpack(buffer, offset)
            # Parse JPAChildShape
            elif magic == "SSP1":
                self.child_shape = JPAChildShape()
                self.child_shape.unpack(buffer, offset)
            # Parse JPAExTexShape
            elif magic == "ETX1":
                self.ex_tex_shape = JPAExTexShape()
                self.ex_tex_shape.unpack(buffer, offset)
            # Parse texture ID database
            elif magic == "TDB1":
                num_texture_ids = (size - 8) // 2

                # Since TDB1 is always aligned to 4 bytes, we have to drop invalid IDs. Therefore, we only accept IDs of
                # 0 if it is the first texture ID entry.
                zero_found = False
                for j in range(num_texture_ids):
                    texture_id = get_s16(block, 0x8 + j * 0x2)

                    if texture_id == 0:
                        if zero_found:
                            break  # overflow into padding
                        zero_found = True

                    self.texture_ids.append(texture_id)
            # Just to be sure we find a wrong section
            else:
                raise Exception(f"Unknown section {magic}")

            # Adjust offset and total size
            self.total_size += size
            offset += size

    def pack(self) -> bytes:
        # Pack header
        out_buf = bytearray() + struct.pack(">4h", self.index, 0, self.unk4, self.unk6)

        # Pack blocks
        num_sections = 0
        if len(self.texture_ids) > 0:
            num_sections += 1

        if self.dynamics_block:
            out_buf += self.dynamics_block.pack()
            num_sections += 1
        if len(self.field_blocks) > 0:
            for field_block in self.field_blocks:
                out_buf += field_block.pack()
                num_sections += 1
        if len(self.key_blocks) > 0:
            for key_block in self.key_blocks:
                out_buf += key_block.pack()
                num_sections += 1
        if self.base_shape:
            out_buf += self.base_shape.pack()
            num_sections += 1
        if self.extra_shape:
            out_buf += self.extra_shape.pack()
            num_sections += 1
        if self.child_shape:
            out_buf += self.child_shape.pack()
            num_sections += 1
        if self.ex_tex_shape:
            out_buf += self.ex_tex_shape.pack()
            num_sections += 1

        # Write section count
        struct.pack_into(">h", out_buf, 0x2, num_sections)

        # Pack texture ID database
        out_tdb1 = bytearray()

        if len(self.texture_ids) > 0:
            for texture_id in self.texture_ids:
                out_tdb1 += pack_s16(texture_id)
            out_tdb1 += align4(out_tdb1, "\0")

            out_tdb1 = "TDB1".encode("ascii") + pack_s32(len(out_tdb1) + 8) + out_tdb1

        # Assemble output
        out_buf += out_tdb1
        self.total_size = len(out_buf)

        return out_buf


class JParticlesContainer:
    def __init__(self):
        self.particles = list()  # List of JPAResource entries
        self.textures = dict()   # JPATextures indexed by their file name

    def unpack(self, buffer, offset: int = 0):
        self.particles.clear()
        self.textures.clear()

        # Parse header
        magic = buffer[offset:offset + 0x8].decode("ascii")
        if magic != "JPAC2-10":
            raise Exception("Fatal! No JPAC2-10 data provided.")

        num_particles, num_textures, off_textures = struct.unpack_from(">HHi", buffer, offset + 0x8)

        # Parse JPAResource entries
        next_offset = offset + 0x10

        for i in range(num_particles):
            jpa = JPAResource()
            jpa.unpack(buffer, next_offset)

            self.particles.append(jpa)
            next_offset += jpa.total_size

        # Parse JPATexture entries
        texture_filenames = list()
        next_offset = offset + off_textures

        for i in range(num_textures):
            jpatex = JPATexture()
            jpatex.unpack(buffer, next_offset)

            texture_filenames.append(jpatex.file_name)
            self.textures[jpatex.file_name] = jpatex
            next_offset += jpatex.total_size

        # Append texture file names for every particle
        for jpa in self.particles:
            for texture_index in jpa.texture_ids:
                jpa.texture_names.append(texture_filenames[texture_index])

    def pack(self):
        # Pack header
        out_buf = bytearray() + "JPAC2-10".encode("ascii")
        out_buf += struct.pack(">HHi", len(self.particles), len(self.textures), 0)

        # Pack JPAResource entries
        texture_name_to_id = list(self.textures.keys())

        for jpa in self.particles:
            # Get texture IDs from texture names
            jpa.texture_ids.clear()

            for texture_name in jpa.texture_names:
                texture_id = texture_name_to_id.index(texture_name)
                if texture_id == -1:
                    raise Exception(f"Unknown texture name {texture_name}. Is this in the JSON's texture list?")

                jpa.texture_ids.append(texture_id)

            out_buf += jpa.pack()

        # Align buffer and write offset to textures
        out_buf += align32(out_buf)
        struct.pack_into(">i", out_buf, 0xC, len(out_buf))

        # Pack JPATexture entries
        for jpatex in self.textures.values():
            out_buf += jpatex.pack()
        # no padding necessary here since textures are already aligned to 32 bytes

        # Assemble and return packed data
        return out_buf
