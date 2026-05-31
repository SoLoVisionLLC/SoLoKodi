# SoLoTV build — file overrides

Drop replacement files here to override **any file inside the build zip**, keyed
by the file's path *inside the build* (which extracts to Kodi's home folder).

The pipeline (`scripts/build_solotv_build.py`) applies these on top of the
upstream Diggz foundation after text rebranding, so use this for **images and
binary/branding assets** that simple text replacement can't handle.

## How it works

- The path under `overrides/` mirrors the path inside the build zip.
- Example: to replace the Xenon skin logo, find its path in the build
  (e.g. `addons/skin.xenon/extras/SoLoVision/logo.png`) and place your file at:

  ```
  src/solotv_build/overrides/addons/skin.xenon/extras/SoLoVision/logo.png
  ```

- Text files (`.xml .txt .json .po .properties .ini .md .lang`) are automatically
  rebranded (Diggz → SoLoTV / SoLoVision). You only need overrides here for files
  that text replacement cannot fix (images, fonts, pre-rendered text, etc.).

## Brand images are generated from masters (don't hand-edit)

The image overrides in this folder are **derived** from two master images in
`src/solotv_build/brand/` (`solotv_bg_master.png`, `solotv_icon_master.png`) by
`scripts/make_solotv_overrides.py`, which crops/resizes each to the exact
dimensions Kodi expects. To rebrand, edit a master (keep the brand palette) and
regenerate — don't edit the derived files by hand:

```
python scripts/make_solotv_overrides.py      # refresh overrides + build-picker card
python scripts/build_solotv_build.py K21     # bake them into the build zip
```

**Brand palette:** Dark Navy `#1B2232`, Deep Red `#BC2026`,
Cool Light Grey `#A9B2BC`, White `#FFFFFF`.

To add a *new* branded asset, find its path/dimensions with `--inspect`, add a
target to `scripts/make_solotv_overrides.py`, and regenerate:

```
python scripts/build_solotv_build.py --inspect K21
```

This directory is committed to git; the large build zips are not.
