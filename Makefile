.PHONY: smoke-acoustic

# Start uvicorn in the background, poll /health until 200, run the smoke
# harness, then tear down. PANNs CNN14 weight-loading takes ~10–20s on CPU
# so a fixed sleep is fragile — readiness probe is more reliable.
smoke-acoustic:
	@venv/bin/uvicorn backend.main:app --port 8000 --log-level warning > /tmp/uvicorn-smoke.log 2>&1 & \
	echo $$! > /tmp/uvicorn-smoke.pid; \
	for i in $$(seq 1 40); do \
	    curl -sf http://localhost:8000/health > /dev/null && break; \
	    sleep 1; \
	done; \
	venv/bin/python scripts/smoke_acoustic.py; rc=$$?; \
	kill $$(cat /tmp/uvicorn-smoke.pid) 2>/dev/null; \
	rm -f /tmp/uvicorn-smoke.pid; \
	exit $$rc
