from enum import IntFlag

from formats.compression import decompress, decompress_szs, decompress_szp, JKRCompressionType
from formats.helper import *


class JKRFileAttr(IntFlag):
    FILE = 1
    DIRECTORY = 2
    COMPRESSED = 4
    IS_DATA = 16
    IS_REL = 32
    USE_YAZ0 = 128


class JKRDirEntry:
    def __init__(self, name: str):
        self.__name = name
        self.sub_folders = list()
        self.sub_files = list()

    def __str__(self):
        return self.__name

    def __len__(self):
        return len(self.sub_folders) + len(self.sub_files)

    def set_name(self, name: str):
        self.__name = name.strip("/")

    def find_folder(self, file_path: str, fix_file_path=True):
        # Function to find direct child folder
        def find_child(child_name: str):
            child_name = child_name.lower()
            for folder in self.sub_folders:
                if child_name == str(folder).lower():
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
                if child_name == str(file).lower():
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

    def add_file(self, file) -> bool:
        lower_file = str(file).lower()
        for sub_file in self.sub_files:
            if str(sub_file).lower() == lower_file:
                return False

        self.sub_files.append(file)
        return True

    def add_folder(self, folder) -> bool:
        lower_folder = str(folder).lower()
        for sub_folder in self.sub_folders:
            if str(sub_folder).lower() == lower_folder:
                return False

        self.sub_folders.append(folder)
        return True

    def remove_folder(self, folder_name: str):
        folder_name = folder_name.lower()
        index = -1
        i = 0

        for folder in self.sub_folders:
            if str(folder).lower() == folder_name:
                index = i
                break
            i += 1

        if index > -1:
            folder = self.sub_folders[index]
            self.sub_folders.pop(index)
            return folder

        return None

    def remove_file(self, file_name: str):
        file_name = file_name.lower()
        index = -1
        i = 0

        for file in self.sub_files:
            if str(file).lower() == file_name:
                index = i
                break
            i += 1

        if index > -1:
            file = self.sub_files[index]
            self.sub_files.pop(index)
            return file

        return None


class JKRFileEntry:
    def __init__(self, name: str, data=None, compression: int = JKRCompressionType.NONE, is_rel: bool = False):
        self.__name = name
        self.__data = data
        self.set_compression(compression)
        self.is_rel = is_rel

    def __str__(self):
        return self.__name

    def __len__(self):
        if self.__data:
            return len(self.__data)
        return 0

    def set_name(self, name: str):
        self.__name = name.strip("/")

    def get_data(self):
        return self.__data

    def set_data(self, data):
        self.__data = data

    def set_compression(self, compression: int):
        if compression < JKRCompressionType.NONE or compression >= JKRCompressionType.ASR:
            compression = JKRCompressionType.NONE
        self.__compression = compression

    def get_compression(self):
        return self.__compression


