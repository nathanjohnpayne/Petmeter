# Petmeter

Coding-agent usage from the Petmeter daemon

A JavaScript app for the BUSY Bar, generated from the BUSY JS app template.

## Getting started

```sh
pnpm install
cp .env.example .env   # set VITE_BUSY_ADDR to your device's address
pnpm build
```

The app's id is `app.petmeter`, set in `src/appmeta/manifest.json`. An id is `<namespace>.<app>`, at most 32 characters, made of letters, digits, dot, underscore and dash, and not starting with a dot (busy-cli checks it the way the firmware does). If yours still says `app.example`, change it to your own namespace before publishing.

## Layout

`src/` is the app — everything in it is yours to edit.

```
my-app/
├── src/                          the app
│   ├── main.ts                   the entry point: exports nothing, ends with run()
│   ├── appmeta/
│   │   ├── manifest.json         id, name, version
│   │   ├── settings.json         the settings screen — optional
│   │   ├── icon_front_8x8.png    front icon, 8×8 colour — optional
│   │   └── icon_back_11x11.png   back icon, 11×11 greyscale — optional
│   ├── images/
│   ├── animations/
│   └── sounds/
├── shared/                       app-level helpers, imported as @shared/*
```

Both icons are optional; without them a default is used.

## Resources

Anything in `src/` that isn't a source file is copied into the package. Files in `src/images`, `src/animations` and `src/sounds` keep their folder; everything else is sorted by extension into the same three, and whatever has no match lands in `resources/`.

| Extension | Goes to |
| --- | --- |
| `.png` `.jpg` `.jpeg` `.gif` `.bmp` `.webp` `.svg` `.image` `.ico` | `images/` |
| `.anim` `.animation` | `animations/` |
| `.wav` `.snd` `.sng` `.mp3` `.ogg` `.rtttl` | `sounds/` |
| anything else | `resources/` |

A file whose extension disagrees with the folder it sits in is still placed by the folder, with a warning.

Everything the app draws goes through the layout helpers in `@busy-app/busy-lib`: build a tree out of `row` / `column` / `stack`, hand it to `render()`, and send the result with `device.DisplayDraw()`. The screen is 72×16 pixels.

## Commands

| Command | What it does |
| --- | --- |
| `pnpm build` | builds the package into `dist/`, as both the folder and a `.tgz` beside it (`busy-cli build --emit both`) |
| `pnpm build --out <path>` | builds into `<path>` instead |
| `pnpm build --tgz-name "{id}-{version}.tgz"` | names the archive; `{id}` and `{version}` come from the manifest |
| `pnpm exec busy-cli build` | packs the `.tgz` and leaves nothing else (busy-cli's own default, `--emit tgz`) |
| `pnpm build --no-minify` | readable output, for debugging |
| `pnpm build --bundle` | inlines every module into one `main.js` |
| `pnpm typecheck` | type-checks the app |

## Build output

The package folder is named after the app id:

```
dist/
└── app.petmeter/
    ├── appmeta/manifest.json
    ├── scripts/main.js
    └── images/ animations/ sounds/ resources/
```

The `.tgz` beside it, `dist/app.petmeter.tgz` by default, packs that folder with the folder itself at the root of the archive. The folder is what `tools/busybar_install_app.py` uploads, which is why `pnpm build` keeps it.

## Manifest

`src/appmeta/manifest.json` carries the app's identity and a couple of knobs:

| Field | |
| --- | --- |
| `format_version` | manifest format, `1` — required |
| `id` | up to 32 characters — required |
| `name` | display name — required |
| `version` | semver, e.g. `1.0.0` — required |
| `description`, `author` | free form, default `""` |
| `heap_size_kib` | memory for the app heap, 1–256, default 32 |
| `debug` | when true, shown only in developer mode, default false |

Raise `heap_size_kib` if the app runs out of memory.

## Node version

The app builds on Node 24 — the version in `.nvmrc` and the range `engines` allows. Node 26 breaks the build and is excluded. With `fnm` or `nvm` installed, `fnm use` / `nvm use` picks the right one up from `.nvmrc`.

## Settings

To give the app a settings screen, add `src/appmeta/settings.json` describing the fields, then read the stored values:

```ts
import { loadValues } from "@shared/settings";

const values = await loadValues();
```

`loadValues()` returns `null` when nothing is stored yet — use the defaults.
