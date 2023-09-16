.PHONY: usage clean dist doc testpypi-upload pypi-upload

usage:
	@echo Available make targets are: \
	clean, dist, doc, testpypi-upload, and pypi-upload	

doc:
	rm -rf stash/doc/*
	cd documentation ; make PYTHONEXE=python3.11 html
	mv documentation/build/html stash/doc

dist:
# Unset PIP_CONFIG_FILE in case pip.conf sets user = True
	env PIP_CONFIG_FILE=/dev/null python3.11 -m build -x --sdist --wheel .

clean:
	rm -rf build dist */*.egg-info */__pycache__ */*.pyc

testpypi-upload:
	python3.11 -m twine upload --repository testpypi dist/*

pypi-upload:
	python3.11 -m twine upload dist/*
