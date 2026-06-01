# Changelog

## v0.5.1 - 2026-06-01

- Added shared Codex CLI discovery for Windows and macOS control flows.
- Improved Windows Codex CLI lookup for local app installs, PATH entries, and registry hints.
- Added clear `CODEX_CLI_PATH` guidance when the Codex CLI cannot be found.
- Standardized UTF-8 file and subprocess handling for Windows release builds.
- Included `codex_cli.py` in the Windows runtime packaging list.

## v0.5.0 - 2026-05-20

- Added the first Windows 11 installer path using PyInstaller and Inno Setup.
- Added a Windows Scheduled Task service helper for user-level background startup.
- Added a minimal Windows control app for starting, stopping, restarting, opening the Web UI, opening logs, and toggling Codex proxy mode.
- Updated Windows PowerShell helper scripts to use the Windows service CLI instead of macOS LaunchAgent actions.
- Added packaging guards to reject credentials, `.docx` files, macOS app bundles, and copied runtime dependency trees.
- Updated Windows documentation for the `0.5.0` installer build flow.
- Uploaded the Windows installer and existing `Codex-Proxy-Control-0.4.3-mac.dmg` to the `v0.5.0` GitHub release.
- Reorganized source into `src/core`, `platforms/mac`, and `platforms/windows`.
