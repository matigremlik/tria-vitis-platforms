FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI:append = " \
  file://0001-link-absl-for-protobuf4.patch \
  file://0002-link-absl-for-protobuf4-postprocessor.patch \
"
