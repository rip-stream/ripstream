.PHONY: format test

format:
	@ruff_status=0; ty_status=0; \
	uv run --frozen ruff check --fix || ruff_status=$$?; \
	uv run --frozen ty check || ty_status=$$?; \
	if [ $$ruff_status -ne 0 ] || [ $$ty_status -ne 0 ]; then \
		echo "format failed (ruff=$$ruff_status, ty=$$ty_status)"; \
		exit 1; \
	fi

test:
	uv run --frozen pytest -n auto
