import struct
import pyaurum
from copy import deepcopy

__all__ = [
    # Classes
    "JPATexture",
    "JPAChunk",
    "JPADynamicsBlock",
    "JPAFieldBlock",
    "JPAKeyBlock",
    "JPABaseShape",
    "JPAExtraShape",
    "JPAChildShape",
    "JPAExTexShape",
    "JPAResource",
    "JParticlesContainer"
]


class JPATexture:
    def __init__(self):
        self.file_name = ""          # Texture file name
        self.bti_data = bytearray()  # BTI texture data
        self.total_size = 0          # Total size in bytes, set when (un)packing

    def unpack(self, buffer, offset: int = 0):
        self.total_size = pyaurum.get_s32(buffer, offset + 0x4)
        self.file_name = pyaurum.read_fixed_string(buffer, offset + 0xC, 0x14)
        self.bti_data = buffer[offset + 0x20:offset + self.total_size]

    def pack(self) -> bytes:
        # Pack name and align BTI data
        out_name = pyaurum.pack_fixed_string(self.file_name, 0x14)
        out_pad_bti = pyaurum.align32(self.bti_data)

        # Calculate total size; 0x20 = header and name size
        self.total_size = 0x20 + len(self.bti_data) + len(out_pad_bti)

        # Assemble output
        out_packed = bytearray(struct.pack(">3i", 0x54455831, self.total_size, 0))
        out_packed += out_name + self.bti_data + out_pad_bti

        return out_packed

    def replace_with(self, other):
        self.file_name = other.file_name
        self.bti_data = other.bti_data[:]


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
        size = pyaurum.get_s32(buffer, offset + 0x4) - 8
        offset += 0x8
        self.binary_data = buffer[offset:offset + size]

    def unpack_json(self, entry):
        self.binary_data = bytes.fromhex(entry)

    def pack(self) -> bytes:
        out_data = self.binary_data + pyaurum.align4(self.binary_data)
        return "BEM1".encode("ascii") + pyaurum.pack_s32(8 + len(out_data)) + out_data

    def pack_json(self):
        return self.binary_data.hex()


class JPAFieldBlock(JPAChunk):
    def __init__(self):
        self.binary_data = None

    def unpack(self, buffer, offset: int = 0):
        size = pyaurum.get_s32(buffer, offset + 0x4) - 8
        offset += 0x8
        self.binary_data = buffer[offset:offset + size]

    def unpack_json(self, entry):
        self.binary_data = bytes.fromhex(entry)

    def pack(self) -> bytes:
        out_data = self.binary_data + pyaurum.align4(self.binary_data)
        return "FLD1".encode("ascii") + pyaurum.pack_s32(8 + len(out_data)) + out_data

    def pack_json(self):
        return self.binary_data.hex()


class JPAKeyBlock(JPAChunk):
    def __init__(self):
        self.binary_data = None

    def unpack(self, buffer, offset: int = 0):
        size = pyaurum.get_s32(buffer, offset + 0x4) - 8
        offset += 0x8
        self.binary_data = buffer[offset:offset + size]

    def unpack_json(self, entry):
        self.binary_data = bytes.fromhex(entry)

    def pack(self) -> bytes:
        out_data = self.binary_data + pyaurum.align4(self.binary_data)
        return "KFA1".encode("ascii") + pyaurum.pack_s32(8 + len(out_data)) + out_data

    def pack_json(self):
        return self.binary_data.hex()


class JPABaseShape(JPAChunk):
    def __init__(self):
        self.binary_data = None

    def unpack(self, buffer, offset: int = 0):
        size = pyaurum.get_s32(buffer, offset + 0x4) - 8
        offset += 0x8
        self.binary_data = buffer[offset:offset + size]

    def unpack_json(self, entry):
        self.binary_data = bytes.fromhex(entry)

    def pack(self) -> bytes:
        out_data = self.binary_data + pyaurum.align4(self.binary_data)
        return "BSP1".encode("ascii") + pyaurum.pack_s32(8 + len(out_data)) + out_data

    def pack_json(self):
        return self.binary_data.hex()


class JPAExtraShape(JPAChunk):
    def __init__(self):
        self.binary_data = None

    def unpack(self, buffer, offset: int = 0):
        size = pyaurum.get_s32(buffer, offset + 0x4) - 8
        offset += 0x8
        self.binary_data = buffer[offset:offset + size]

    def unpack_json(self, entry):
        self.binary_data = bytes.fromhex(entry)

    def pack(self) -> bytes:
        out_data = self.binary_data + pyaurum.align4(self.binary_data)
        return "ESP1".encode("ascii") + pyaurum.pack_s32(8 + len(out_data)) + out_data

    def pack_json(self):
        return self.binary_data.hex()


