---
status: current
created: 2026-06-19
verdict: NO
---

# ESP32 baseline server URL switch

Question: can the upstream baseline firmware switch from official/16302 server to a local xinnan-tech server without reflashing?

Verdict: **NO** for the user-facing baseline path. The firmware can persist server endpoints, but the path that writes them is the OTA check response; the baseline firmware's OTA URL itself defaults to the official endpoint and there is no Wi-Fi config page, button path, menu, or built-in MCP tool that writes `wifi/ota_url` or `websocket/url`.

Evidence:

- `esp/xiaozhi-esp32/README_zh.md:107` says the beginner path is prebuilt firmware flashing; `esp/xiaozhi-esp32/README_zh.md:111` says firmware defaults to the official `xiaozhi.me` server. The console mentioned at `esp/xiaozhi-esp32/README_zh.md:130` is for large-model configuration after connecting to the official server, not choosing the transport endpoint.
- `esp/xiaozhi-esp32/main/Kconfig.projbuild:3` defines `CONFIG_OTA_URL`; `esp/xiaozhi-esp32/main/Kconfig.projbuild:7` says this OTA URL is used to check firmware and server address. This is a build-time default.
- `esp/xiaozhi-esp32/main/ota.cc:46` reads `Settings("wifi").GetString("ota_url")`; `esp/xiaozhi-esp32/main/ota.cc:49` falls back to `CONFIG_OTA_URL`. Repo search found no baseline writer for `ota_url`.
- `esp/xiaozhi-esp32/main/ota.cc:167` parses a `websocket` object from the OTA response; `esp/xiaozhi-esp32/main/ota.cc:170` opens `Settings("websocket", true)` and `esp/xiaozhi-esp32/main/ota.cc:175` writes OTA-provided keys into NVS.
- `esp/xiaozhi-esp32/main/protocols/websocket_protocol.cc:83` opens the audio channel; `esp/xiaozhi-esp32/main/protocols/websocket_protocol.cc:85` reads `websocket/url`; `esp/xiaozhi-esp32/main/protocols/websocket_protocol.cc:175` connects to that URL.
- `esp/xiaozhi-esp32/main/boards/common/wifi_board.cc:159` enters Wi-Fi config mode; `esp/xiaozhi-esp32/main/boards/common/wifi_board.cc:166` starts hotspot provisioning and `esp/xiaozhi-esp32/main/boards/common/wifi_board.cc:178` starts BluFi. `esp/xiaozhi-esp32/docs/blufi_zh.md:17` describes BluFi sending only Wi-Fi SSID/password.
- `esp/xiaozhi-esp32/main/boards/otto-robot/otto_robot.cc:209` wires the boot button; `esp/xiaozhi-esp32/main/boards/otto-robot/otto_robot.cc:213` only enters Wi-Fi config mode when starting.

Partial technical note: if a device already uses a custom OTA endpoint, that OTA response can redirect `websocket/url` without reflashing the application. For the official baseline, however, getting onto that custom OTA endpoint requires a new build/flash or equivalent NVS mutation, which is outside the requested no-reflash user path.

## Impact on H1b Flashing Path

H1b should be issued immediately after H008 if the goal is to connect this OttoRobot baseline to local Docker. The practical path is to build/flash a firmware variant with `CONFIG_OTA_URL` pointed at local xinnan-tech OTA or otherwise seed NVS with `wifi/ota_url`; relying on Wi-Fi provisioning or official console is not enough.
