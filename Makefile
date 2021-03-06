rev = $(shell ./version.sh)

ui_files = MainWindow.ui AboutDialog.ui ProgramDialog.ui RunnerDialog.ui IconDialog.ui ShortcutImport.ui Settings.ui SlotSettings.ui
ui_files_py = ${ui_files:.ui=.py}
qrc_files = resources.qrc
qrc_files_py = ${qrc_files:.qrc=_rc.py}
py_files = swine.py swinecli.py swinerun.py swinelib.py shortcutlib.py icolib.py config.py winetricks.py
deb_dir = package-files/deb
buildfiles = Makefile
resources = resources/*
images = images/*
lang = en de he fr es fi pl tr vi
lang_ts = $(addprefix lang/,$(addsuffix .ts,$(lang)))
lang_qm = $(addprefix translations/,$(addsuffix .qm,$(lang)))
sources = $(py_files) $(ui_files) $(qrc_files) README.md LICENSE version.sh $(buildfiles) $(images) $(resources) $(lang_ts)
distfiles = $(py_files) $(ui_files_py) $(qrc_files_py) README LICENSE version.sh $(resources) $(lang_qm)

.SUFFIXES: _rc.py .qrc .py .ui

.ui.py:
	pyuic4 $< -o $@

.qrc_rc.py:
	pyrcc4 $< -o $@

all: compile

deb-version:
	cd $(deb_dir); export rev=$(rev); make version

version: deb-version

deb-clean:
	cd $(deb_dir); export rev=$(rev); make clean

deb-build: swine-$(rev)-src.tar.gz
	cd $(deb_dir); export rev=$(rev); make build

deb-rebuild: swine-$(rev)-src.tar.gz
	cd $(deb_dir); export rev=$(rev); make rebuild

README: README.md
	cp README.md README

$(lang_ts): $(ui_files_py) $(py_files)

lang/xx.ts: $(ui_files_py) $(py_files)
	mkdir -p lang
	-rm lang/xx.ts
	pylupdate4 $(ui_files_py) $(py_files) -ts $@

lang/%: $(ui_files_py) $(py_files)
	mkdir -p lang
	pylupdate4 $(ui_files_py) $(py_files) -ts $@

$(lang_qm): $(lang_ts)
translations/%.qm: lang/%.ts
	mkdir -p translations
	lrelease-qt4 $< -compress -qm $@

swine-$(rev).tar.gz: compile $(distfiles)
	mkdir swine-$(rev)
	rsync -R $(distfiles) swine-$(rev)
	tar -czvf swine-$(rev).tar.gz swine-$(rev)
	rm -r swine-$(rev)

swine-$(rev)-src.tar.gz: $(sources) $(buildfiles)
	mkdir swine-$(rev)
	rsync -R $(sources) swine-$(rev)
	tar -czvf swine-$(rev)-src.tar.gz swine-$(rev)
	rm -r swine-$(rev)

compile: $(ui_files_py) $(qrc_files_py) $(lang_qm) README
dist: swine-$(rev).tar.gz swine-$(rev)-src.tar.gz

clean:
	rm -rf $(ui_files_py) $(qrc_files_py) $(lang_qm) *.pyc *.tar.gz *~

install: compile
	mkdir -p $(DESTDIR)/usr/lib/swine
	cp $(py_files) $(ui_files_py) $(qrc_files_py) $(DESTDIR)/usr/lib/swine
	mkdir -p $(DESTDIR)/usr/share/swine/translations
	cp $(lang_qm) $(DESTDIR)/usr/share/swine/translations
	mkdir -p $(DESTDIR)/usr/share/swine/images
	cp images/swine32.png $(DESTDIR)/usr/share/swine/images
	mkdir -p $(DESTDIR)/usr/share/applications
	cp resources/swine.desktop $(DESTDIR)/usr/share/applications/swine.desktop
	cp resources/swine-extensions.desktop $(DESTDIR)/usr/share/applications/swine-extensions.desktop
	ln -s ../lib/swine/swine.py $(DESTDIR)/usr/bin/swine
	ln -s ../lib/swine/swinecli.py $(DESTDIR)/usr/bin/swinecli
	ln -s ../lib/swine/swinerun.py $(DESTDIR)/usr/bin/swinerun

deb: deb-clean deb-build
