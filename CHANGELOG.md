# Changelog

## [1.1.0] - 2026-03-30

### Added

- Neon-style banner image added to README.md header.
- .github/workflows/changelog.yml: Auto-update CHANGELOG on every push to main.


## [1.0.0] - 2026-03-29

### Added
- Initial release
- README.md: Full ROCm 5.x → 6.x migration guide covering parallel install, breaking changes, Ubuntu 22.04, WSL2, Docker, and rollback
- verify_rocm.py: Health check script (ROCm version, GPU detection, PyTorch, MIOpen, memory)
- compatibility_matrix.md: Full GPU × ROCm × PyTorch × OS version matrix
- LICENSE: MIT
- .github/FUNDING.yml

### Covers
- ROCm 5.7 through 6.3.3
- PyTorch 2.1 through 2.7
- Ubuntu 20.04, 22.04, 24.04
- WSL2 on Windows 11
- Docker with AMD ROCm images

[1.1.0]: https://github.com/ChharithOeun/rocm-migration-5x-to-6x/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/ChharithOeun/rocm-migration-5x-to-6x/releases/tag/v1.0.0
