from enum import IntEnum

from formats.compression import decompress, decompress_yaz0, decompress_yay0, JKRCompressionType
from formats.helper import *


class JKRFileAttr(IntEnum):
    NORMAL = 0
    DIRECTORY = 1
    COMPRESSED = 2
    COMPRESSION_TYPE = 7


class JKRDirEntry:
    def __init__(self, name: str):
        self.name = name
        self.sub_folders = list()
        self.sub_files = list()

    def __str__(self):
        return self.name

    def __len__(self):
        return len(self.sub_folders) + len(self.sub_files)

    def set_name(self, name: str):
        self.name = name.strip("/")

    def find_folder(self, file_path: str, fix_file_path=True):
        # Function to find direct child folder
        def find_child(child_name: str):
            for folder in self.sub_folders:
                if child_name == folder.name.lower():
                    return folder
            return None

        # Find nested folder (e.g. "jmp/Placement")
        if file_path.find("/") != -1:
            # Try to remove any leading or trailing separators
            if fix_file_path:
                file_path = file_path.strip("/").lower()

            child_name, sub_path = file_path.split("/", 1)
            child = find_child(child_name)

            if child is not None:
                return child.find_folder(sub_path, False)
        # Find folder (e.g. "jmp")
        else:
            return find_child(file_path)

        return None

    def find_file(self, file_path: str, fix_file_path=True):
        # Function to find direct child folder
        def find_child(child_name: str):
            child_name = child_name.lower()
            for file in self.sub_files:
                if child_name == file.name.lower():
                    return file
            return None

        # Find nested file (e.g. "ActorInfo/InitActor.bcsv")
        if file_path.find("/") != -1:
            # Try to remove any leading or trailing separators
            if fix_file_path:
                file_path = file_path.strip("/")

            sub_path, child_name = file_path.rsplit("/", 1)
            folder = self.find_folder(sub_path)

            if folder is not None:
                return folder.find_file(child_name, False)
        # Find file (e.g. "Kuribo.bdl")
        else:
            return find_child(file_path)

        return None


class JKRFileEntry:
    def __init__(self, name: str):
        self.name = name
        self.data = None
        self.compression = JKRCompressionType.NONE

    def __str__(self):
        return self.name

    def __len__(self):
        if self.data:
            return len(self.data)
        return 0

    def set_name(self, name: str):
        self.name = name.strip("/")

    def get_data(self):
        return self.data

    def set_data(self, data):
        self.data = data


class JKRArchive:
    def __init__(self, root: str = "root"):
        self.root = JKRDirEntry(root)

    def unpack(self, buffer):
        self.root = None

        # In SMG1/2, and possibly other games, RARC files are usually compressed. We have to decompress our buffer first
        # before we can start parsing the archive data.
        buffer = decompress(buffer)

        # Parse header
        if get_magic4(buffer, 0x0) != "RARC":
            raise Exception("Fatal! No RARC data provided.")

        # The header consists of many more values than we are using here. There is no need to parse the remaining values
        # since these are only relevant when the game loads and parses these archives. The following fields have been
        # ignored here: total file size, total data size, MRAM size and ARAM size.
        off_info, len_info = struct.unpack_from(">2I", buffer, 0x8)

        # Parse info header. Again, a lot of values are irrelevant for this tool. The following fields have been ignored
        # here: number of total file entries INCLUDING directories, total size of the string pool, and total number of
        # total file entries.
        num_nodes, off_nodes = struct.unpack_from(">2I", buffer, off_info)
        off_files = get_u32(buffer, off_info + 0xC) + off_info
        off_strings = get_u32(buffer, off_info + 0x14) + off_info

        # Fix relative offsets
        off_data = off_info + len_info
        off_nodes += off_info

        nodes = list()
        sub_nodes = dict()

        # Parse all directory nodes
        off_node = off_nodes

        for _ in range(num_nodes):
            # Directory nodes consist of a 4-byte identifier, offset to the name, hash, number of files and the first
            # file entry index. However, the identifier and hash have no use here, meaning that we can safely skip those
            # values when parsing the nodes.
            off_name, num_files, idx_files_start = struct.unpack_from(">IxxHI", buffer, off_node + 0x4)
            off_name += off_strings

            # Read the current node's name, create and append a directory entry for the node
            dir_name = read_ascii(buffer, off_name)
            dir_entry = JKRDirEntry(dir_name)
            nodes.append(dir_entry)

            # Store the sub directory nodes of the current nodes. These will be used to assign the proper subdirectories
            # for all the nodes at the end.
            sub_nodes_for_dir = list()
            sub_nodes[dir_entry] = sub_nodes_for_dir

            # The very first node is always the root node of the archive
            if self.root is None:
                self.root = dir_entry

            # Calculate the starting offset of the file entries for the current directory node
            off_file = off_files + (idx_files_start * 0x14)

            # Parse all file entries, including sub directories
            for _ in range(num_files):
                # Usually, file entries consist of a unique identifier, a 16-bit hash, attribute flags, the name offset,
                # the data offset and data size. However, the identifier and hash are not required when we parse entries
                # here. Therefore, we do not read those values at all.
                flags, off_file_data, len_file_data = struct.unpack_from(">3I", buffer, off_file + 0x4)

                # The upper 8 bits are the attribute flags whereas the lower 24 bits are the offset to the file name.
                off_name = off_strings + (flags & 0x00FFFFFF)
                flags = (flags >> 24) & 0xFF

                # Read file name
                file_name = read_ascii(buffer, off_name)

                # Update the next file offset already in case we find one of the two useless directories.
                off_file += 0x14

                # These directories... exist. These are found in every JKRArchive, however, they are never used. Thus,
                # we simply ignore and skip those files.
                if file_name == "." or file_name == "..":
                    continue

                # Directory entry
                if test_bit(flags, JKRFileAttr.DIRECTORY):
                    sub_nodes_for_dir.append(off_file_data)
                # File entry
                else:
                    # Is file data compressed? If so, determine the compression type (YAZ0 or YAY0)
                    if test_bit(flags, JKRFileAttr.COMPRESSED):
                        if test_bit(flags, JKRFileAttr.COMPRESSION_TYPE):
                            compression_type = JKRCompressionType.YAZ0
                        else:
                            compression_type = JKRCompressionType.YAY0
                    else:
                        compression_type = JKRCompressionType.NONE

                    # Read file data
                    off_file_data = off_data + off_file_data
                    buf_file_data = buffer[off_file_data:off_file_data + len_file_data]

                    # Decompress file data if necessary
                    if compression_type == JKRCompressionType.YAZ0:
                        buf_file_data = decompress_yaz0(buf_file_data, False)
                    elif compression_type == JKRCompressionType.YAY0:
                        buf_file_data = decompress_yay0(buf_file_data, False)

                    # Create and append file entry
                    file_entry = JKRFileEntry(file_name)
                    file_entry.data = buf_file_data
                    file_entry.compression = compression_type

                    dir_entry.sub_files.append(file_entry)

            off_node += 0x10

        # Append the proper subdirectories to the corresponding parent directories. I believe there is still a much
        # better approach to this problem.
        for parent_dir, sub_nodes_for_dir in sub_nodes.items():
            for sub_node in sub_nodes_for_dir:
                parent_dir.sub_folders.append(nodes[sub_node])

    def pack(self):
        pass
