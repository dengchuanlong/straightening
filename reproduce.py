"""Reproduce the frozen 24 October MGRE revision and all scientific displays."""
from pathlib import Path
import subprocess,sys

def main():
    root=Path(__file__).resolve().parent
    for name in ['run_revision.py','build_revision_tables.py','make_revision_figures.py','verify_revision.py']:
        subprocess.run([sys.executable,str(root/'scripts'/name)],cwd=root,check=True)

if __name__=='__main__':main()
