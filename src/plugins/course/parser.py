from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re

import xlrd
from xlrd import XLRDError

WEEKDAY_MAP = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "日": 7,
    "天": 7,
}

WEEKDAY_RE = re.compile(r"星期([一二三四五六日天])")
PERIOD_INDEX_MAP = {
    "一": (1, 2),
    "二": (3, 4),
    "三": (5, 6),
    "四": (7, 8),
    "五": (9, 10),
    "六": (11, 12),
    "七": (13, 14),
}


def _period_from_index(text: str) -> tuple[int, int] | None:
    text = text.strip()
    return PERIOD_INDEX_MAP.get(text[:1]) if text else None
PERIOD_RE = re.compile(r"(\d+)\s*-\s*(\d+)\s*节?")
SINGLE_PERIOD_RE = re.compile(r"^\s*(\d+)\s*节?\s*$")
WEEK_RANGE_RE = re.compile(r"(\d+)\s*-\s*(\d+)\s*周")
WEEK_SINGLE_RE = re.compile(r"(\d+)\s*周")
DATE_RE = re.compile(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})")


@dataclass
class Course:
    name: str
    weekday: int
    start_section: int
    end_section: int
    weeks: list[int]
    location: str = ""
    teacher: str = ""


@dataclass
class CourseSchedule:
    courses: list[Course]
    semester: str = ""
    class_name: str = ""
    start_date: date | None = None


def _cell_text(sheet: xlrd.sheet.Sheet, row: int, col: int) -> str:
    value = sheet.cell_value(row, col)
    return str(value).strip() if value is not None else ""


def _parse_weeks(text: str) -> list[int]:
    weeks: set[int] = set()
    for start, end in WEEK_RANGE_RE.findall(text):
        a, b = int(start), int(end)
        if 1 <= a <= b <= 60:
            weeks.update(range(a, b + 1))
    if not weeks:
        for value in WEEK_SINGLE_RE.findall(text):
            n = int(value)
            if 1 <= n <= 60:
                weeks.add(n)
    return sorted(weeks)


def _parse_period(text: str) -> tuple[int, int] | None:
    match = PERIOD_RE.search(text)
    if match:
        return int(match.group(1)), int(match.group(2))
    match = SINGLE_PERIOD_RE.match(text)
    if match:
        n = int(match.group(1))
        return n, n
    return None


def _find_start_date(sheet: xlrd.sheet.Sheet) -> date | None:
    for row in range(sheet.nrows):
        for col in range(sheet.ncols):
            text = _cell_text(sheet, row, col)
            if "上课" not in text and "开学" not in text:
                continue
            match = DATE_RE.search(text)
            if not match:
                continue
            try:
                return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except ValueError:
                continue
    return None


def parse_qiangzhi_xls(path: Path) -> CourseSchedule:
    """解析强智教务系统导出的 .xls 课表。"""
    try:
        workbook = xlrd.open_workbook(str(path), encoding_override="gbk")
    except XLRDError as error:
        raise ValueError("无法读取课表文件，请确认是 .xls 格式") from error

    sheet = workbook.sheet_by_index(0)

    header_row = None
    weekday_cols: dict[int, int] = {}
    for row in range(min(sheet.nrows, 10)):
        found: dict[int, int] = {}
        for col in range(sheet.ncols):
            match = WEEKDAY_RE.search(_cell_text(sheet, row, col))
            if match:
                found[WEEKDAY_MAP[match.group(1)]] = col
        if len(found) >= 3:
            header_row = row
            weekday_cols = found
            break

    if header_row is None or not weekday_cols:
        raise ValueError("没有找到课表的星期表头，请确认模板是否为强智教务系统导出")

    semester = _cell_text(sheet, 0, 0)
    class_name = ""
    for col in range(sheet.ncols):
        text = _cell_text(sheet, 0, col)
        if "课表" in text:
            class_name = text
            break

    courses: list[Course] = []
    for row in range(header_row + 1, sheet.nrows):
        first = _cell_text(sheet, row, 0)
        if first.startswith("注") or "打印时间" in first:
            break

        row_period = _period_from_index(_cell_text(sheet, row, 1))

        for weekday, col in weekday_cols.items():
            text = _cell_text(sheet, row, col)
            if not text:
                continue
            for entry in re.split(r"[\r\n]+", text):
                entry = entry.strip()
                if not entry:
                    continue
                parts = [part.strip() for part in entry.split("/")]
                name = parts[0]
                if not name:
                    continue
                period = _parse_period(parts[1]) if len(parts) > 1 else None
                if period is None:
                    period = row_period
                if period is None:
                    continue
                start_section, end_section = period
                weeks = _parse_weeks(parts[1]) if len(parts) > 1 else []
                if not weeks:
                    continue
                courses.append(
                    Course(
                        name=name,
                        weekday=weekday,
                        start_section=start_section,
                        end_section=end_section,
                        weeks=weeks,
                        location=parts[2] if len(parts) > 2 else "",
                        teacher=parts[3] if len(parts) > 3 else "",
                    )
                )

    if not courses:
        raise ValueError("课表里没有解析到课程，请确认模板内容")

    return CourseSchedule(
        courses=courses,
        semester=semester,
        class_name=class_name,
        start_date=_find_start_date(sheet),
    )
