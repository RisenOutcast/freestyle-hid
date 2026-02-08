# SPDX-FileCopyrightText: © 2020 The freestyle-hid Authors
# SPDX-License-Identifier: Apache-2.0
"""HID wrappers to access files with either hidraw or cython-hidapi."""

import abc
import pathlib
import os
from typing import BinaryIO, Optional, Union

try:
    import hid
except ImportError:
    hid = None

from ._exceptions import HIDError


class HidWrapper(abc.ABC):
    _handle: Union[BinaryIO, "hid.device"]

    def write(self, report: bytes) -> None:
        if len(report) > 65:
            raise HIDError(f"Invalid report length {len(report)}.")

        if hasattr(self._handle, "write"):
            written = self._handle.write(report)
        else:
            written = os.write(self._handle, report)

        if written is not None and written < 0:
            raise HIDError(f"Invalid write ({written}).")

    @abc.abstractmethod
    def read(self, size: int = 64) -> bytes:
        pass

    @staticmethod
    def open(
        device_path: Optional[pathlib.Path], vendor_id: int, product_id: Optional[int]
    ) -> "HidWrapper":
        if device_path:
            return HidRaw(device_path)
        else:
            assert product_id is not None
            return HidApi(vendor_id, product_id)


class HidRaw(HidWrapper):
    def __init__(self, device_path: pathlib.Path) -> None:
        if not device_path.exists():
            raise ValueError(f"Path {device_path} does not exist.")
        self._fd = os.open(str(device_path), os.O_RDWR)
        self._handle = self._fd

    def __del__(self):
        if hasattr(self, "_fd"):
            os.close(self._fd)

    def read(self, size: int = 64) -> bytes:
        return os.read(self._fd, size)


class HidApi(HidWrapper):
    _handle: "hid.device"

    def __init__(self, vendor_id: int, product_id: int) -> None:
        if hid is None:
            raise ValueError("cython-hidapi not found.")
        self._handle = hid.device()
        self._handle.open(vendor_id, product_id)

    def read(self, size: int = 64) -> bytes:
        # Standard blocking read (timeout=0 means non-blocking in hidapi, 
        # but we want blocking here so we rely on default or a long timeout)
        data = self._handle.read(size)
        return bytes(data)