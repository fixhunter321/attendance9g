
import csv
import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)


# =========================
# KONFIGURASI
# =========================

INPUT_FILE = "Absensi.csv"
OUTPUT_FOLDER = "Hasil_Absensi"

# Isi dengan 30 nama kelas sebenarnya agar PDF tetap dibuat
# meskipun suatu kelas belum memiliki siswa hadir.
EXPECTED_CLASSES = []


# =========================
# MEMBACA WAKTU
# =========================

def parse_time(value):
    value = str(value).strip()

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError:
        pass

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def format_time(value):
    parsed = parse_time(value)

    if parsed:
        return parsed.strftime("%d-%m-%Y %H:%M:%S")

    return str(value).strip()


# =========================
# MEMBACA CSV
# =========================

def read_data():

    file_path = Path(__file__).parent / INPUT_FILE

    if not file_path.exists():
        raise FileNotFoundError(
            f"File {INPUT_FILE} tidak ditemukan!"
        )

    data = defaultdict(dict)
    detected_classes = set()

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("CSV tidak memiliki header.")

        headers = {
            str(header).strip().lower(): header
            for header in reader.fieldnames
        }

        required = ["time", "name", "class"]

        for column in required:
            if column not in headers:
                raise ValueError(
                    f"Kolom {column} tidak ditemukan!"
                )

        for row in reader:

            time = row.get(headers["time"], "")
            name = str(
                row.get(headers["name"], "")
            ).strip()

            student_class = str(
                row.get(headers["class"], "")
            ).strip()

            if not time or not name or not student_class:
                continue

            group = (
                "Guru"
                if student_class.casefold() == "guru"
                else student_class
            )

            if group != "Guru":
                detected_classes.add(group)

            parsed = parse_time(time)

            timestamp = (
                parsed.timestamp()
                if parsed
                else float("inf")
            )

            # Kunci identitas agar absensi ganda tidak masuk.
            key = (
                name.casefold(),
                student_class.casefold()
            )

            record = {
                "Time": format_time(time),
                "Name": name,
                "Class": student_class,
                "_timestamp": timestamp
            }

            previous = data[group].get(key)

            # Jika duplikat, gunakan waktu paling awal.
            if (
                previous is None
                or timestamp < previous["_timestamp"]
            ):
                data[group][key] = record

    return data, detected_classes


# =========================
# MEMBUAT PDF
# =========================

def safe_filename(name):

    return re.sub(
        r'[<>:"/\\|?*]',
        "_",
        name
    ).strip()


def create_pdf(group_name, records, output_path):

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=16,
        alignment=1,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=9,
        alignment=1,
        spaceAfter=12
    )

    elements = []

    elements.append(
        Paragraph(
            f"DAFTAR ABSENSI - {group_name}",
            title_style
        )
    )

    elements.append(
        Paragraph(
            f"Jumlah kehadiran: {len(records)} orang",
            subtitle_style
        )
    )

    elements.append(Spacer(1, 5 * mm))

    table_data = [
        ["Time", "Name", "Class"]
    ]

    for record in records:

        table_data.append([
            record["Time"],
            record["Name"],
            record["Class"]
        ])

    table = Table(
        table_data,
        colWidths=[
            55 * mm,
            150 * mm,
            45 * mm
        ],
        repeatRows=1
    )

    table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#26364A")
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, 0),
                "CENTER"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.4,
                colors.grey
            ),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#F1F4F7")
                ]
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                6
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                6
            )
        ])
    )

    elements.append(table)

    document.build(elements)


# =========================
# PROSES UTAMA
# =========================

def main():

    base_path = Path(__file__).parent

    output_path = base_path / OUTPUT_FOLDER
    output_path.mkdir(exist_ok=True)

    data, detected_classes = read_data()

    classes = (
        set(EXPECTED_CLASSES)
        if EXPECTED_CLASSES
        else detected_classes
    )

    groups = sorted(
        classes,
        key=str.casefold
    )

    groups.append("Guru")

    generated = 0

    for group in groups:

        records = list(
            data[group].values()
        )

        records.sort(
            key=lambda item: (
                item["_timestamp"],
                item["Name"].casefold()
            )
        )

        # Hapus kolom internal sebelum membuat PDF.
        clean_records = [
            {
                "Time": item["Time"],
                "Name": item["Name"],
                "Class": item["Class"]
            }
            for item in records
        ]

        filename = (
            safe_filename(group) + ".pdf"
        )

        create_pdf(
            group,
            clean_records,
            output_path / filename
        )

        generated += 1

        print(
            f"[OK] {filename} - "
            f"{len(clean_records)} data"
        )

    print("\n======================")
    print("PROSES SELESAI")
    print("======================")

    print(f"Total PDF: {generated}")
    print(f"Lokasi: {output_path}")

    if not EXPECTED_CLASSES:
        print(
            "Kelas dideteksi otomatis dari CSV. "
            "Untuk tepat 31 PDF, pastikan ada 30 "
            "kelas berbeda atau isi EXPECTED_CLASSES."
        )


if __name__ == "__main__":

    try:
        main()

    except Exception as error:

        print("ERROR:", error)
        sys.exit(1)
