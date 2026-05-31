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

## Finding branded assets

Run the pipeline once with `--inspect` to list the largest images and any files
whose path or name contains `diggz`/`xenon`/`chef`, then add overrides for the
ones you want to rebrand.

```
python scripts/build_solotv_build.py --inspect K21
```

This directory is committed to git; the large build zips are not.
