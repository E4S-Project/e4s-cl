"""
Tests relating to MPI library version detection
"""

from pathlib import Path
import tests
from e4s_cl.model.profile import Profile
from e4s_cl.cf.libraries import resolve
from e4s_cl.cf.detect_name import (try_rename, detect_name, version_info,
                                   _suffix_name, _extract_mvapich_version,
                                   _extract_intel_mpi_version,
                                   _extract_mpich_version,
                                   _extract_cray_mpich_version,
                                   _extract_open_mpi_version, _extract_vinfo)

EMPTY_LIB = Path(Path(__file__).parent, 'assets', 'libgver.so.0')


class DetectNameTests(tests.TestCase):
    """
    Tests relating to MPI library version detection
    """

    def test_suffix(self):
        self.assertEqual(_suffix_name('apple', {}), 'apple')
        self.assertEqual(_suffix_name('apple', {'advanced'}), 'apple')
        self.assertEqual(_suffix_name('apple', {'applesauce'}), 'apple')
        self.assertEqual(_suffix_name('apple', {'advanced', 'apple'}),
                         'apple-2')
        self.assertEqual(_suffix_name('apple', {'advanced', 'apple-4'}),
                         'apple')
        self.assertEqual(
            _suffix_name('apple', {'advanced', 'apple', 'apple-4'}), 'apple-5')

    def test_version_mvapich2(self):
        output_string = """MVAPICH2 Version      :	2.3.5
MVAPICH2 Release date :	Mon November 30 22:00:00 EST 2020
MVAPICH2 Device       :	ch3:mrail
MVAPICH2 configure    :	--prefix=/storage/packages/hackathon-spack/padded-path-length-for-binaries/linux-centos8-x86_64/gcc-8.3.1/mvapich2-2.3.5-7ad2fvw2udf4zchllbq5csvdt437mpw4 --enable-shared --enable-romio --disable-silent-rules --disable-new-dtags --enable-fortran=all --enable-threads=multiple --with-ch3-rank-bits=32 --enable-wrapper-rpath=yes --disable-alloca --enable-fa"""

        self.assertEqual(_extract_mvapich_version(output_string), '2.3.5')

    def test_version_mpich(self):
        output_string = """MPICH Version:	3.3.2
MPICH Release date:	Tue Nov 12 21:23:16 CST 2019
MPICH ABI:	13:8:1
MPICH Device:	ch3:nemesis
MPICH configure:	--prefix=/storage/packages/hackathon-spack/padded-path-length-for-binaries/linux-centos8-x86_64/gcc-8.3.1/mpich-3.3.2-p3cgu65l6tfwgcz2di4c2as3xegyvqwq --disable-silent-rules --enable-shared --with-hwloc-prefix=/storage/packages/hackathon-spack/padded-path-length-for-binaries/linux-centos8-x86_64/gcc-8.3.1/hwloc-2.4.0-t5gpp6x6bw6blyx25ujx4bk5if5iywjt --with-pm=hydra -"""

        self.assertEqual(_extract_mpich_version(output_string), '3.3.2')

    def test_version_cray_mpich(self):
        output_string = """MPI VERSION    : CRAY MPICH version 7.7.14 (ANL base 3.2)
MPI BUILD INFO : Built Tue May 19 13:54:36 2020 (git hash e25eab9) MT-G

"""

        self.assertEqual(_extract_cray_mpich_version(output_string), '7.7.14')

    def test_version_intel(self):
        output_string = """Intel(R) MPI Library 2019 Update 6 for Linux* OS

"""

        self.assertEqual(_extract_intel_mpi_version(output_string),
                         '2019 Update 6')

    def test_version_ompi(self):
        output_string = """Open MPI v4.1.1, package: Open MPI user@host Distribution, ident: 4.1.1, repo rev: v4.1.1, Apr 24, 2021"""

        self.assertEqual(_extract_open_mpi_version(output_string), '4.1.1')

    @tests.skipIf(not resolve('libmpi.so'), "No library to test with")
    def test_extract_handle(self):
        self.assertIsNotNone(_extract_vinfo(Path(resolve('libmpi.so'))))

    def test_extract_handle_inexistent_path(self):
        self.assertIsNone(_extract_vinfo(Path('/tmp/sikenolib')))

    def test_extract_handle_bad_path(self):
        self.assertIsNone(_extract_vinfo(Path('/root')))

    def test_extract_handle_incomplete_library(self):
        self.assertIsNone(_extract_vinfo(EMPTY_LIB))

    @tests.skipIf(not resolve('libmpi.so'), "No library to test with")
    def test_get_version_info(self):
        self.assertIsNotNone(version_info(Path(resolve('libmpi.so'))))

        self.assertIsNotNone(
            version_info(Path(resolve('libmpi.so')).as_posix()))

    def test_get_version_info_inexistent_path(self):
        self.assertIsNone(version_info(Path('/tmp/sikenolib')))

    def test_get_version_info_bad_path(self):
        self.assertIsNone(version_info(Path('/root')))

    def test_get_version_info_incomplete_library(self):
        self.assertIsNone(
            version_info(Path(Path(__file__).parent, 'assets',
                              'libgver.so.0')))

    @tests.skipIf(not resolve('libmpi.so'), "No library to test with")
    def test_detect_name(self):
        self.assertTrue(detect_name([resolve('libmpi.so')]))

    def test_detect_name_no_mpi(self):
        self.assertFalse(detect_name([EMPTY_LIB]))

    @tests.skipIf(not resolve('libmpi.so'), "No library to test with")
    def test_rename_profile(self):
        name = '__test_profile_rename'

        profile = Profile.controller().create({
            'name': name,
            'libraries': [resolve('libmpi.so')]
        })

        try_rename(profile.eid)

        profile = Profile.controller().one(profile.eid)

        self.assertNotEqual(profile.get('name'), name)

    def test_rename_profile_mpiless(self):
        name = '__test_profile_rename'

        profile = Profile.controller().create({
            'name': name,
            'libraries': [resolve('libc.so.6')]
        })

        try_rename(profile.eid)

        profile = Profile.controller().one(profile.eid)

        self.assertEqual(profile.get('name'), name)

    def test_rename_profile_bad_eid(self):
        try_rename(256)