class JPAChildShape(JPAChunk):
    def __init__(self):
        self.binary_data = None

    def unpack(self, buffer, offset: int = 0):
        size = pyaurum.get_s32(buffer, offset + 0x4) - 8
        offset += 0x8
        self.binary_data = buffer[offset:offset + size]

    def unpack_json(self, entry):
        self.binary_data = bytes.fromhex(entry)

    def pack(self) -> bytes:
        out_data = self.binary_data + pyaurum.align4(self.binary_data)
        return "SSP1".encode("ascii") + pyaurum.pack_s32(8 + len(out_data)) + out_data

    def pack_json(self):
        return self.binary_data.hex()


class JPAExTexShape(JPAChunk):
    def __init__(self):
        self.binary_data = None

    def unpack(self, buffer, offset: int = 0):
        size = pyaurum.get_s32(buffer, offset + 0x4) - 8
        offset += 0x8
        self.binary_data = buffer[offset:offset + size]

    def unpack_json(self, entry):
        self.binary_data = bytes.fromhex(entry)

    def pack(self) -> bytes:
        out_data = self.binary_data + pyaurum.align4(self.binary_data)
        return "ETX1".encode("ascii") + pyaurum.pack_s32(8 + len(out_data)) + out_data

    def pack_json(self):
        return self.binary_data.hex()


class JPAResource:
    def __init__(self):
        self.name = None
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
        self.total_size = 0          # Total size in bytes, set when (un)packing

    def unpack(self, buffer, offset: int = 0):
        # Setup members
        self.name = None
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
        self.index, num_sections, num_field_blocks, num_key_blocks, num_textures = struct.unpack_from(">2h3B", buffer, offset)
        offset += self.total_size

        # Go through all available sections
        for i in range(num_sections):
            # Parse block header and extract block
            magic = buffer[offset:offset + 0x4].decode("ascii")
            size = pyaurum.get_s32(buffer, offset + 0x4)
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
                for j in range(num_textures):
                    self.texture_ids.append(pyaurum.get_s16(block, 0x8 + j * 0x2))
            # Just to be sure we find a wrong section
            else:
                raise Exception(f"Unknown section {magic}")

            # Adjust offset and total size
            self.total_size += size
            offset += size

        if num_key_blocks != len(self.key_blocks):
            raise Exception(f"Expected {num_key_blocks} key blocks, found {len(self.key_blocks)}")
        if num_field_blocks != len(self.field_blocks):
            raise Exception(f"Expected {num_field_blocks} field blocks, found {len(self.field_blocks)}")

    def unpack_json(self, entry: dict):
        self.field_blocks.clear()
        self.key_blocks.clear()

        self.texture_ids.clear()
        self.texture_names = entry["textures"]

        self.index = -1
        self.total_size = 0

        if "dynamicsBlock" in entry:
            self.dynamics_block = JPADynamicsBlock()
            self.dynamics_block.unpack_json(entry["dynamicsBlock"])
        if "fieldBlocks" in entry:
            for field_block_json in entry["fieldBlocks"]:
                field_block = JPAFieldBlock()
                field_block.unpack_json(field_block_json)
                self.field_blocks.append(field_block)
        if "keyBlocks" in entry:
            for key_block_json in entry["keyBlocks"]:
                key_block = JPAKeyBlock()
                key_block.unpack_json(key_block_json)
                self.key_blocks.append(key_block)
        if "baseShape" in entry:
            self.base_shape = JPABaseShape()
            self.base_shape.unpack_json(entry["baseShape"])
        if "extraShape" in entry:
            self.extra_shape = JPAExtraShape()
            self.extra_shape.unpack_json(entry["extraShape"])
        if "childShape" in entry:
            self.child_shape = JPAChildShape()
            self.child_shape.unpack_json(entry["childShape"])
        if "exTexShape" in entry:
            self.ex_tex_shape = JPAExTexShape()
            self.ex_tex_shape.unpack_json(entry["exTexShape"])

    def pack(self) -> bytes:
        # Pack header
        num_field_blocks = len(self.field_blocks)
        num_key_blocks = len(self.key_blocks)
        num_textures = len(self.texture_ids)
        out_buf = bytearray() + struct.pack(">2h4B", self.index, 0, num_field_blocks, num_key_blocks, num_textures, 0)

        # Pack blocks
        num_sections = 1

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

        for texture_id in self.texture_ids:
            out_tdb1 += pyaurum.pack_s16(texture_id)
        out_tdb1 += pyaurum.align4(out_tdb1, "\0")

        out_tdb1 = "TDB1".encode("ascii") + pyaurum.pack_s32(len(out_tdb1) + 8) + out_tdb1

        # Assemble output
        out_buf += out_tdb1
        self.total_size = len(out_buf)

        return out_buf

    def pack_json(self) -> dict:
        entry = dict()

        # Pack blocks
        if self.dynamics_block:
            entry["dynamicsBlock"] = self.dynamics_block.pack_json()
        if len(self.field_blocks) > 0:
            entry["fieldBlocks"] = list()

            for field_block in self.field_blocks:
                entry["fieldBlocks"].append(field_block.pack_json())
        if len(self.key_blocks) > 0:
            entry["keyBlocks"] = list()

            for key_block in self.key_blocks:
                entry["keyBlocks"].append(key_block.pack_json())
        if self.base_shape:
            entry["baseShape"] = self.base_shape.pack_json()
        if self.extra_shape:
            entry["extraShape"] = self.extra_shape.pack_json()
        if self.child_shape:
            entry["childShape"] = self.child_shape.pack_json()
        if self.ex_tex_shape:
            entry["exTexShape"] = self.ex_tex_shape.pack_json()

        # Pack texture names
        entry["textures"] = self.texture_names

        return entry

    def replace_with(self, other):
        self.name = other.name
        self.field_blocks.clear()
        self.key_blocks.clear()
        self.texture_names.clear()
        self.texture_names += other.texture_names

        self.dynamics_block = deepcopy(other.dynamics_block)

        for block in other.field_blocks:
            self.field_blocks.append(deepcopy(block))

        for block in other.key_blocks:
            self.key_blocks.append(deepcopy(block))

        self.base_shape = deepcopy(other.base_shape)
        self.extra_shape = deepcopy(other.extra_shape)
        self.child_shape = deepcopy(other.child_shape)
        self.ex_tex_shape = deepcopy(other.ex_tex_shape)


