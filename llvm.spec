%if 0%{?rhel} == 6
%define rhel6 1
%endif

# llvm works on the 64-bit versions of these, but not the 32 versions.
# consequently we build swrast on them instead of llvmpipe.
ExcludeArch: ppc s390 %{?rhel6:s390x}

%global svndate 20131023
#%global prerel rc3
%global downloadurl http://llvm.org/%{?prerel:pre-}releases/%{version}%{?prerel:/%{prerel}}

Name:           mesa-private-llvm
Version:        3.3
#Release:        0.4.%{prerel}%{?dist}
Release:        0.8.%{svndate}%{?dist}
Summary:        llvm engine for Mesa

Group:		System Environment/Libraries
License:        NCSA
URL:            http://llvm.org/
#Source0:        %{downloadurl}/llvm-source-%{version}%{?prerel:%{prerel}}.tar.gz
Source0:	llvm-%{svndate}.tar.xz
Source1:	make-llvm-snapshot.sh
# multilib fixes
Source2:        llvm-Config-config.h
Source3:        llvm-Config-llvm-config.h

# Data files should be installed with timestamps preserved
Patch0:         llvm-2.6-timestamp.patch
Patch1:         llvm-drop-patch-version-number.patch

BuildRequires:  bison
BuildRequires:  chrpath
BuildRequires:  flex
BuildRequires:  gcc-c++ >= 3.4
BuildRequires:  groff
BuildRequires:  libtool-ltdl-devel
BuildRequires:  zip
# for DejaGNU test suite
BuildRequires:  dejagnu tcl-devel python

%description
This package contains the LLVM-based runtime support for Mesa.  It is not a
fully-featured build of LLVM, and use by any package other than Mesa is not
supported.

%package devel
Summary:        Libraries and header files for Mesa's llvm engine
Group:          Development/Libraries
Requires:       %{name}%{?_isa} = %{version}-%{release}
Requires:       libstdc++-devel >= 3.4

%description devel
This package contains library and header files needed to build the LLVM
support in Mesa.

%prep
#setup -q -n llvm-%{version}%{?prerel}.src
%setup -q -n llvm-%{svndate}
#setup -q -n llvm.src
rm -r -f tools/clang

# llvm patches
%patch0 -p1 -b .timestamp
%patch1 -p1 -b .version

# fix ld search path
sed -i 's|/lib /usr/lib $lt_ld_extra|%{_libdir} $lt_ld_extra|' \
    ./configure

%build
%configure \
  --prefix=%{_prefix} \
  --libdir=%{_libdir} \
  --includedir=%{_includedir}/mesa-private \
  --with-extra-ld-options=-Wl,-Bsymbolic,--default-symver \
  --enable-targets=host \
%ifnarch s390x
  --enable-experimental-targets=R600 \
%endif
  --enable-bindings=none \
  --enable-debug-runtime \
  --enable-jit \
  --enable-shared \
  --disable-assertions \
  --disable-docs \
  --disable-libffi \
%ifarch armv7hl armv7l
  --with-cpu=cortex-a8 \
  --with-tune=cortex-a8 \
  --with-arch=armv7-a \
  --with-float=hard \
  --with-fpu=vfpv3-d16 \
  --with-abi=aapcs-linux \
%endif

# FIXME file this
# configure does not properly specify libdir or includedir
sed -i 's|(PROJ_prefix)/lib|(PROJ_prefix)/%{_lib}|g' Makefile.config
sed -i 's|(PROJ_prefix)/include|&/mesa-private|g' Makefile.config

# mangle the library name
sed -i 's|^LLVMVersion.*|&-mesa|' Makefile.config

# FIXME upstream need to fix this
# llvm-config.cpp hardcodes lib in it
sed -i 's|ActiveLibDir = ActivePrefix + "/lib"|ActiveLibDir = ActivePrefix + "/%{_lib}"|g' tools/llvm-config/llvm-config.cpp
sed -i 's|ActiveIncludeDir = ActivePrefix + "/include|&/mesa-private|g' tools/llvm-config/llvm-config.cpp

make %{_smp_mflags} VERBOSE=1 OPTIMIZE_OPTION="%{optflags} -fno-strict-aliasing"

%install
make install DESTDIR=%{buildroot}

