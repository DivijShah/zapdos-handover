demo-drop:
	cp tests/drops/demo-2030.txt inbox/drops/demo-2030.txt

demo-reset:
	rm -f inbox/drops/demo-2030.txt

.PHONY: demo-drop demo-reset
