# Copyright 1999-2005 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

inherit eutils

MY_PV="${PV/_/-}"

RESTRICT="nomirror"
DESCRIPTION="Swine is wine frontend for Qt"
HOMEPAGE="http://swine.sourceforge.net"
SRC_URI="mirror://sourceforge/${PN}/${PN}-src-${MY_PV}.tar.gz"
LICENSE="GPL-2"
KEYWORDS="~x86"
SLOT="0"
IUSE=""

DEPEND="app-emulation/wine
	dev-lang/python
	dev-python/PyQt"
RDEPEND="${DEPEND}"

S="${WORKDIR}"

src_unpack() {
        unpack ${A}
        cd "${S}"
}

src_compile() {
	emake || die "emake failed"
}

src_install() {
	cd "${S}"

	dodoc README
	dodoc LICENSE

	dodir /usr/lib/swine
	insinto /usr/lib/swine
	doins *.py

	dodir /usr/lib/swine/images
	insinto /usr/lib/swine/images
	doins images/*

	dodir /usr/lib/swine/images/16x16
	insinto /usr/lib/swine/images/16x16
	doins images/16x16/*

	exeinto /usr/lib/swine
	doexe swine.py swinecli.py

	dosym ../lib/swine/swine.py /usr/bin/swine
        dosym ../lib/swine/swinecli.py /usr/bin/swinecli
}
