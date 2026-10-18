"""Portable stdlib test runner; writes an actual result log and exits nonzero on failure."""
from pathlib import Path
import argparse
import io
import sys
import unittest

root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/"src"))

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--log",default=str(root/"reports"/"unit-tests.txt"))
    args=parser.parse_args()
    result_log=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(root/"tests"))
    result=unittest.TextTestRunner(stream=result_log,verbosity=2).run(suite)
    output=result_log.getvalue()
    target=Path(args.log);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(output,encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(output)
    return 0 if result.wasSuccessful() else 1

if __name__=="__main__":raise SystemExit(main())
