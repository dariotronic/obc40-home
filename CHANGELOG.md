# Changelog

All notable changes to obc40-home. Versions follow [semantic versioning](https://semver.org/).

## 0.1.0

- New layout: clock, edit button and weather are part of the tile grid (clock and weather two tiles wide).
- Edit mode: tap the pencil or long-press a tile. Tiles shrink and wiggle; ✕ empties a tile, the pencil changes it, + fills an empty one, ✓ ends.
- Every tile can hold an installed app, a home function or a website; a website tile shows the site's icon. The tiles are saved in `[tiles]` in `~/.config/obc-home.ini` (the 0.0.3 `main_app` setting is taken over).
- Swipe down on the home to bring down the XFCE top panel, swipe up to hide it. The home is now maximised instead of full screen, sets the top panel to hide itself and styles the panels with the home's colours.
- Bigger status bar, with an easier to tap version button.

## 0.0.3

- Choose the app of the big tile on the screen: tap the empty tile (or long-press it to change the app) and pick from the list of installed apps; the choice is saved in `~/.config/obc-home.ini`. Before, the list only launched the app and the tile stayed empty.

## 0.0.2

- The big tile is now generic: it opens the app set in `~/.config/obc-home.ini` (`[launcher] main_app = <file>.desktop`), or the list of all applications if none is set.
- One-line installer: `wget -qO- https://raw.githubusercontent.com/dariotronic/obc40-home/main/get.sh | sh`.
- Release checksums use LF line endings, so `sha256sum -c` works.

## 0.0.1

First public release.

- Fullscreen touch launcher for the OBC40 1024×600 display: clock and date, weather (Open-Meteo, tap the card to set the city), big tiles for Music, Terminal, Files, Settings, Wi-Fi, on-screen keyboard, Desktop, Android (only on dual-boot boards) and Power off.
- Status bar with Wi-Fi network and signal, IP address, battery, temperature and uptime.
- `obc-fitwin`: maximises windows that do not fit the 600 px high screen.
- Manual updates: tap the version in the status bar to check for a new release and install it; the previous version is kept and restored automatically if the new one does not start.
- `faccessat-fix` for the Android 4.14 kernel (GLib file checks fail without it).
- Optional `extras/xfce-touch-setup.sh` to make XFCE touch-friendly.
