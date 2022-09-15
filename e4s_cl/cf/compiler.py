from pathlib import Path
from elftools.elf.elffile import ELFFile
from elftools.common.exceptions import ELFError
from e4s_cl.logger import get_logger

LOGGER = get_logger(__name__)


def _get_comment(elf_file: Path) -> str:
    """
    Returns the contents of the .comment sections of the ELF file passed as an argument
    """
    try:
        with open(elf_file, 'rb') as data:
            elf = ELFFile(data)
            comment_sections = filter(lambda x: x.name == '.comment',
                                      elf.iter_sections())
            return ' - '.join(
                map(lambda x: x.data().decode(), comment_sections))
    except (PermissionError, FileNotFoundError, IsADirectoryError,
            ELFError) as err:
        LOGGER.debug("Error reading comments of file %s: %s", str(elf_file),
                     str(err))
        return ''
