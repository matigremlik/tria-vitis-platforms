This directory keeps the target-side runtime sources that are practical to version in git.

Included:
- Python entry points and benchmark scripts
- `run_all_mobilenetv2_target.sh`
- `mobilenetv2.xmodel`

Intentionally excluded from git:
- `images/` bulk sample corpus
- `highrestst/` ad hoc sample images
- `../app.tar.gz` generated deployment bundle

If you want a deployable bundle from this tree, create it from this directory after adding whatever images and extra assets you need.
