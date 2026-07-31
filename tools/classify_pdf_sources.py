from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

import pdfplumber

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_EXTRACTED_DIR = BASE_DIR / 'data' / 'extracted'
OUTPUT_CSV = BASE_DIR / 'data' / 'processed' / 'marts' / 'pdf_source_classification.csv'


def classify_pdf(pdf_path: Path) -> dict[str, object]:
    try:
        with pdfplumber.open(pdf_path) as doc:
            page_count = len(doc.pages)
            first_page_text = doc.pages[0].extract_text() or '' if page_count else ''
            sample_text_len = len(first_page_text.strip())
    except Exception as exc:
        return {
            'archive': pdf_path.parent.name,
            'file_name': pdf_path.name,
            'classification': 'error',
            'page_count': 0,
            'sample_text_len': 0,
            'note': type(exc).__name__,
        }

    if sample_text_len >= 80:
        classification = 'text_based'
    elif sample_text_len > 0:
        classification = 'mixed_or_sparse_text'
    else:
        classification = 'image_based_or_ocr_needed'

    return {
        'archive': pdf_path.parent.name,
        'file_name': pdf_path.name,
        'classification': classification,
        'page_count': page_count,
        'sample_text_len': sample_text_len,
        'note': '',
    }


def write_csv(rows: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8-sig', newline='') as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=['archive', 'file_name', 'classification', 'page_count', 'sample_text_len', 'note'],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    pdf_files = sorted(DEFAULT_EXTRACTED_DIR.rglob('*.pdf'))
    rows = [classify_pdf(pdf_path) for pdf_path in pdf_files]
    write_csv(rows, OUTPUT_CSV)

    overall = Counter(row['classification'] for row in rows)
    by_archive: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        by_archive[str(row['archive'])][str(row['classification'])] += 1

    print('pdf_count', len(rows))
    print('overall', dict(overall))

    interesting_archives = []
    for archive, counts in by_archive.items():
        if counts.get('text_based', 0) and counts.get('image_based_or_ocr_needed', 0):
            interesting_archives.append((archive, counts))

    print('mixed_archives', len(interesting_archives))
    for archive, counts in sorted(interesting_archives)[:20]:
        print(archive, dict(counts))

    latest_archives = sorted(by_archive)[-10:]
    print('latest_archives')
    for archive in latest_archives:
        print(archive, dict(by_archive[archive]))

    print('output_csv', OUTPUT_CSV)


if __name__ == '__main__':
    main()
