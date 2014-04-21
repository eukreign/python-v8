VERSION = 0.1.4
PACKAGE = 1

createdeb: clean
	pip install stdeb
	python setup.py --command-packages=stdeb.command sdist_dsc --debian-version 1

builddeb: createdeb
	cd deb_dist/python-v8-$(VERSION)/; dpkg-buildpackage -us -uc

installdeb: builddeb
	cd deb_dist/; sudo dpkg -i python-v8*.deb

release: createdeb
	cd deb_dist/python-v8-$(VERSION)/; debuild -S -sa -k3F08E7FE
	cd deb_dist/; dput ppa:damoti/ppa python-v8_$(VERSION)-$(PACKAGE)_source.changes

clean:
	rm -rf deb_dist dist v8.egg-info v8-*.tar.gz _v8.so
