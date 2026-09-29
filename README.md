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

---

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

---

**Supported platforms:** `hamoa`, `lemans`, `monaco`, `kodiak`, `purwa`
(iris2 / iris3 variants).

The upstream driver source lives at:
<https://github.com/qualcomm-linux/video-driver>

---

## Getting in Contact

Issues specific to the video driver source should be reported in the Issues
section of the upstream repository:
<https://github.com/qualcomm-linux/video-driver>

Issues specific to this RPM packaging repository (spec file, CI workflows,
checksum) should be reported in the Issues section of this repository.

---

## Branch model

The main branch contains repository documentation and workflow support files.

| Branch | Role | Contents |
|---|---|---|
| `main` | Template + docs home. **Nothing is built here.** | This README, [docs/](docs/), community files, workflows. |
| `c10s` | **CentOS 10 Stream package branch — where you work.** | Your `<component>.spec` + `sources` at the root, plus the workflows. |

Future streams get their own branch (`c11s`, …) off the same model, so one repo
can carry a package for several distro versions without branching history.

---

## License

pkg-rpm-video-driver BSD 3-Clause License

**pkg-rpm-video-driver** is licensed under **BSD 3-Clause License** See [LICENSE.txt](https://github.com/qualcomm-linux/pkg-rpm-video-driver/blob/main/LICENSE.txt) for the full license text.
