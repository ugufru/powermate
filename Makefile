.PHONY: issues
issues:
	python3 tools/issues_html.py render issues.jsonl issues.html roadmap.jsonl --title="powermate issues"
