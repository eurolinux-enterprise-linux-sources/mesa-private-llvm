# Components enabled if supported by target architecture:
%ifarch %ix86 x86_64
  %bcond_without gold
%else
  %bcond_with gold
%endif

%if 0%{?rhel} == 6
%define rhel6 1
%endif

# llvm works on the 64-bit versions of these, but not the 32 versions.
# consequently we build swrast on them instead of llvmpipe.
ExcludeArch: ppc s390 %{?rhel6:s390x}

%ifarch s390x
%global host_target SystemZ
%endif
%ifarch ppc64 ppc64le
%global host_target PowerPC
%endif
%ifarch %ix86 x86_64
%global host_target X86
%endif
%ifarch aarch64
%global host_target AArch64
%endif
%ifarch %{arm}
%global host_target ARM
%endif

%ifnarch s390x
%global amdgpu ;AMDGPU
%endif

Name:		mesa-private-llvm
Version:	3.8.1
Release:	1%{?dist}
Summary:	llvm engine for Mesa

Group:          System Environment/Libraries
License:	NCSA
URL:		http://llvm.org
Source0:	http://llvm.org/releases/%{version}/llvm-%{version}.src.tar.xz
Source100:	llvm-config.h

# recognize s390 as SystemZ when configuring build
#Patch0:		llvm-3.7.1-cmake-s390.patch

Patch1: fix-cmake-include.patch
Patch2: llvm-3.8.1-rhel-7.3.patch

BuildRequires:	cmake
BuildRequires:	zlib-devel
%if %{with gold}
BuildRequires:  binutils-devel
%endif
BuildRequires:  libstdc++-static
BuildRequires:  python

%description
This package contains the LLVM-based runtime support for Mesa.  It is not a
fully-featured build of LLVM, and use by any package other than Mesa is not
supported.

%package devel
Summary:	Libraries and header files for LLVM
Requires:	%{name}%{?_isa} = %{version}-%{release}

%description devel
This package contains library and header files needed to build the LLVM
support in Mesa.

%prep
%setup -q -n llvm-%{version}.src
#patch0 -p1 -b .s390
%patch1 -p1 -b .fixinc
%patch2 -p1

%build

sed -i 's|ActiveIncludeDir = ActivePrefix + "/include|&/mesa-private|g' tools/llvm-config/llvm-config.cpp

mkdir -p _build
cd _build

# force off shared libs as cmake macros turns it on.
%cmake .. \
	-DINCLUDE_INSTALL_DIR=%{_includedir}/mesa-private \
	-DLLVM_VERSION_SUFFIX="-mesa" \
	-DBUILD_SHARED_LIBS:BOOL=OFF \
	-DCMAKE_BUILD_TYPE=RelWithDebInfo \
	-DCMAKE_SHARED_LINKER_FLAGS="-Wl,-Bsymbolic -static-libstdc++" \
%if 0%{?__isa_bits} == 64
	-DLLVM_LIBDIR_SUFFIX=64 \
%else
	-DLLVM_LIBDIR_SUFFIX= \
%endif
	\
	-DLLVM_TARGETS_TO_BUILD="%{host_target}%{?amdgpu}" \
	-DLLVM_ENABLE_LIBCXX:BOOL=OFF \
	-DLLVM_ENABLE_ZLIB:BOOL=ON \
	-DLLVM_ENABLE_FFI:BOOL=OFF \
	-DLLVM_ENABLE_RTTI:BOOL=OFF \
%if %{with gold}
	-DLLVM_BINUTILS_INCDIR=%{_includedir} \
%endif
	\
	-DLLVM_BUILD_RUNTIME:BOOL=ON \
	\
	-DLLVM_INCLUDE_TOOLS:BOOL=ON \
	-DLLVM_BUILD_TOOLS:BOOL=ON \
	\
	-DLLVM_INCLUDE_TESTS:BOOL=ON \
	-DLLVM_BUILD_TESTS:BOOL=ON \
	\
	-DLLVM_INCLUDE_EXAMPLES:BOOL=OFF \
	-DLLVM_BUILD_EXAMPLES:BOOL=OFF \
	\
	-DLLVM_INCLUDE_UTILS:BOOL=ON \
	-DLLVM_INSTALL_UTILS:BOOL=OFF \
	\
	-DLLVM_INCLUDE_DOCS:BOOL=OFF \
	-DLLVM_BUILD_DOCS:BOOL=OFF \
	-DLLVM_ENABLE_SPHINX:BOOL=OFF \
	-DLLVM_ENABLE_DOXYGEN:BOOL=OFF \
	\
	-DLLVM_BUILD_LLVM_DYLIB:BOOL=ON \
	-DLLVM_DYLIB_EXPORT_ALL:BOOL=ON \
	-DLLVM_LINK_LLVM_DYLIB:BOOL=ON \
	-DLLVM_BUILD_EXTERNAL_COMPILER_RT:BOOL=ON \
	-DLLVM_INSTALL_TOOLCHAIN_ONLY:BOOL=OFF

