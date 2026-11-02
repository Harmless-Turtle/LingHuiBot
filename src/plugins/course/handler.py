import asyncio
from dataclasses import asdict
from datetime import date
import tempfile
from pathlib import Path

import httpx
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
from nonebot.matcher import Matcher

from ..Exceptions import UserVisibleError
from ..utils import handle_errors
from .command import course_clear, course_import, course_today, course_week
from .parser import CourseSchedule, parse_qiangzhi_xls
from .storage import clear_schedule, load_schedule, save_schedule

MAX_FILE_BYTES = 5 * 1024 * 1024


def _current_week(start_date: str | None) -> int | None:
    if not start_date:
        return None
    try:
        start = date.fromisoformat(start_date)
    except ValueError:
        return None
    days = (date.today() - start).days
    return days // 7 + 1 if days >= 0 else None


def _format_courses(data: dict, *, week: int | None = None, weekday: int | None = None) -> str:
    courses = data.get("courses", [])
    selected = [
        course
        for course in courses
        if (week is None or week in course.get("weeks", []))
        and (weekday is None or course.get("weekday") == weekday)
    ]
    if not selected:
        return "这段时间没有课呢，好好休息 awa"

    selected.sort(key=lambda item: (item.get("weekday", 0), item.get("start_section", 0)))
    lines = []
    for course in selected:
        day_text = "一二三四五六日"[max(0, min(6, course.get("weekday", 1) - 1))]
        location = f" @{course['location']}" if course.get("location") else ""
        teacher = f" {course['teacher']}" if course.get("teacher") else ""
        lines.append(
            f"周{day_text} {course.get('start_section')}-{course.get('end_section')}节 "
            f"{course.get('name', '未知课程')}{location}{teacher}"
        )
    return "\n".join(lines)


def _schedule_to_dict(schedule: CourseSchedule) -> dict:
    return {
        "semester": schedule.semester,
        "class_name": schedule.class_name,
        "start_date": schedule.start_date.isoformat() if schedule.start_date else None,
        "courses": [asdict(course) for course in schedule.courses],
    }


def _find_file_url(event: MessageEvent) -> str | None:
    for segment in event.get_message():
        if segment.type != "file":
            continue
        for key in ("url", "file"):
            value = segment.data.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value
    return None


@course_import.handle()
@handle_errors
async def handle_course_import(
        matcher: Matcher,
        event: MessageEvent,
        ) -> None:
    url = _find_file_url(event)
    if not url:
        raise UserVisibleError("请把课表 .xls 文件和“导入课表”一起发送哦~")

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise UserVisibleError("课表文件下载失败，请稍后重试~") from error

    content = response.content
    if len(content) > MAX_FILE_BYTES:
        raise UserVisibleError("课表文件太大了，请确认是 5MB 以内的 .xls 文件")

    tmp_path: Path | None = None
    try:
        fd, tmp_name = tempfile.mkstemp(suffix=".xls")
        tmp_path = Path(tmp_name)
        with open(fd, "wb") as file:
            file.write(content)
        schedule = await asyncio.to_thread(parse_qiangzhi_xls, tmp_path)
    except ValueError as error:
        raise UserVisibleError(str(error)) from error
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    save_schedule(str(event.user_id), _schedule_to_dict(schedule))
    await matcher.finish(
        MessageSegment.reply(event.message_id)
        + f"课表导入成功，共 {len(schedule.courses)} 门课程。\n"
        "发送“本周课表”或“今日课表”查看吧 awa"
    )


@course_week.handle()
@handle_errors
async def handle_course_week(
        matcher: Matcher,
        event: MessageEvent,
        ) -> None:
    data = load_schedule(str(event.user_id))
    if not data:
        raise UserVisibleError("你还没有导入课表呢，先发“导入课表”并附上 .xls 文件吧~")

    week = _current_week(data.get("start_date"))
    header = f"第 {week} 周" if week else "全部课程"
    body = _format_courses(data, week=week)
    await matcher.finish(MessageSegment.reply(event.message_id) + f"📚 {header}\n{body}")


@course_today.handle()
@handle_errors
async def handle_course_today(
        matcher: Matcher,
        event: MessageEvent,
        ) -> None:
    data = load_schedule(str(event.user_id))
    if not data:
        raise UserVisibleError("你还没有导入课表呢，先发“导入课表”并附上 .xls 文件吧~")

    week = _current_week(data.get("start_date"))
    weekday = date.today().isoweekday()
    body = _format_courses(data, week=week, weekday=weekday)
    today_text = "一二三四五六日"[weekday - 1]
    await matcher.finish(
        MessageSegment.reply(event.message_id) + f"📚 今天（周{today_text}）的课：\n{body}"
    )


@course_clear.handle()
@handle_errors
async def handle_course_clear(
        matcher: Matcher,
        event: MessageEvent,
        ) -> None:
    clear_schedule(str(event.user_id))
    await matcher.finish(MessageSegment.reply(event.message_id) + "课表已清除~")
