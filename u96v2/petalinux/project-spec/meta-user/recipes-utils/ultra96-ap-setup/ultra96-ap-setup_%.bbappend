FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

RDEPENDS:${PN}:remove = "udhcpd"
RDEPENDS:${PN}:remove = "busybox-udhcpd"
RDEPENDS:${PN}:append = " dnsmasq"
