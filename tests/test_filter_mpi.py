import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from e4s_cl.cli.commands.profile.detect import _filter_mpi_artifacts

class FilterMPITest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir_obj = TemporaryDirectory()
        self.tmp_dir = Path(self.tmp_dir_obj.name)
        
        # Create 'system' MPI
        self.sys_mpi = self.tmp_dir / "usr/lib/mpich/lib/libmpi.so"
        self.sys_mpi.parent.mkdir(parents=True)
        self.sys_mpi.touch()

        # Create 'system' launcher
        self.sys_launcher = self.tmp_dir / "usr/bin/mpirun"
        self.sys_launcher.parent.mkdir(parents=True)
        self.sys_launcher.touch()
        self.sys_launcher.chmod(0o755)

        # Create 'conflicting' Intel MPI
        self.intel_mpi = self.tmp_dir / "opt/intel/oneapi/lib/libmpi.so"
        self.intel_mpi.parent.mkdir(parents=True)
        self.intel_mpi.touch()

        # Create unrelated artifact (depends on Intel MPI)
        self.intel_dep = self.tmp_dir / "opt/intel/oneapi/lib/libfabric.so"
        self.intel_dep.touch()

    def tearDown(self):
        self.tmp_dir_obj.cleanup()

    def test_filter_pollution(self):
        libs = [self.sys_mpi, self.intel_mpi, self.intel_dep]
        files = []
        
        filtered_libs, filtered_files = _filter_mpi_artifacts(libs, files, self.sys_launcher)
        
        # We expect sys_mpi to be present
        self.assertIn(str(self.sys_mpi), filtered_libs)
        
        # We expect intel_mpi to be removed
        self.assertNotIn(str(self.intel_mpi), filtered_libs)
        
        # We expect intel_dep to be KEPT now, because we whitelist non-core libs
        self.assertIn(str(self.intel_dep), filtered_libs)

    def test_filter_system_usr(self):
        # Scenario: Launcher in /usr/bin, lib in /usr/lib
        # This checks the "system" heuristic
        
        libs = [self.sys_mpi]
        files = []
        filtered_libs, _ = _filter_mpi_artifacts(libs, files, self.sys_launcher)
        self.assertIn(str(self.sys_mpi), filtered_libs)

    def test_filter_divergent_paths_kept(self):
        """
        Divergent paths (where launcher and lib don't share prefix) are kept 
        if no other library matches the launcher. Fail-open behavior.
        """
        divergent_dir = self.tmp_dir / "opt/divergent"
        divergent_dir.mkdir(parents=True)
        
        launcher = divergent_dir / "bin/mpirun"
        launcher.parent.mkdir(parents=True)
        launcher.touch()
        
        lib = divergent_dir / "custom/lib/libmpi.so"
        lib.parent.mkdir(parents=True)
        lib.touch()
        
        libs = [lib]
        files = []
        filtered_libs, _ = _filter_mpi_artifacts(libs, files, launcher)
        
        self.assertIn(str(lib), filtered_libs)

    def test_example_a_openmpi_external_deps(self):
        """
        Example A: Open MPI built with external PMIx / UCX / HWLOC
        Should keep all libraries because they are required deps, even if different prefixes.
        """
        launcher = Path('/opt/mpi/openmpi/4.1.6/bin/mpirun')
        libs = [
            Path('/opt/mpi/openmpi/4.1.6/lib/libmpi.so'),
            Path('/opt/pmix/4.2.6/lib/libpmix.so'),
            Path('/opt/ucx/1.15.0/lib/libucp.so'),
            Path('/usr/lib64/libhwloc.so')
        ]
        files = []
        
        kept_libs, kept_files = _filter_mpi_artifacts(libs, files, launcher)
        
        self.assertEqual(len(kept_libs), 4)
        self.assertIn('/opt/mpi/openmpi/4.1.6/lib/libmpi.so', kept_libs)

    def test_example_c_vendor_wrapper(self):
        """
        Example C: Vendor launcher + Spack-provided MPI
        Launcher in /usr/bin, MPI in /opt/spack via LD_LIBRARY_PATH.
        Should keep everything.
        """
        launcher = Path('/usr/bin/mpirun')
        libs = [
            Path('/opt/spack/openmpi/lib/libmpi.so'),
            Path('/opt/spack/pmix/lib/libpmix.so')
        ]
        files = []

        kept_libs, kept_files = _filter_mpi_artifacts(libs, files, launcher)

        self.assertEqual(len(kept_libs), 2)

    def test_example_e_worst_case(self):
        """
        Example E: Mixed environment with /usr/bin launcher
        """
        launcher = Path('/usr/bin/mpirun')
        libs = [
            Path('/opt/spack/openmpi/lib/libmpi.so'),
            Path('/opt/spack/pmix/lib/libpmix.so'),
            Path('/usr/lib64/libhwloc.so'),
            Path('/opt/intel/oneapi/lib/libfabric.so')
        ]
        files = []

        kept_libs, kept_files = _filter_mpi_artifacts(libs, files, launcher)

        self.assertEqual(len(kept_libs), 4)

    def test_multiple_mpi_core_libs(self):
        """
        Scenario where multiple MPI core libs exist.
        Should pick authoritative one (closest to launcher) and discard other CORE libs.
        But keep non-core libs even if under discarded prefix.
        """
        launcher = Path('/opt/ompi/bin/mpirun')
        libs = [
            Path('/opt/ompi/lib/libmpi.so'),        # Authoritative
            Path('/opt/mpich/lib/libmpich.so'),     # Conflicting MPI
            Path('/opt/mpich/lib/libfabric.so'),    # Useful dep in discarded prefix
            Path('/opt/other/lib/libfoo.so')        # Neutral
        ]
        
        kept_libs, kept_files = _filter_mpi_artifacts(libs, files=[], launcher=launcher)
        
        self.assertIn('/opt/ompi/lib/libmpi.so', kept_libs)
        self.assertNotIn('/opt/mpich/lib/libmpich.so', kept_libs)
        self.assertIn('/opt/mpich/lib/libfabric.so', kept_libs)
        self.assertIn('/opt/other/lib/libfoo.so', kept_libs)

    def test_mpi_filter_off(self):
        """
        Test disabling the filter.
        """
        launcher = Path('/opt/ompi/bin/mpirun')
        libs = [
            Path('/opt/ompi/lib/libmpi.so'),
            Path('/opt/mpich/lib/libmpich.so'),
        ]
        files = []

        kept_libs, kept_files = _filter_mpi_artifacts(libs, files, launcher, mpi_filter='off')
        
        self.assertEqual(len(kept_libs), 2)

    def test_mpi_filter_manual(self):
        """
        Test manual filter (disables auto filter, but respects exclusions if provided - tested separately).
        Solely manual should return everything if no exclusions provided.
        """
        launcher = Path('/opt/ompi/bin/mpirun')
        libs = [
            Path('/opt/ompi/lib/libmpi.so'),
            Path('/opt/mpich/lib/libmpich.so'),
        ]
        files = []

        kept_libs, kept_files = _filter_mpi_artifacts(libs, files, launcher, mpi_filter='manual')

        self.assertEqual(len(kept_libs), 2)

    def test_exclude_lib_name(self):
        """
        Test manual exclusion by name.
        """
        launcher = Path('/opt/ompi/bin/mpirun')
        libs = [
            Path('/opt/ompi/lib/libmpi.so'),
            Path('/opt/mpich/lib/libmpich.so'),
        ]
        files = []

        kept_libs, kept_files = _filter_mpi_artifacts(
            libs, files, launcher, 
            mpi_filter='auto', 
            exclude_names=['libmpich.so']
        )
        
        self.assertIn('/opt/ompi/lib/libmpi.so', kept_libs)
        self.assertNotIn('/opt/mpich/lib/libmpich.so', kept_libs)

    def test_exclude_lib_prefix(self):
        """
        Test manual exclusion by prefix.
        """
        launcher = Path('/opt/ompi/bin/mpirun')
        libs = [
            Path('/opt/ompi/lib/libmpi.so'),
            Path('/opt/bad/lib/libbad.so'),
        ]
        files = []

        kept_libs, kept_files = _filter_mpi_artifacts(
            libs, files, launcher, 
            mpi_filter='auto', 
            exclude_prefixes=['/opt/bad']
        )
        
        self.assertIn('/opt/ompi/lib/libmpi.so', kept_libs)
        self.assertNotIn('/opt/bad/lib/libbad.so', kept_libs)
