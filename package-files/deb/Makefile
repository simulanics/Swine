ALL: build

swine_$(rev).orig.tar.gz:
	cp -a ../../swine-$(rev)-src.tar.gz swine_$(rev).orig.tar.gz

unpack: swine_$(rev).orig.tar.gz
	tar -xzvf swine_$(rev).orig.tar.gz
	cp -a swine-$(rev) swine-$(rev).orig
	cp -a meta/* swine-$(rev)
	find swine-$(rev) -name .svn -exec rm -rf \{\} \; || true

build: unpack
	cd swine-$(rev); debuild -b -us -uc; cd ..

rebuild: swine_$(rev).dsc
	dpkg-source -x swine_$(rev).dsc
	cd swine-$(rev); debuild -b -us -uc; cd ..

version:
	cd meta; dch -v $(rev) --force-distribution -D unstable

clean:
	rm -rf swine-$(rev)*
	rm -rf swine_$(rev)*
