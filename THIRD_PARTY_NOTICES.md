# Third-party notices

## Upstream parse-video

This repository is derived from `wujunwei928/parse-video` and retains its MIT License and original copyright notice in `LICENSE`.

## Python embeddable runtime

The Windows release package includes the official CPython 3.13.12 embeddable x64 runtime from `python.org`. Its `LICENSE.txt` is included alongside the runtime. The build script pins the official URL and verifies SHA-256 before packaging.

## FFmpeg, whisper.cpp and speech models

The current Windows RC package does not bundle FFmpeg, whisper.cpp, or a Whisper speech model. Its optional dependency helper can download a pinned Gyan FFmpeg essentials build (GPLv3), the official whisper.cpp Windows x64 release (MIT), and the `ggml-base.bin` model after explicit user confirmation and SHA-256 verification. These files remain outside the release ZIP and retain their own upstream terms.

## Go dependencies

The parser binary statically includes the Go modules declared in `go.mod`. A public release must preserve the applicable third-party license notices for those modules; generating the complete license inventory is a release gate, not yet claimed complete in this RC.
