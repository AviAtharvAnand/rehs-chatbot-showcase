.PHONY: help install check validate site serve clean

help:
	@echo "make install    install the few Python packages this repo needs"
	@echo "make check      check every chatbot folder (run this before you push)"
	@echo "make site       build the gallery into site/"
	@echo "make serve      build, then open http://localhost:8000"
	@echo "make clean      delete site/"

install:
	pip install -r requirements.txt

check:
	python _pages/scripts/validate.py

# alias, in case you type the other one
validate: check

site:
	python _pages/scripts/build_site.py

serve:
	python _pages/scripts/build_site.py --base-url http://localhost:8000/ --serve

clean:
	rm -rf site