class JKRArchive:
    def __init__(self, root: str = "root"):
        self.__root = JKRDirEntry(root)

    def __str__(self):
        """
        This prints the entire file structure contained in this archive. This should only be used for debugging and
        testing purposes.
        """
        if self.__root is None:
            print("None")

        result = ""
        is_continuous = False

        def print_dir(folder, indent):
            nonlocal result, is_continuous
            if is_continuous:
                result += "\n"
            is_continuous = True

            spaces = " " * indent
            result += spaces + str(folder)

            for sub_folder in folder.sub_folders:
                print_dir(sub_folder, indent + 1)

            for sub_file in folder.sub_files:
                result += "\n " + spaces + str(sub_file)

        print_dir(self.__root, 0)

        return result

    def unpack(self, buffer):
        self.__root = None

        # In SMG1/2, and possibly other games, RARC files are usually compressed. We have to try decompressing our
        # buffer before we can start parsing the actual archive data.
        buffer = decompress(buffer)

        # Parse header
        if get_magic4(buffer) != "RARC":
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

        all_nodes = list()  # List of all directory nodes
        sub_nodes = dict()  # Stores subdirectory node IDs for each directory

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
            all_nodes.append(dir_entry)

            # Store the sub directory nodes of the current nodes. These will be used to assign the proper subdirectories
            # for all the nodes at the end.
            sub_nodes_for_dir = list()
            sub_nodes[dir_entry] = sub_nodes_for_dir

            # The very first node is always the root node of the archive
            if self.__root is None:
                self.__root = dir_entry

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
                if flags & JKRFileAttr.DIRECTORY:
                    sub_nodes_for_dir.append(off_file_data)
                # File entry
                elif flags & JKRFileAttr.FILE:
                    # Is file data compressed? If so, determine the compression type (YAZ0 or YAY0)
                    if flags & JKRFileAttr.COMPRESSED:
                        if flags & JKRFileAttr.USE_YAZ0:
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
                        buf_file_data = decompress_szs(buf_file_data, False)
                    elif compression_type == JKRCompressionType.YAY0:
                        buf_file_data = decompress_szp(buf_file_data, False)

                    # Test if the file is a REL file
                    is_rel = test_bit(flags, JKRFileAttr.IS_REL)

                    # Create and append file entry
                    file_entry = JKRFileEntry(file_name, buf_file_data, compression_type, is_rel)

                    dir_entry.sub_files.append(file_entry)
                else:
                    raise Exception(f"Fatal! Unknown file entry {file_name} with attributes {flags} found.")

            off_node += 0x10

        # Append the proper subdirectories to the corresponding parent directories. I believe there is still a much
        # better approach to this problem.
        for parent_dir, sub_nodes_for_dir in sub_nodes.items():
            for sub_node in sub_nodes_for_dir:
                parent_dir.sub_folders.append(all_nodes[sub_node])

    @staticmethod
    def __file_name_to_hash(file_name: str) -> int:
        file_hash = 0
        for ch in file_name.encode("ascii"):
            file_hash *= 3
            file_hash += ch
        return file_hash & 0xFFFF

    @staticmethod
    def __dir_identifier(dir_name: str, is_first: bool) -> int:
        # Root node uses "ROOT" as identifier
        if is_first:
            return 0x524F4F54

        enc_upper = dir_name.upper().encode("ascii")
        len_enc_name = len(enc_upper)

        identifier = 0
        for i in range(4):
            identifier <<= 8
            if i >= len_enc_name:
                identifier += 0x20
            else:
                identifier += enc_upper[i]
        return identifier

    def pack(self):
        out_buf = bytearray(64)

        # Prepare output buffers and data
        out_strings = bytearray()
        out_data = bytearray()
        string_offsets = dict()
        num_nodes = 0
        num_total_files = 0

        # File entries with actual data are indexed, this stores the next index
        cur_file_id = 0

        def find_or_add_string(val: str) -> int:
            nonlocal out_strings
            if val in string_offsets:
                off = string_offsets[val]
            else:
                off = len(out_strings)
                string_offsets[val] = off
                out_strings += pack_ascii(val)
            return off

        # These two directory names always appear first in the string table
        find_or_add_string(".")
        find_or_add_string("..")

        def create_nodes(directory: JKRDirEntry):
            nonlocal out_buf, num_total_files, num_nodes

            dir_name = str(directory)
            ind_node = self.__dir_identifier(dir_name, num_nodes == 0)
            off_name = find_or_add_string(dir_name)
            hash_name = self.__file_name_to_hash(dir_name)
            num_files = len(directory) + 2  # 2 is for "." and ".."

            # This stores the temporary ID for this node since we need it later on when creating the file entries.
            directory.temp_id = num_nodes

            # Write node data to buffer and update counters
            out_buf += struct.pack(">2I2HI", ind_node, off_name, hash_name, num_files, num_total_files)
            num_total_files += num_files
            num_nodes += 1

            # Create nodes for sub folders recursively
            for folder in directory.sub_folders:
                create_nodes(folder)

        def create_files(directory: JKRDirEntry, parent_id: int):
            nonlocal out_buf, out_data, num_total_files, cur_file_id

            # Create folder entries
            for folder in directory.sub_folders:
                dir_name = str(folder)
                off_name = find_or_add_string(dir_name)
                hash_name = self.__file_name_to_hash(dir_name)
                flags = (1 << (24 + JKRFileAttr.DIRECTORY)) | off_name

                out_buf += struct.pack(">2H4I", 0xFFFF, hash_name, flags, folder.temp_id, 0x10, 0x0)

            # Create file entries
            for file in directory.sub_files:
                dir_name = str(file)
                off_name = find_or_add_string(dir_name)
                hash_name = self.__file_name_to_hash(dir_name)

                flags = JKRFileAttr.FILE
                flags |= JKRFileAttr.IS_REL if file.is_rel else JKRFileAttr.IS_DATA

                buf_file_data = file.get_data()

                # todo: Compression of individual files? Although this is not used, the game supports this

                flags_and_name = (flags << 24) | off_name
                off_file_data = len(out_data)

                out_data += buf_file_data

                out_buf += struct.pack(">2H4I", cur_file_id, hash_name, flags_and_name, off_file_data, len(buf_file_data), 0x0)
                cur_file_id += 1

            node_id = directory.temp_id

            # Create folder entries for "." and "..", these are constant except for their node index
            out_buf += struct.pack(">2H4I", 0xFFFF, 0x002E, 0x02000000, node_id, 0x10, 0x0)
            out_buf += struct.pack(">2H4I", 0xFFFF, 0x00B8, 0x02000002, parent_id, 0x10, 0x0)

            # Create entries for all sub folders and their files
            for folder in directory.sub_folders:
                create_files(folder, node_id)

            # Delete temporary ID since it is no longer required
            del directory.temp_id

        # Create nodes for all folders
        create_nodes(self.__root)
        out_buf += align32(out_buf)

        # Create entries for all files
        off_files = len(out_buf) - 0x20
        create_files(self.__root, 0xFFFFFFFF)
        out_buf += align32(out_buf)

        # Join output with strings
        off_strings = len(out_buf) - 0x20
        out_buf += out_strings
        out_buf += align32(out_buf)
        del out_strings

        # Join output with data
        off_data = len(out_buf) - 0x20
        len_strings = off_data - off_strings
        out_buf += out_data
        len_data = len(out_data)
        del out_data

        # Write header and information block data
        struct.pack_into(">4s5I", out_buf, 0x0, pack_magic4("RARC"), len(out_buf), 0x20, off_data, len_data, len_data)
        struct.pack_into(">6IHB", out_buf, 0x20, num_nodes, 0x20, num_total_files, off_files, len_strings, off_strings, num_total_files, 1)

        return out_buf

    def get_root(self) -> JKRDirEntry:
        return self.__root

    def set_root(self, new_root: JKRDirEntry):
        self.__root = new_root

    @staticmethod
    def path_without_root(file_path: str) -> str:
        file_path = file_path.strip("/")
        if file_path.find("/") != -1:
            _, file_path = file_path.split("/", 1)
        return file_path

    def find_folder(self, folder_path: str) -> JKRDirEntry:
        return self.__root.find_folder(self.path_without_root(folder_path), False)

    def find_file(self, file_path: str) -> JKRFileEntry:
        return self.__root.find_file(self.path_without_root(file_path), False)

    def add_folder(self, folder_path: str, directory: JKRDirEntry) -> bool:
        folder = self.find_folder(folder_path)
        if folder is None:
            return False
        return folder.add_folder(directory)

    def add_file(self, folder_path: str, file: JKRFileEntry) -> bool:
        folder = self.find_folder(folder_path)
        if folder is None:
            return False
        return folder.add_file(file)

    def remove_folder(self, folder_path: str) -> JKRDirEntry:
        raise Exception("Operation not supported yet.")

    def remove_file(self, file_path: str) -> JKRFileEntry:
        file_path = self.path_without_root(file_path)
        folder = self.__root

        if file_path.rfind("/") != -1:
            folder_path, file_name = file_path.rsplit("/", 1)
            folder = self.__root.find_folder(folder_path)
            file_path = file_name

        if folder is None:
            return None

        return folder.remove_file(file_path)
