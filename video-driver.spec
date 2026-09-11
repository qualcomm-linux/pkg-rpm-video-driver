# SPDX-License-Identifier: GPL-2.0-only
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.

Name:           iris-vpu
Version:        1.0.20
Release:        3%{?dist}
Summary:        DKMS package for MSM VIDC video driver (out-of-tree)
License:        GPL-2.0-only
URL:            https://github.com/qualcomm-linux/video-driver

Source0:        https://github.com/qualcomm-linux/video-driver/archive/refs/tags/v%{version}.tar.gz#/video-driver-%{version}.tar.gz

# Conflicts with the in-tree Qualcomm iris driver
Conflicts:      qcom-iris-dkms

BuildArch:      noarch

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
# 1. Install driver source into DKMS source tree
DKMS_SRC_DIR=%{buildroot}/usr/src/%{name}-%{version}
install -d "${DKMS_SRC_DIR}"

cp -r . "${DKMS_SRC_DIR}/"

sed -i '/^ccflags-y += -Werror$/a ccflags-y += -Wno-error=attributes' \
    "${DKMS_SRC_DIR}/video/Kbuild"

# 2. Install dkms.conf with the correct version substituted.
sed -e "s/PACKAGE_VERSION=\"[^\"]*\"/PACKAGE_VERSION=\"%{version}\"/" \
    -e '/^CLEAN[[:space:]]*=/d' \
    -e '/^REMAKE_INITRD[[:space:]]*=/d' \
    -e 's|BUILT_MODULE_LOCATION\[0\]="\."|BUILT_MODULE_LOCATION[0]="video"|' \
    pkg-iris-vpu/dkms.conf > "${DKMS_SRC_DIR}/dkms.conf"

# 3. Install modprobe blacklist — blacklists qcom_iris (in-tree driver)
install -d %{buildroot}/usr/lib/modprobe.d
install -m 644 pkg-iris-vpu/debian/modprobe.d/iris-vpu-dkms.conf \
              %{buildroot}/usr/lib/modprobe.d/iris-vpu-dkms.conf

# 4. Install iris-vpu load helper script
install -d %{buildroot}/usr/lib/iris-vpu-dkms
install -m 755 pkg-iris-vpu/debian/iris-vpu-load.sh \
              %{buildroot}/usr/lib/iris-vpu-dkms/iris-vpu-load.sh

# 5. Install helper scripts required by dkms-build-wrapper at DKMS build time
install -d "${DKMS_SRC_DIR}/scripts"
install -m 755 pkg-iris-vpu/scripts/detect-platform.sh     "${DKMS_SRC_DIR}/scripts/"
install -m 755 pkg-iris-vpu/scripts/set-build-env.sh       "${DKMS_SRC_DIR}/scripts/"
install -m 755 pkg-iris-vpu/scripts/cross-compile.sh       "${DKMS_SRC_DIR}/scripts/"

cat > "${DKMS_SRC_DIR}/scripts/dkms-build-wrapper.sh" << 'WRAPPER_EOF'

echo "Starting DKMS build for iris-vpu..."

KERNEL_VERSION="${kernelver:-$(uname -r)}"
KERNEL_ARCH="${arch:-$(uname -m)}"
echo "Target kernel: $KERNEL_VERSION ($KERNEL_ARCH)"

if [[ "$KERNEL_VERSION" == *"-dirty" ]] || \
   [[ "$KERNEL_VERSION" == *"rc"* ]]   || \
   [[ "$KERNEL_VERSION" =~ -g[0-9a-f]{7,} ]]; then
    echo "Custom/development kernel detected, enabling basic compatibility..."
    export DKMS_DISABLE_APPORT=1
    export IGNORE_CC_MISMATCH=1
fi

echo "Detecting platform from device tree..."
COMPATIBLE=$($(dirname "$0")/detect-platform.sh 2>/dev/null) || true

if [ -n "$COMPATIBLE" ]; then
    echo "Detected compatible: $COMPATIBLE"
    # Setup build environment for the detected platform.
    echo "Setting up build environment..."
    source "$(dirname "$0")/set-build-env.sh" "$COMPATIBLE" || true
else
    echo "Warning: Platform detection failed or returned empty result." >&2
    echo "Falling back to default QLI configuration (qli_video.conf)." >&2
fi