class JParticlesContainer:
    def __init__(self):
        self.particles = list()  # List of JPAResource entries
        self.textures = dict()   # JPATextures indexed by their file name

    def unpack(self, buffer, offset: int = 0):
        self.particles.clear()
        self.textures.clear()

        # Parse header
        if pyaurum.get_magic8(buffer, offset) != "JPAC2-10":
            raise Exception("Fatal! No JPAC2-10 data provided.")

        num_particles, num_textures, off_textures = struct.unpack_from(">HHI", buffer, offset + 0x8)

        # Parse JPATexture entries
        # We parse them first as we need the texture filenames for particles. This saves loading time as we do not have
        # to go through all the particles twice. However, in the actual JPC file, the particle data comes first.
        texture_filenames = list()
        next_offset = offset + off_textures

        for i in range(num_textures):
            texture = JPATexture()
            texture.unpack(buffer, next_offset)

            texture_filenames.append(texture.file_name)
            self.textures[texture.file_name] = texture
            next_offset += texture.total_size

        # Parse JPAResource entries
        next_offset = offset + 0x10

        for i in range(num_particles):
            particle = JPAResource()
            particle.unpack(buffer, next_offset)

            # Append texture file names for every particle
            for texture_index in particle.texture_ids:
                particle.texture_names.append(texture_filenames[texture_index])

            self.particles.append(particle)
            next_offset += particle.total_size

    def pack(self):
        # Pack header, we will write the textures offset later
        out_buf = bytearray() + pyaurum.pack_magic8("JPAC2-10")
        out_buf += struct.pack(">HHI", len(self.particles), len(self.textures), 0)

        # Pack JPAResource entries
        texture_name_to_id = list(self.textures.keys())

        for particle in self.particles:
            # Get texture IDs from texture names
            particle.texture_ids.clear()

            for texture_name in particle.texture_names:
                # This error can only occur in batch mode since the editor prevents saving if the error check finds
                # invalid texture names.
                try:
                    particle.texture_ids.append(texture_name_to_id.index(texture_name))
                except ValueError:
                    pass

            out_buf += particle.pack()

        # Align buffer and write offset to textures
        out_buf += pyaurum.align32(out_buf)
        struct.pack_into(">I", out_buf, 0xC, len(out_buf))

        # Pack JPATexture entries
        for texture in self.textures.values():
            out_buf += texture.pack()
        # No padding necessary here since textures are already aligned to 32 bytes

        # Return packed data
        return out_buf