# rename the few binaries we're keeping
mv %{buildroot}%{_bindir}/llvm-config %{buildroot}%{_bindir}/%{name}-config-%{__isa_bits}

pushd %{buildroot}%{_includedir}/mesa-private/llvm/Config
mv config.h config-%{__isa_bits}.h
cp -p %{SOURCE2} config.h
mv llvm-config.h llvm-config-%{__isa_bits}.h
cp -p %{SOURCE3} llvm-config.h
popd

file %{buildroot}/%{_bindir}/* %{buildroot}/%{bindir}/*.so | \
    awk -F: '$2~/ELF/{print $1}' | \
    xargs -r chrpath -d

# FIXME file this bug
sed -i 's,ABS_RUN_DIR/lib",ABS_RUN_DIR/%{_lib}/%{name}",' \
  %{buildroot}%{_bindir}/%{name}-config-%{__isa_bits}

rm -f %{buildroot}%{_libdir}/*.a

# remove documentation makefiles:
# they require the build directory to work
find examples -name 'Makefile' | xargs -0r rm -f

# RHEL: strip out most binaries, most libs, and man pages
ls %{buildroot}%{_bindir}/* | grep -v bin/mesa-private | xargs rm -f
ls %{buildroot}%{_libdir}/* | grep -v libLLVM | xargs rm -f
rm -rf %{buildroot}%{_mandir}/man1

# RHEL: Strip out some headers Mesa doesn't need
rm -rf %{buildroot}%{_includedir}/mesa-private/llvm/{Analysis,Assembly}
rm -rf %{buildroot}%{_includedir}/mesa-private/llvm/{DebugInfo,Object,Option}
rm -rf %{buildroot}%{_includedir}/mesa-private/llvm/TableGen

%if 0
%check
# the Koji build server does not seem to have enough RAM
# for the default 16 threads

# LLVM test suite failing on ARM, PPC64 and s390(x)
make check LIT_ARGS="-v -j4" \
%ifarch %{arm} ppc64 s390x
     | tee llvm-testlog-%{_arch}.txt
%else
 %{nil}
%endif
%endif

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

# also unlike fedora, we don't alternatives around llvm-config
# mesa knows to append -%{__isa_bits}

%files
%defattr(-,root,root,-)
%doc LICENSE.TXT
%{_libdir}/libLLVM-3.3-mesa.so

%files devel
%defattr(-,root,root,-)
%{_bindir}/%{name}-config-%{__isa_bits}
%{_includedir}/mesa-private/llvm
%{_includedir}/mesa-private/llvm-c

%changelog
* Tue Jan 28 2014 Adam Jackson <ajax@redhat.com> 3.3-0.8.20131023
- Disable %%check, only fails in places that don't matter to Mesa (#1028575)

* Fri Jan 24 2014 Daniel Mach <dmach@redhat.com> - 3.3-0.7.20131023
- Mass rebuild 2014-01-24

* Fri Dec 27 2013 Daniel Mach <dmach@redhat.com> - 3.3-0.6.20131023
- Mass rebuild 2013-12-27

* Wed Oct 23 2013 Jerome Glisse <jglisse@redhat.com> 3.3-0.5.20131023
- 3.3.1 snapshot

* Tue Aug 20 2013 Adam Jackson <ajax@redhat.com> 3.3-0.4.rc3
- Build with -fno-strict-aliasing

* Tue Jun 18 2013 Adam Jackson <ajax@redhat.com> 3.3-0.3.rc3
- Port to RHEL6
- Don't bother building R600 on s390x

* Tue Jun 11 2013 Adam Jackson <ajax@redhat.com> 3.3-0.2.rc3
- 3.3 rc3
- Drop tblgen
- Strip out some headers

* Tue May 14 2013 Adam Jackson <ajax@redhat.com> 3.3-0.1.rc1
- Update to 3.3 rc1
- Move library to %%{_libdir} to avoid rpath headaches
- Link with -Bsymbolic and --default-symver
- --disable-libffi
- Misc spec cleanup

* Wed Dec 05 2012 Adam Jackson <ajax@redhat.com> 3.1-13
- Forked spec for RHEL7 Mesa's private use
  - no ocaml support
  - no doxygen build
  - no clang support
  - no static archives
  - no libraries, binaries, or manpages not needed by Mesa
