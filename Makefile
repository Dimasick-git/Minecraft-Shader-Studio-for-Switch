# Minecraft Shader Studio — Author: Dimasick-git
.PHONY: all native test python-test check clean
all: native
native:
	cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
	cmake --build build --parallel

test: native python-test
	ctest --test-dir build --output-on-failure
python-test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v
check: test
	PYTHONPATH=src python3 -m compileall -q src scripts tests
clean:
	rm -rf build dist *.egg-info src/*.egg-info
