"""Retrieval over ARSET materials: collect PDFs, split them into chunks, index, search.

Everything this package writes lives under corpus/ (git-ignored): the
materials belong to their authors and are kept only as a local search index.
"""
from pathlib import Path

from ..catalog import ROOT

CORPUS = ROOT / "corpus"
TEXT_DIR = CORPUS / "text"  # one JSON file of extracted page text per material