MAKE_ARGS="M=$(pwd) VIDEO_ROOT=$(pwd) KERNEL_SRC=/lib/modules/${KERNEL_VERSION}/build modules"
if [[ "$KERNEL_VERSION" == *"-dirty" ]]; then
    MAKE_ARGS="$MAKE_ARGS CONFIG_CC_VERSION_TEXT=\"\""
fi

echo "Building kernel module..."
make -C "/lib/modules/${KERNEL_VERSION}/build" $MAKE_ARGS
BUILD_STATUS=$?
if [ $BUILD_STATUS -ne 0 ]; then
    echo "Error: kernel module build failed with exit status $BUILD_STATUS" >&2
    exit $BUILD_STATUS
fi

echo "Build completed successfully!"
WRAPPER_EOF
chmod 755 "${DKMS_SRC_DIR}/scripts/dkms-build-wrapper.sh"

%files
%license LICENSE.txt
%doc pkg-iris-vpu/README.md
/usr/src/%{name}-%{version}/
/usr/lib/modprobe.d/iris-vpu-dkms.conf
/usr/lib/iris-vpu-dkms/iris-vpu-load.sh

%post

KERNEL_VERSION=$(uname -r)
MODULE_NAME="iris-vpu"
DRIVER_VERSION="%{version}"
BLACKLIST_FILE="/etc/modprobe.d/blacklist-video.conf"
DKMS_BUILD_SUCCESS=false

echo "Configuring iris-vpu-dkms..."

# 1. Clean up any leftover #MODULE_VERSION# entries from previous buggy installs
if dkms status 2>/dev/null | grep -q 'iris-vpu/#MODULE_VERSION#'; then
    dkms remove -m iris-vpu -v '#MODULE_VERSION#' --all 2>/dev/null || true
    rm -rf '/var/lib/dkms/iris-vpu/#MODULE_VERSION#' 2>/dev/null || true
fi

# 2. Register module source with DKMS
echo "Registering iris-vpu module source with DKMS..."
dkms add -m "$MODULE_NAME" -v "$DRIVER_VERSION" 2>/dev/null || true

# 3. Build the module via DKMS
echo "Building iris-vpu module via DKMS..."
if dkms build --force -m "$MODULE_NAME" -v "$DRIVER_VERSION" -k "$KERNEL_VERSION"; then
    DKMS_BUILD_SUCCESS=true
else
    echo "Warning: DKMS build failed for kernel $KERNEL_VERSION."
    echo "Attempting automatic recovery..."

    MODULE_PATH="/var/lib/dkms/iris-vpu/$DRIVER_VERSION/build/video/iris_vpu.ko"
    if [ -f "$MODULE_PATH" ]; then
        echo "Module file found at $MODULE_PATH, proceeding with manual installation..."
        TARGET_DIR="/lib/modules/$KERNEL_VERSION/extra/dkms"
        TARGET_FILE="$TARGET_DIR/iris_vpu.ko"
        if mkdir -p "$TARGET_DIR" && cp "$MODULE_PATH" "$TARGET_FILE" && depmod -a; then
            if modprobe iris_vpu 2>/dev/null; then
                modprobe -r iris_vpu 2>/dev/null || true
                DKMS_BUILD_SUCCESS=true
                touch "/var/lib/dkms/iris-vpu-overlay.flag"
                echo "Manual recovery succeeded."
            else
                echo "Warning: Module copied but could not be loaded — will retry on next boot."
            fi
        else
            echo "Warning: Manual recovery failed (copy/depmod error)."
        fi
    else
        echo "Warning: Module file not found at $MODULE_PATH"
        echo "The iris-vpu kernel module could not be built for kernel $KERNEL_VERSION."
        echo "Possible causes:"
        echo "  - Kernel headers for $KERNEL_VERSION are not installed."
        echo "    Install them with: dnf install kernel-devel-$KERNEL_VERSION"
        echo "  - The platform was not detected by detect-platform.sh."
        echo "    Check /var/lib/dkms/iris-vpu/$DRIVER_VERSION/build/make.log for details."
        echo "The package has been installed; re-run 'dkms build -m iris-vpu -v $DRIVER_VERSION'"
        echo "after installing the correct kernel headers."
    fi
fi

# 4. Install the DKMS module (skip if manual recovery was used)
if [ "$DKMS_BUILD_SUCCESS" = true ]; then
    DKMS_TARGET_FILE="/lib/modules/$KERNEL_VERSION/extra/dkms/iris_vpu.ko"
    if [ ! -f "$DKMS_TARGET_FILE" ]; then
        echo "Installing iris-vpu module via DKMS..."
        if ! dkms install -m "$MODULE_NAME" -v "$DRIVER_VERSION" -k "$KERNEL_VERSION"; then
            echo "Warning: DKMS install step failed — module may still be usable."
        fi
    fi
    echo "SUCCESS: iris-vpu module built and installed successfully!"