make %{?_smp_mflags} VERBOSE=1

%install
cd _build
make install DESTDIR=%{buildroot}

# fix multi-lib
mv -v %{buildroot}%{_bindir}/llvm-config %{buildroot}%{_bindir}/%{name}-config-%{__isa_bits}
mv -v %{buildroot}%{_includedir}/mesa-private/llvm/Config/llvm-config{,-%{__isa_bits}}.h
install -m 0644 %{SOURCE100} %{buildroot}%{_includedir}/mesa-private/llvm/Config/llvm-config.h

rm -f %{buildroot}%{_libdir}/*.a

rm -f %{buildroot}%{_libdir}/libLLVM.so

# remove documentation makefiles:
# they require the build directory to work
find examples -name 'Makefile' | xargs -0r rm -f

# RHEL: strip out most binaries, most libs, and man pages
ls %{buildroot}%{_bindir}/* | grep -v bin/mesa-private | xargs rm -f
ls %{buildroot}%{_libdir}/* | grep -v libLLVM | xargs rm -f
rm -rf %{buildroot}%{_mandir}/man1

# RHEL: Strip out some headers Mesa doesn't need
rm -rf %{buildroot}%{_includedir}/mesa-private/llvm/{Assembly}
rm -rf %{buildroot}%{_includedir}/mesa-private/llvm/Option
rm -rf %{buildroot}%{_includedir}/mesa-private/llvm/TableGen
rm -rf %{buildroot}%{_includedir}/llvm-c/lto.h

# RHEL: Strip out cmake build foo
rm -rf %{buildroot}%{_datadir}/llvm/cmake

%check
cd _build
# 3.8.1 note: skx failures are XFAIL. the skylake backport does not wire
# up AVX512 for skylake, but the tests are from code that expects that.
# safe to ignore.
make check-all || :

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%doc LICENSE.TXT
%{_libdir}/libLLVM-3.8*-mesa.so

%files devel
%{_bindir}/%{name}-config-%{__isa_bits}
%{_includedir}/mesa-private/llvm
%{_includedir}/mesa-private/llvm-c

%changelog
* Wed Jul 13 2016 Adam Jackson <ajax@redhat.com> - 3.8.1-1
- Update to 3.8.1
- Sync some x86 getHostCPUName updates from trunk

* Tue Jun 14 2016 Dave Airlie <airlied@redhat.com> - 3.8.0-2
- drop private cmake build

* Thu Mar 10 2016 Dave Airlie <airlied@redhat.com> 3.8.0-1
- llvm 3.8.0 final release

* Thu Mar 03 2016 Dave Airlie <airlied@redhat.com> 3.8.0-0.2
- llvm 3.8.0 rc3 release

* Fri Feb 19 2016 Dave Airlie <airlied@redhat.com> 3.8.0-0.1
- llvm 3.8.0 rc2 release

* Tue Feb 16 2016 Dan Horák <dan[at][danny.cz> 3.7.1-7
- recognize s390 as SystemZ when configuring build

* Sat Feb 13 2016 Dave Airlie <airlied@redhat.com> 3.7.1-6
- export C++ API for mesa.

* Sat Feb 13 2016 Dave Airlie <airlied@redhat.com> 3.7.1-5
- reintroduce llvm-static, clang needs it currently.

* Fri Feb 12 2016 Dave Airlie <airlied@redhat.com> 3.7.1-4
- jump back to single llvm library, the split libs aren't working very well.

* Fri Feb 05 2016 Dave Airlie <airlied@redhat.com> 3.7.1-3
- add missing obsoletes (#1303497)

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 3.7.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Thu Jan 07 2016 Jan Vcelak <jvcelak@fedoraproject.org> 3.7.1-1
- new upstream release
- enable gold linker

* Wed Nov 04 2015 Jan Vcelak <jvcelak@fedoraproject.org> 3.7.0-100
- fix Requires for subpackages on the main package

* Tue Oct 06 2015 Jan Vcelak <jvcelak@fedoraproject.org> 3.7.0-100
- initial version using cmake build system
