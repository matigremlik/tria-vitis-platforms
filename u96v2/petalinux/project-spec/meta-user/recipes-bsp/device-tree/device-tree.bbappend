FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI:append = " file://system-user.dtsi"

require ${@'device-tree-sdt.inc' if d.getVar('SYSTEM_DTFILE') != '' else ''}

# PetaLinux XSCT-generated system-bsp.dtsi references PL-only labels (axi_intc_0, amba_pl)
# which do not exist in the base DT. Strip those blocks after generation.
do_configure:append() {
    if [ -e ${DT_FILES_PATH}/system-bsp.dtsi ]; then
        sed -i '/^\/\* Vitis interrupt/,/^};$/d' ${DT_FILES_PATH}/system-bsp.dtsi
        sed -i '/^&amba_pl/,/^};$/d' ${DT_FILES_PATH}/system-bsp.dtsi
    fi
}

# Location of the PetaLinux workspace-generated device tree
PLNX_WORKSPACE ?= "${TOPDIR}/../components/plnx_workspace"
PLNX_DT_DIR ?= "${PLNX_WORKSPACE}/device-tree/device-tree"

# Also patch the workspace-generated system-bsp.dtsi before compile in case it was regenerated
# after do_configure, since dtc includes it from PLNX_DT_DIR.
do_compile[prefuncs] += "plnx_fixup_system_bsp"
plnx_fixup_system_bsp() {
    if [ -e ${PLNX_DT_DIR}/system-bsp.dtsi ]; then
        sed -i '/^\/\* Vitis interrupt/,/^};$/d' ${PLNX_DT_DIR}/system-bsp.dtsi
        sed -i '/^&amba_pl/,/^};$/d' ${PLNX_DT_DIR}/system-bsp.dtsi
    fi
}
