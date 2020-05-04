import os
from e4s_cl import logger, util
from e4s_cl import PROFILE_DIR
from e4s_cl.cf.storage import StorageError
from e4s_cl.cf.storage.local_file import LocalFileStorage

LOGGER = logger.get_logger(__name__)

class ProfileStorageError(StorageError):
    message_fmt = ("%(value)s\n"
                   "\n"
                   "%(hints)s\n"
                   "Please contact %(contact)s for assistance.")

    def __init__(self, search_root):
        """Initialize the error object.
        
        Args:
            search_root (str): Directory in which the search for a profile directory was initiated.
        """
        value = "Profile directory not found in '%s' or any of its parent directories." % search_root
        hints = "Make sure that you have already run the `tau initialize` command in this directory or any of its parent directories."
        super(ProfileStorageError, self).__init__(value, hints)
        self.search_root = search_root
        
class ProfileStorage(LocalFileStorage):
    """Handle the special case profile storage.
    
    Each TAU Commander profile has its own profile storage that holds profile-specific files
    (i.e. performance data) and the profile configuration.
    """
    
    def __init__(self):
        super(ProfileStorage, self).__init__('profile', None)
        self._force_cwd = False
        self._tau_directory = None
    
    def connect_filesystem(self, *args, **kwargs):
        """Prepares the store filesystem for reading and writing."""
        from e4s_cl.cf.storage.levels import USER_STORAGE
        profile_prefix = os.path.join(os.getcwd(), PROFILE_DIR)
        if os.path.exists(os.path.join(profile_prefix, USER_STORAGE.name + ".json")):
             raise StorageError("Cannot create profile in home directory. "
                                   "Use '-@ user' option for user level storage.")
        try:
            util.mkdirp(profile_prefix)
        except Exception as err:
            raise StorageError("Failed to access %s filesystem prefix '%s': %s" % 
                                   (self.name, profile_prefix, err))
        # Exclude profile storage directory from git
        with open(os.path.join(self.prefix, '.gitignore'), 'w+') as fout:
            fout.write('/*\n')
        LOGGER.debug("Initialized %s filesystem prefix '%s'", self.name, profile_prefix)

    def destroy(self, *args, **kwargs):
        """Disconnects the database and filesystem and recursively deletes the filesystem.
        
        Args:
            *args: Passed through to :any:`disconnect_filesystem`.
            **kwargs: Keyword arguments for :any:`disconnect_filesystem` or :any:`shutil.rmtree`.
        """
        self.disconnect_filesystem(*args, **kwargs)
        ignore_errors = kwargs.pop('ignore_errors', False)
        onerror = kwargs.pop('onerror', None)
        if self._prefix:
            util.rmtree(self._prefix, ignore_errors=ignore_errors, onerror=onerror)
            self._prefix = None

    @property
    def prefix(self):
        return PROFILE_DIR

    def force_cwd(self, force):
        self._force_cwd = force

    def tau_dir(self, taudir):
        self._tau_directory = taudir
