"""Run pytest on given test files from a script so it passes through rt_py. Output dir redirected to scratch
(NHTSA_OUTPUT_DIR must be set by the caller); tests that read/write outputs use that directory."""
import sys, pytest
sys.exit(pytest.main(["-q", "-p", "no:cacheprovider", *sys.argv[1:]]))
