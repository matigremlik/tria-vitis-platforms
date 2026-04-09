# Avoid setuptools_scm git-describe timeout when building libfdt wheel in native sysroot.
# The upstream setup.py uses use_scm_version and can stall on slow filesystems.
export SETUPTOOLS_SCM_PRETEND_VERSION = "${PV}"
export SETUPTOOLS_SCM_PRETEND_VERSION_FOR_LIBFDT = "${PV}"

do_configure:prepend () {
    sed -i "/use_scm_version=/,/},/c\\    version='${PV}'," ${S}/setup.py
}
