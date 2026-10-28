# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.

Name:           iris-vpu
Version:        1.0.28
Release:        4%{?dist}
Summary:        DKMS package for MSM VIDC video driver (out-of-tree)
License:        GPL-2.0-only
URL:            https://github.com/qualcomm-linux/video-driver

Source0:        https://github.com/qualcomm-linux/video-driver/archive/refs/tags/v%{version}.tar.gz#/video-driver-%{version}.tar.gz
Source1:        dkms-build-wrapper.sh
Source2:        iris-vpu-dkms.dkms

Conflicts:      qcom-iris-dkms

BuildArch:      noarch

BuildRequires:  systemd-rpm-macros
Requires:       dkms
Recommends:     kernel-devel

%description
This package installs source for the iris_vpu kernel module and
registers it with DKMS so it is built automatically for the running
kernel via /lib/modules/${kernelver}/build.

The driver supports multiple Qualcomm platforms and automatically
detects the platform from the device tree compatible string to
enable the appropriate configuration macros (CONFIG_MSM_VIDC_QLI).

Supported platforms: hamoa, lemans, monaco, kodiak, purwa.

# Prep — unpack the source tarball
%prep
%autosetup -n video-driver-%{version}

%build

%install
DKMS_SRC_DIR=%{buildroot}%{_usrsrc}/%{name}-%{version}
install -d "${DKMS_SRC_DIR}"

cp -r . "${DKMS_SRC_DIR}/"

sed -i '/^ccflags-y += -Werror$/a ccflags-y += -Wno-error=attributes' \
    "${DKMS_SRC_DIR}/video/Kbuild"

install -Dm0644 %{SOURCE2} "${DKMS_SRC_DIR}/dkms.conf"
sed -i 's/#MODULE_VERSION#/%{version}/g' "${DKMS_SRC_DIR}/dkms.conf"

install -d %{buildroot}%{_modprobedir}
install -m 644 pkg-iris-vpu/debian/modprobe.d/iris-vpu-dkms.conf \
              %{buildroot}%{_modprobedir}/iris-vpu-dkms.conf

install -d %{buildroot}%{_modulesloaddir}
echo iris_vpu > %{buildroot}%{_modulesloaddir}/iris-vpu-dkms.conf

install -d "${DKMS_SRC_DIR}/scripts"
install -m 755 pkg-iris-vpu/scripts/detect-platform.sh     "${DKMS_SRC_DIR}/scripts/"
install -m 755 pkg-iris-vpu/scripts/set-build-env.sh       "${DKMS_SRC_DIR}/scripts/"
install -m 755 pkg-iris-vpu/scripts/cross-compile.sh       "${DKMS_SRC_DIR}/scripts/"

install -Dm0755 %{SOURCE1} "${DKMS_SRC_DIR}/scripts/dkms-build-wrapper.sh"

%files
%license LICENSE.txt
%doc pkg-iris-vpu/README.md
%{_usrsrc}/%{name}-%{version}/
%{_modprobedir}/iris-vpu-dkms.conf
%{_modulesloaddir}/iris-vpu-dkms.conf

%post
%{_sbindir}/dkms add -m iris-vpu -v %{version} || :
%{_sbindir}/dkms autoinstall -m iris-vpu -v %{version} || :

%preun
if [ "$1" -eq 0 ]; then
    %{_sbindir}/dkms remove -m iris-vpu -v %{version} --all || :
fi

%changelog
* Wed Sep 23 2026 Gangabhavani Yenugula <gyenugul@qti.qualcomm.com> - 1.0.28-4
- Follow DKMS packaging guidelines: drop scriptlet-driven modprobe/rmmod
  and manual DKMS-build recovery logic from %%post/%%preun; leave module
  (un)loading to the administrator and to DKMS's own kernel hooks.

* Tue Jul 28 2026 Nagesh Jamakhandi <njamakha@qti.qualcomm.com> - 1.0.20-3
- Fix DKMS build compatibility with newer kernels
- Improve compiler compatibility
- Fix DKMS build failure reporting

* Mon Jul 27 2026 Nagesh Jamakhandi <njamakha@qti.qualcomm.com> - 1.0.20-2
- Improve DKMS build handling for custom kernels
- Fix module discovery and installation paths
- Improve installation robustness and error messaging
