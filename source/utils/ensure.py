import inspect
import re
from pathlib import Path


def _extract_ensure_content(source_lines: list[str], start_line: int) -> str | None:
    source_text = "".join(source_lines[max(0, start_line - 1) : min(len(source_lines), start_line + 10)])

    ensure_pattern = r"ensure\s*\("
    match = re.search(ensure_pattern, source_text)
    if not match:
        return None

    start_pos = match.end() - 1
    paren_count = 0
    i = start_pos

    while i < len(source_text):
        match source_text[i]:
            case "(":
                paren_count += 1
            case ")":
                paren_count -= 1
                if paren_count == 0:
                    content = source_text[start_pos + 1 : i]

                    comma_pos = _find_top_level_comma(content)
                    if comma_pos != -1:
                        content = content[:comma_pos]

                    return content.strip()

        i += 1

    return None


def _find_top_level_comma(text: str) -> int:
    paren_count = 0
    bracket_count = 0

    for i, char in enumerate(text):
        match char:
            case "(":
                paren_count += 1
            case ")":
                paren_count -= 1
            case "[":
                bracket_count += 1
            case "]":
                bracket_count -= 1
            case "," if paren_count == 0 and bracket_count == 0:
                return i
    return -1


def ensure[T](value: T | None, error_raise_type: type[Exception] = ValueError) -> T:
    field_name = None
    location_info = ""

    if value is None:
        frame = inspect.currentframe()
        if frame and frame.f_back:
            filename = frame.f_back.f_code.co_filename
            line_number = frame.f_back.f_lineno
            function_name = frame.f_back.f_code.co_name

            location_parts = [f"file {filename}", f"line {line_number}"]

            if function_name != "<module>":
                location_parts.append(f"function {function_name}")

            location_info = " (" + ", ".join(location_parts) + ")"

            try:
                with Path(filename).open(encoding="utf-8") as f:
                    lines = f.readlines()
                    field_name = _extract_ensure_content(lines, line_number)
            except (OSError, IndexError):
                pass

        if field_name:
            raise error_raise_type("Unexpected None in field " + field_name + location_info)
        raise error_raise_type("Unexpected None in field" + location_info)

    return value
