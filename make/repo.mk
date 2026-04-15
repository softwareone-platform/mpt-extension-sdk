## Add repo-specific targets here. Do not modify the shared *.mk files.
build-package:
	$(RUN) uv build

run-demo:
	$(DC) -f compose.demo.yaml up
