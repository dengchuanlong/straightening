"""Reproduce the seed-40/41/42 benchmark and seed-43 paired bootstrap.

Run from any current directory with Python 3.12 and pinned requirements.
No finite-element solver is invoked. Source provenance remains pending.
"""
from pathlib import Path
import argparse
import subprocess
import sys

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-figures',action='store_true')
    parser.add_argument('--skip-learning-curves',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    command=[sys.executable,str(root/'scripts/run_experiments.py'),'--data',str(root/'data/dataset.json'),
             '--output',str(root),'--seeds','40','41','42','--bootstrap-seed','43']
    if args.skip_learning_curves:command.append('--skip-learning-curves')
    subprocess.run(command,check=True,cwd=root)
    subprocess.run([sys.executable,str(root/'scripts/verify_experiment.py'),'--root',str(root)],check=True,cwd=root)
    if not args.skip_learning_curves:
        subprocess.run([sys.executable,str(root/'scripts/verify_seed_revision.py')],check=True,cwd=root)
    subprocess.run([sys.executable,str(root/'scripts/export_revision_tables.py')],check=True,cwd=root)
    if not args.skip_figures:
        subprocess.run([sys.executable,str(root/'scripts/make_paper_figures.py')],check=True,cwd=root)
    subprocess.run([sys.executable,str(root/'scripts/build_release_manifest.py')],check=True,cwd=root)

if __name__=='__main__':main()