fi

# 5. Save current qcom_iris state for potential rollback
QCOM_IRIS_WAS_LOADED=false
if lsmod | grep -q "qcom_iris"; then
    QCOM_IRIS_WAS_LOADED=true
fi

# 6. Unload qcom_iris to free hardware resources
if [ "$QCOM_IRIS_WAS_LOADED" = true ]; then
    echo "Unloading qcom_iris module..."
    modprobe -r qcom_iris 2>/dev/null || true
fi

# 7. Blacklist qcom_iris in /etc/modprobe.d/ (runtime, not initramfs-managed)
echo "Adding qcom_iris to module blacklist..."
if [ -f "$BLACKLIST_FILE" ]; then
    if ! grep -q "blacklist qcom_iris" "$BLACKLIST_FILE"; then
        echo "" >> "$BLACKLIST_FILE"
        echo "# Added by iris-vpu RPM package" >> "$BLACKLIST_FILE"
        echo "blacklist qcom_iris" >> "$BLACKLIST_FILE"
        echo "install qcom_iris /bin/true" >> "$BLACKLIST_FILE"
    fi
else
    mkdir -p /etc/modprobe.d
    {
        echo "# Blacklist for iris-vpu RPM package"
        echo "blacklist qcom_iris"
        echo "install qcom_iris /bin/true"
    } > "$BLACKLIST_FILE"
fi

# 8. Load iris_vpu module (only if the build succeeded)
if [ "$DKMS_BUILD_SUCCESS" = true ]; then
    echo "Loading iris-vpu module..."
    if modprobe iris_vpu 2>/dev/null; then
        if lsmod | grep -q "^iris_vpu "; then
            echo "SUCCESS: iris-vpu module loaded!"
            echo "iris_vpu" > /etc/modules-load.d/iris-vpu.conf
            echo "iris-vpu-dkms configuration completed successfully!"
        else
            echo "Warning: iris_vpu loaded but not detected in lsmod — rolling back..."
            modprobe -r iris_vpu 2>/dev/null || true
            if [ -f "$BLACKLIST_FILE" ]; then
                grep -v "blacklist qcom_iris" "$BLACKLIST_FILE" | \
                    grep -v "install qcom_iris /bin/true" | \
                    grep -v "# Added by iris-vpu RPM package" > "${BLACKLIST_FILE}.tmp" && \
                    mv "${BLACKLIST_FILE}.tmp" "$BLACKLIST_FILE" || true
            fi
            [ "$QCOM_IRIS_WAS_LOADED" = true ] && modprobe qcom_iris 2>/dev/null || true
        fi
    else
        echo "Warning: Failed to load iris-vpu module immediately."
        echo "iris_vpu will be loaded automatically on next boot."
        echo "iris_vpu" > /etc/modules-load.d/iris-vpu.conf
    fi
fi

exit 0

%preun

KERNEL_VERSION=$(uname -r)
DRIVER_VERSION="%{version}"
MODULE_NAME="iris-vpu"

echo "Preparing to remove iris-vpu-dkms..."

# 1. Unload iris_vpu module if loaded
if lsmod | grep -q "^iris_vpu "; then
    echo "Unloading iris_vpu module..."
    modprobe -r iris_vpu 2>/dev/null || {
        echo "Warning: Failed to unload iris_vpu module — reboot may be required"
    }
fi

# 2. Clean up any leftover #MODULE_VERSION# entries
if dkms status 2>/dev/null | grep -q 'iris-vpu/#MODULE_VERSION#'; then
    dkms remove -m iris-vpu -v '#MODULE_VERSION#' --all 2>/dev/null || true
    rm -rf '/var/lib/dkms/iris-vpu/#MODULE_VERSION#' 2>/dev/null || true
fi

# 3. Remove DKMS module registration
if dkms status 2>/dev/null | grep -q "$MODULE_NAME.*$DRIVER_VERSION"; then
    echo "Removing iris-vpu DKMS module..."
    dkms remove -m "$MODULE_NAME" -v "$DRIVER_VERSION" --all 2>/dev/null || {
        echo "Warning: Failed to remove DKMS module"
    }
fi

