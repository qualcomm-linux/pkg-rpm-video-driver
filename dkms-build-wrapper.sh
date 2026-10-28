#!/bin/bash
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.

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
