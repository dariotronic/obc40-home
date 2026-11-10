# Changelog

All notable changes to obc40-home. Versions follow [semantic versioning](https://semver.org/).

## 0.0.1

First public release.

- Fullscreen touch launcher for the OBC40 1024×600 display: clock and date, weather (Open-Meteo, tap the card to set the city), big tiles for Music, Terminal, Files, Settings, Wi-Fi, on-screen keyboard, Desktop, Android (only on dual-boot boards) and Power off.
- Status bar with Wi-Fi network and signal, IP address, battery, temperature and uptime.
- `obc-fitwin`: maximises windows that do not fit the 600 px high screen.
- Manual updates: tap the version in the status bar to check for a new release and install it; the previous version is kept and restored automatically if the new one does not start.
- `faccessat-fix` for the Android 4.14 kernel (GLib file checks fail without it).
- Optional `extras/xfce-touch-setup.sh` to make XFCE touch-friendly.