# 4. Check for overlay installation and clean up manually installed files
OVERLAY_FLAG="/var/lib/dkms/iris-vpu-overlay.flag"
if [ -f "$OVERLAY_FLAG" ]; then
    echo "Detected overlay installation, cleaning up..."
    MANUAL_MODULE_FILE="/lib/modules/$KERNEL_VERSION/extra/dkms/iris_vpu.ko"
    [ -f "$MANUAL_MODULE_FILE" ] && rm -f "$MANUAL_MODULE_FILE" || true
    rm -f "$OVERLAY_FLAG" || true
    DKMS_DIR="/lib/modules/$KERNEL_VERSION/extra/dkms"
    [ -d "$DKMS_DIR" ] && [ -z "$(ls -A "$DKMS_DIR" 2>/dev/null)" ] && rmdir "$DKMS_DIR" || true
fi

# 5. Remove auto-load configuration
rm -f /etc/modules-load.d/iris-vpu.conf || true
sed -i '/^iris_vpu$/d' /etc/modules 2>/dev/null || true

# 6. Remove legacy blacklist entry added by %post
rm -f /etc/modprobe.d/blacklist-video.conf || true

echo "iris-vpu pre-removal completed."
exit 0

%changelog
* Mon Jul 28 2026 Qualcomm Technologies, Inc. <linux-qcom@qualcomm.com> - 1.0.20-3
- Fix: pass KERNEL_SRC=/lib/modules/$kernelver/build to make so that
  video/Kbuild's UBWC-helpers detection (grep on $(KERNEL_SRC)/include/...)
  succeeds; without it MSM_VIDC_HAS_QCOM_UBWC_HELPERS is unset and the
  driver redefines qcom_ubwc_* functions already present in the kernel header,
  causing redefinition errors
- Fix: patch video/Kbuild in %%install to append
  "ccflags-y += -Wno-error=attributes" after "ccflags-y += -Werror"; this
  allows building with GCC < 16 against kernels built with GCC 16+ where
  the 'counted_by' attribute is used in kernel headers but not supported by
  the older compiler (the more-specific flag must follow -Werror to win)
- Fix: capture make exit status explicitly in dkms-build-wrapper.sh and
  exit with it; previously the wrapper always exited 0 because
  "echo Build completed successfully!" was the last command, masking make
  failures from DKMS ("Building module(s)... done." with no .ko produced)

* Mon Jul 28 2026 Qualcomm Technologies, Inc. <linux-qcom@qualcomm.com> - 1.0.20-2
- Fix: remove "set -e" from dkms-build-wrapper.sh; platform detection is
  best-effort — failure now falls back to the default QLI config instead of
  aborting the DKMS build with exit status 1
- Fix: detect custom kernels with git-hash version suffixes
  (e.g. 6.18.37-g48143db58c4c) in addition to -dirty and rc kernels
- Fix: use DKMS-provided $kernelver instead of $(uname -r) in the wrapper
  so cross-version builds are supported
- Fix: change BUILT_MODULE_LOCATION[0] from "." to "video" in dkms.conf;
  the module is built in the video/ subdirectory (per Kbuild: obj-m := video/)
  so DKMS must look there after the build completes
- Fix: remove deprecated CLEAN and REMAKE_INITRD directives from installed
  dkms.conf (caused DKMS 3.4.1 warnings and potential build failures)
- Fix: remove "set -e" from %%post scriptlet; RPM scriptlets must always
  exit 0 to avoid aborting the dnf transaction on DKMS build failures
- Fix: add --force to "dkms build" to ensure a clean rebuild even when a
  partial build state is left from a previous failed attempt
- Fix: blacklist qcom_iris regardless of DKMS build outcome so the in-tree
  driver does not reload on next boot
- Fix: write iris_vpu to modules-load.d even when modprobe succeeds but
  the module is not yet visible in lsmod (timing race)
- Improve: add explicit "exit 0" at end of %%post and %%preun scriptlets
- Improve: add Recommends: kernel-devel to hint at missing kernel headers
- Improve: expand error messages to guide users when DKMS build fails

* Thu Jul 24 2025 Qualcomm Technologies, Inc. <linux-qcom@qualcomm.com> - 1.0.20-1
- Initial RPM packaging of iris-vpu DKMS driver (translated from Debian pkg-iris-vpu)
- Supports QLI platforms: lemans, hamoa, monaco, kodiak, purwa (iris2/iris3 variants)
- Blacklists in-tree qcom_iris driver on install
