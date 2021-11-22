"""
Tests relating to MPI library version detection
"""

from e4s_cl import tests
from e4s_cl.cf.detect_name import (_suffix_name, _extract_mvapich_version,
                                   _extract_intel_mpi_version,
                                   _extract_mpich_version,
                                   _extract_cray_mpich_version,
                                   _extract_open_mpi_version)


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
