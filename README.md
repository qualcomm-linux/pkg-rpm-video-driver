<!--
Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
SPDX-License-Identifier: BSD-3-Clause
-->

# pkg-rpm-video-driver

RPM packaging repository for the **Qualcomm Video Driver** (`iris-vpu` DKMS
kernel module) targeting **CentOS 10 Stream** (`c10s`).

This repository does **not** contain the driver source code. It holds the
RPM spec file and the SHA-512 checksum (`sources`) that together allow
GitHub CI to fetch the upstream source tarball, verify its integrity, and
build distributable RPM packages.

---

## About the Video Driver

The video driver provides VPU (Video Processing Unit) support for Qualcomm
Snapdragon targets. It is required to use VPU hardware for hardware-accelerated
video encode and decode.

The VPU is a multi-pipe hardware block that offloads video stream processing
from the application processor (AP). It communicates with the AP through a
well-defined protocol called the **Host Firmware Interface (HFI)**, which
provides fine-grained and asynchronous control over individual hardware
features.

**Supported codecs:**

| Operation | Codecs |
|-----------|--------|
| Decode | H.264, H.265, VP9, AV1 |
| Encode | H.264, H.265 |

**Driver highlights:**

- V4L2-compliant driver with M2M and STREAMING capability.
- Centralized resource management and core/instance state management.
- Platform-specific capability definitions — single point of control to
  enable or disable features per platform.
- Handles standard video sequences: DRC, Drain, Seek, EOS.
- Asynchronous communication with hardware for low-latency use cases.
- Output and capture planes controlled independently, allowing per-plane
  reconfiguration.
- Native hardware support for the LAST flag, required for port
  reconfiguration and DRAIN sequences per V4L2 guidelines.

**Supported platforms:** `hamoa`, `lemans`, `monaco`, `kodiak`, `purwa`
(iris2 / iris3 variants).

The upstream driver source lives at:
<https://github.com/qualcomm-linux/video-driver>

---

## Repository Layout

```
video-driver.spec   # RPM spec — build instructions, version, dependencies
sources             # SHA-512 checksum of the upstream source tarball
LICENSE.txt         # Repository license
README.md           # This file
```

### `video-driver.spec`

Defines how the RPM is built:

- **Package name / version:** `video-driver-<version>`
- **Build type:** `noarch` DKMS package — the kernel module is compiled on
  the target machine at install time, not at RPM build time.
- **Runtime dependencies:** `dkms` (required), `kernel-devel` (recommended).
- **Conflicts:** `qcom-iris-dkms` (the in-tree Qualcomm iris driver).
- **`%post` scriptlet:** registers the module with DKMS, builds it for the
  running kernel, blacklists the in-tree `qcom_iris` driver, and loads
  `iris_vpu`.
- **`%preun` scriptlet:** unloads `iris_vpu`, removes the DKMS registration,
  and cleans up blacklist and auto-load entries before package removal.

### `sources`

Contains the SHA-512 checksum of the upstream source tarball in
Fedora/CentOS dist-git format:

```
# Example:
SHA512 (video-driver-<version>.tar.gz) = <sha512-checksum>
```

The tarball itself is **never committed to git**. CI fetches it from the
upstream GitHub release URL recorded in `Source0:` inside the spec, then
verifies it against this checksum before building.

---

## CI Workflows

GitHub Actions workflows (`.github/workflows/`) automate the full
build-and-release cycle:

| Workflow | Trigger | What it does |
|---|---|---|
| `build-on-pr` | Pull request | Fetches the tarball, verifies the SHA-512 checksum, builds the RPM(s), and uploads them as workflow artifacts. |
| `pkg-release` | Manual (`Actions → Release → Run workflow`) | Builds and publishes the RPM(s) to Artifactory after a reviewer approves the `pkg-release-approval` gate. |

Download built RPMs from the **Artifacts** section of the `build-on-pr` run.

---

## Updating the Package Version

Two files must be updated together every time the upstream driver version
changes:

### 1. Update the spec file

Bump `Version:` in `video-driver.spec`. If the upstream tarball URL path
also changed, update `Source0:` accordingly.

```spec
# Example:
Version:  <new-version>
```

### 2. Recompute the checksum

Download the new tarball and regenerate `sources`:

```bash
# Example:
sha512sum --tag video-driver-<new-version>.tar.gz > sources
```

The resulting `sources` file should look like:

```
# Example:
SHA512 (video-driver-<new-version>.tar.gz) = <new-sha512-checksum>
```

### 3. Open a pull request

Commit both changes and open a PR against this branch. The `build-on-pr`
workflow will fetch the new tarball, verify the checksum, and build the
updated RPM(s).

### 4. Release

Once the PR is merged, request the maintainer to trigger **Actions → Release → Run workflow**
on this branch. After reviewer approval the new RPM(s) are published to Artifactory.

---

## Getting in Contact

Issues specific to the video driver source should be reported in the Issues
section of the upstream repository:
<https://github.com/qualcomm-linux/video-driver>

Issues specific to this RPM packaging repository (spec file, CI workflows,
checksum) should be reported in the Issues section of this repository.

---

## License

pkg-rpm-video-driver BSD 3-Clause License

**pkg-rpm-video-driver** is licensed under **BSD 3-Clause License** See [LICENSE.txt](https://github.com/qualcomm-linux/pkg-rpm-video-driver/blob/main/LICENSE.txt) for the full license text.

The video driver source code is released under **GPL-2.0-only**. See the
upstream repository for its full license text.
