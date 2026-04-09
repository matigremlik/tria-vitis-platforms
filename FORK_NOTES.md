Base: `https://github.com/AlbertaBeef/tria-vitis-platforms/tree/2024.2`
Base commit: `cb40c11d143d06622a06c849b9ae48c5a0846712`

This staging tree pulls in the local `u96v2` and `meta-avnet` changes from `/home/ruinstoke/triat/tria-vitis-platforms`.

Included here:
- New `u96v2` accel overlays (`accel_dpu`, `accel_dpu_mnist`, `accel_dpu_optimised`, `accel_dpu_oresnet`) and the extra `dualcam_dpu` pre-processing kernel source.
- PetaLinux config changes for the base machine, networking, XRT/Vitis AI/VVAS packages, and SD card packaging.
- `meta-user` recipe additions for XRT, VART, XIR, Vitis AI Library, VVAS, kernel config, firmware recipes, and AP setup.
- `meta-avnet` fixes for pinned source revisions, `https` fetches, package composition, and startup/AP recipes.
- Target-side runtime scripts under `u96v2/sdcard/target_ULTRA/` without the large sample-image datasets.

Important packaging changes:
- Firmware recipe symlinks under `u96v2/petalinux/project-spec/meta-user/recipes-firmware/` were converted to real files in this staging tree so the repo is self-contained after clone.
- Generated Vivado/Vitis output, editor settings, `sdcard/app.tar.gz`, and the large `target_ULTRA/images/` corpus are ignored by `.gitignore`.

Recommended publication flow:
1. Create a GitHub repo for your fork of `tria-vitis-platforms`.
2. Create a separate GitHub fork/repo for `meta-avnet`.
3. In `common/petalinux/meta-avnet`, commit and push the staged submodule changes to your `meta-avnet` fork.
4. In the parent repo, update `.gitmodules` to point `common/petalinux/meta-avnet` at your fork URL before pushing.
5. Commit and push the parent repo changes, including the updated submodule pointer.
6. Publish `u96v2/sdcard/app.tar.gz` and any large demo datasets as GitHub release assets instead of committing them.
