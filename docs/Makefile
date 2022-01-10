.PHONY: FORCE
.DELETE_ON_ERROR:
.SUFFIXES: 

# sudo apt install librsvg-bin
# npm install -g @mermaid-js/mermaid-cli

all: sequence.svg sequence.png

%.svg: %.mmd
	mmdc -i $< -o $@

%.png: %.svg
	rsvg-convert -w 500 -b white $< -o $@

