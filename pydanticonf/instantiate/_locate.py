# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# ---
#
# This module contains code adapted from hydra._internal.utils._locate
# (BSD-3-Clause, Copyright (c) Facebook, Inc. and its affiliates.)
# Source: hydra/_internal/utils.py, lines 614-665
#
# The original code is available at:
# https://github.com/facebookresearch/hydra/blob/main/hydra/_internal/utils.py
#
# BSD-3-Clause license:
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Vendored _locate from hydra._internal.utils for dotted-path resolution.

Walks dotted segments one at a time, falling back to import_module on
AttributeError for each segment. Correctly resolves nested classes
(e.g. ``pkg.mod.Outer.Inner``).
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Any


def locate(path: str) -> Any:
    """Locate an object by name or dotted path, importing as necessary.

    Walks dotted segments one at a time, using getattr per segment with
    a fallback to import_module(parent.child) when getattr fails on a
    ModuleType. This correctly handles nested classes where intermediate
    segments are classes, not modules.

    Args:
        path: Dotted path string (e.g. "pkg.mod.Outer.Inner").

    Returns:
        The resolved object (class, function, etc.).

    Raises:
        ImportError: If the path is empty, contains empty segments,
            or cannot be resolved.
    """
    if path == "":
        raise ImportError("Empty path")

    parts = path.split(".")
    for part in parts:
        if not part:
            raise ValueError(f"Error loading '{path}': invalid dotstring." + "\nRelative imports are not supported.")

    part0 = parts[0]
    try:
        obj: Any = import_module(part0)
    except Exception as exc_import:
        raise ImportError(
            f"Error loading '{path}':\n{repr(exc_import)}" + f"\nAre you sure that module '{part0}' is installed?"
        ) from exc_import

    for m in range(1, len(parts)):
        part = parts[m]
        try:
            obj = getattr(obj, part)
        except AttributeError as exc_attr:
            parent_dotpath = ".".join(parts[:m])
            if isinstance(obj, ModuleType):
                mod = ".".join(parts[: m + 1])
                try:
                    obj = import_module(mod)
                    continue
                except ModuleNotFoundError as exc_import:
                    raise ImportError(
                        f"Error loading '{path}':\n{repr(exc_import)}"
                        + f"\nAre you sure that '{part}' is importable from module '{parent_dotpath}'?"
                    ) from exc_import
                except Exception as exc_import:
                    raise ImportError(f"Error loading '{path}':\n{repr(exc_import)}") from exc_import
            raise ImportError(
                f"Error loading '{path}':\n{repr(exc_attr)}"
                + f"\nAre you sure that '{part}' is an attribute of '{parent_dotpath}'?"
            ) from exc_attr

    return obj
