"""Automation routines extracted from the original Tkinter script."""

from __future__ import annotations

import importlib
import json
import requests
import time
from datetime import timedelta
from threading import Event
from timeit import default_timer as timer
from typing import TYPE_CHECKING, Callable, Iterable, Optional

try:
    import autoit
except ModuleNotFoundError as _autoit_err:  # pragma: no cover - packaging safeguard

    class _AutoItStub:
        def __getattr__(self, name: str):
            raise RuntimeError(
                "The 'autoit' module is required for automation routines. "
                "Install the PyAutoIt package to enable in-game interactions."
            ) from _autoit_err

    autoit = _AutoItStub()  # type: ignore[assignment]
import cv2
import numpy as np
import pyautogui
import pyperclip
import pytesseract
from PIL import Image

from .. import constants
from ..services.arc_client import is_in_char_select_screen
from ..services.mumble import MumbleLink
from ..services.notifications import play_beep, send_message

if TYPE_CHECKING:  # pragma: no cover - type check helpers only
    from char_movement import (
        do_dailies as do_dailies_type,
        farm_home_instance as farm_home_instance_type,
        use_converters as use_converters_type,
        get_lw4_currencies as get_lw4_currencies_type,
        get_drizzlewood_stuff as get_drizzlewood_stuff_type,
    )
    from event_schedule import get_next_event as get_next_event_type
    from wvw_helper import do_wvw as do_wvw_type


def _missing_char_movement(name: str):
    def _raiser(*args, **kwargs):
        raise RuntimeError(
            f"'{name}' is unavailable because the optional module 'char_movement' is missing."
        )

    return _raiser


_char_movement = importlib.util.find_spec("char_movement")
if _char_movement is not None:
    _char_mod = importlib.import_module("char_movement")
    do_dailies = _char_mod.do_dailies  # type: ignore[attr-defined]
    farm_home_instance = _char_mod.farm_home_instance  # type: ignore[attr-defined]
    use_converters = _char_mod.use_converters  # type: ignore[attr-defined]
    get_lw4_currencies = _char_mod.get_lw4_currencies  # type: ignore[attr-defined]
    get_drizzlewood_stuff = _char_mod.get_drizzlewood_stuff  # type: ignore[attr-defined]
else:  # pragma: no cover - optional dependency
    do_dailies = _missing_char_movement("do_dailies")
    farm_home_instance = _missing_char_movement("farm_home_instance")
    use_converters = _missing_char_movement("use_converters")
    get_lw4_currencies = _missing_char_movement("get_lw4_currencies")
    get_drizzlewood_stuff = _missing_char_movement("get_drizzlewood_stuff")


_event_schedule_spec = importlib.util.find_spec("event_schedule")
if _event_schedule_spec is not None:
    get_next_event = importlib.import_module("event_schedule").get_next_event  # type: ignore[attr-defined]
else:  # pragma: no cover - optional dependency

    def get_next_event(*_args, **_kwargs):
        return None


_wvw_helper_spec = importlib.util.find_spec("wvw_helper")
if _wvw_helper_spec is not None:
    do_wvw = importlib.import_module("wvw_helper").do_wvw  # type: ignore[attr-defined]
else:  # pragma: no cover - optional dependency

    def do_wvw(*_args, **_kwargs):
        raise RuntimeError(
            "'do_wvw' is unavailable because the optional module 'wvw_helper' is missing."
        )


Region = tuple[int, int, int, int]
_GW2_WINDOW_TITLE = "Guild Wars 2"


def _is_gw2_window_foreground() -> bool:
    try:
        return bool(autoit.win_active(_GW2_WINDOW_TITLE))
    except Exception:
        return False


def _click_character_selection_slot(x: int, y: int, clicks: int = 2) -> bool:
    """Click a character slot only while Guild Wars 2 owns the foreground."""

    if not _is_gw2_window_foreground():
        autoit.win_activate(_GW2_WINDOW_TITLE)
        time.sleep(1)
        
    autoit.mouse_click("left", x, y, clicks, 0)
    return True


def take_screenshot(region: Region):
    screenshot = pyautogui.screenshot(region=region)
    return screenshot


def find_image_in_image(
    big_image_path: str, small_image_path: str
) -> list[tuple[int, int]]:
    big_image = cv2.imread(big_image_path)
    small_image = cv2.imread(small_image_path)
    big_image_gray = cv2.cvtColor(big_image, cv2.COLOR_BGR2GRAY)
    small_image_gray = cv2.cvtColor(small_image, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(big_image_gray, small_image_gray, cv2.TM_CCOEFF_NORMED)
    threshold = 0.85
    locations = np.where(result >= threshold)
    return list(zip(*locations[::-1]))


def get_pixel_color(x: int, y: int) -> tuple[int, int, int]:
    color = autoit.pixel_get_color(x, y)
    blue = color & 0xFF
    green = (color >> 8) & 0xFF
    red = (color >> 16) & 0xFF
    return red, green, blue


def is_cc_bar() -> bool:
    color = get_pixel_color(1760, 130)
    return 50 < color[0] < 60 and color[1] > 100 and color[2] > 90


def scan_skills():
    debugging = False
    skill_2_ready = False
    skill_f1_ready = False
    skill_3_ready = False
    skill_f2_ready = False
    skill_f3_ready = False
    skill_4_focus_ready = False
    skill_5_focus_ready = False
    skill_5_sword_ready = False
    skill_f5_ready = False
    skill_heal_ready = False
    skill_illusion_ready = False
    skill_ultimate_ready = False
    weapon_swap_ready = False
    blade_count = 0
    quickness = False
    start = timer()
    region = (1514, 1986, 766, 160)
    screenshot = take_screenshot(region)
    screenshot.save("skills.png")
    time.sleep(0.01)
    big_image_path = "skills.png"

    def check(pattern: str) -> bool:
        return bool(find_image_in_image(big_image_path, pattern))

    skill_2_ready = check("skill_2.png")
    skill_3_ready = check("skill_3.png")
    skill_4_focus_ready = check("skill_4_focus.png")
    if skill_4_focus_ready:
        skill_5_focus_ready = check("skill_5_focus.png")
    else:
        skill_5_sword_ready = check("skill_5_sword.png")
    skill_heal_ready = check("skill_heal.png")
    skill_ultimate_ready = check("skill_ultimate.png")
    skill_f1_ready = check("skill_f1.png")
    skill_f2_ready = check("skill_f2.png")
    skill_f3_ready = check("skill_f3.png")
    skill_f5_ready = check("skill_f5.png")
    weapon_swap_ready = check("weapon_swap.png")
    blade_count = len(find_image_in_image(big_image_path, "blade.png"))
    skill_illusion_ready = check("skill_illusions.png")
    quickness = check("quickness.png")
    cc_bar = is_cc_bar()
    end = timer()
    if debugging:
        print(timedelta(seconds=end - start))
    return (
        skill_f3_ready,
        skill_illusion_ready,
        quickness,
        blade_count,
        weapon_swap_ready,
        skill_2_ready,
        skill_3_ready,
        skill_5_focus_ready,
        skill_5_sword_ready,
        skill_f1_ready,
        skill_f2_ready,
        skill_f5_ready,
        skill_heal_ready,
        skill_ultimate_ready,
        cc_bar,
    )


def do_opener():
    (
        skill_f3_ready,
        skill_illusion_ready,
        quickness,
        blade_count,
        weapon_swap_ready,
        skill_2_ready,
        skill_3_ready,
        skill_5_focus_ready,
        skill_5_sword_ready,
        skill_f1_ready,
        skill_f2_ready,
        skill_f5_ready,
        skill_heal_ready,
        skill_ultimate_ready,
        cc_bar,
    ) = scan_skills()
    key_press_delay = 10 / 1000
    time_adjustment = 0.93
    if (
        skill_illusion_ready
        and weapon_swap_ready
        and skill_2_ready
        and skill_3_ready
        and skill_5_sword_ready
        and skill_f1_ready
        and skill_f2_ready
        and skill_heal_ready
    ):
        autoit.send("{F2}")
        time.sleep(key_press_delay)
        autoit.send("{F2}")
        time.sleep(key_press_delay)
        time.sleep(0.44 * time_adjustment)
        autoit.send("3")
        time.sleep(key_press_delay)
        autoit.send("3")
        time.sleep(key_press_delay)
        time.sleep(0.4 * time_adjustment)
        autoit.send("5")
        time.sleep(key_press_delay)
        autoit.send("5")
        time.sleep(key_press_delay)
        autoit.send("{F5}")
        time.sleep(0.75 * time_adjustment)
        autoit.send("°")
        time.sleep(key_press_delay)
        autoit.send("°")
        time.sleep(0.1 * time_adjustment)
        autoit.send("5")
        time.sleep(key_press_delay)
        autoit.send("5")
        time.sleep(key_press_delay)
        autoit.send("{F5}")
        time.sleep(0.5 * time_adjustment)
    else:
        print("Cant do opener.")


def do_skyscale_bug():
    autoit.win_activate("Guild Wars 2")
    time.sleep(0.1)
    autoit.send("+y")
    time.sleep(1.75)
    autoit.send("{x down}")
    autoit.send("{1 down}")
    autoit.send("{x up}")
    autoit.send("{1 up}")
    time.sleep(1.2)
    autoit.mouse_click("left", 2308, 2100, 1, 0)
    time.sleep(1.75)
    autoit.send("^x")


def do_rotation(stop_event: Event, cc_supplier: Callable[[], bool]) -> None:
    key_press_delay = 10 / 1000
    time_adjustment = 0.93
    skill_2_time = 0.01
    skill_3_time = 0.01
    f1_timer_start = None
    f_time_max = 3
    min_blade_count = 5
    autoit.win_activate("Guild Wars 2")
    time.sleep(0.1)
    try:
        do_opener()
    except Exception:
        time.sleep(0.1)
    while True:
        try:
            cc_enabled = cc_supplier()
            if stop_event.is_set():
                break
            (
                skill_f3_ready,
                skill_illusion_ready,
                quickness,
                blade_count,
                weapon_swap_ready,
                skill_2_ready,
                skill_3_ready,
                skill_5_focus_ready,
                skill_5_sword_ready,
                skill_f1_ready,
                skill_f2_ready,
                skill_f5_ready,
                skill_heal_ready,
                skill_ultimate_ready,
                cc_bar,
            ) = scan_skills()
            time_adjustment = 1 if quickness else 2
            if blade_count >= min_blade_count:
                end_time = timer()
                if skill_f3_ready and cc_enabled and cc_bar:
                    autoit.send("{F3}")
                    time.sleep(key_press_delay)
                    autoit.send("{F3}")
                    time.sleep(0.25 * time_adjustment)
                    f1_timer_start = timer()
                elif skill_f2_ready:
                    if f1_timer_start is None:
                        autoit.send("{F2}")
                        time.sleep(key_press_delay)
                        autoit.send("{F2}")
                        time.sleep(0.25 * time_adjustment)
                        f1_timer_start = timer()
                    else:
                        end_time = timer()
                        if end_time - f1_timer_start > f_time_max:
                            autoit.send("{F2}")
                            time.sleep(key_press_delay)
                            autoit.send("{F2}")
                            time.sleep(0.25 * time_adjustment)
                            f1_timer_start = timer()
                        else:
                            if skill_ultimate_ready:
                                autoit.send("r")
                                time.sleep(key_press_delay)
                                autoit.send("r")
                            if skill_5_focus_ready or skill_5_sword_ready:
                                autoit.send("5")
                                time.sleep(key_press_delay)
                                autoit.send("5")
                                time.sleep(0.25 * time_adjustment)
                            if skill_3_ready:
                                autoit.send("3")
                                time.sleep(key_press_delay)
                                autoit.send("3")
                                time.sleep(skill_3_time * time_adjustment)
                            elif skill_2_ready:
                                autoit.send("2")
                                time.sleep(key_press_delay)
                                autoit.send("2")
                                time.sleep(skill_2_time * time_adjustment)
                elif skill_f1_ready:
                    if f1_timer_start is None:
                        autoit.send("{F1}")
                        time.sleep(key_press_delay)
                        autoit.send("{F1}")
                        time.sleep(0.375 * time_adjustment)
                        f1_timer_start = timer()
                    else:
                        end_time = timer()
                        if end_time - f1_timer_start > f_time_max:
                            autoit.send("{F1}")
                            time.sleep(key_press_delay)
                            autoit.send("{F1}")
                            time.sleep(0.375 * time_adjustment)
                            f1_timer_start = timer()
                        else:
                            if skill_ultimate_ready:
                                autoit.send("r")
                                time.sleep(key_press_delay)
                                autoit.send("r")
                            if skill_5_focus_ready or skill_5_sword_ready:
                                autoit.send("5")
                                time.sleep(key_press_delay)
                                autoit.send("5")
                                time.sleep(0.25 * time_adjustment)
                            if skill_3_ready:
                                autoit.send("3")
                                time.sleep(key_press_delay)
                                autoit.send("3")
                                time.sleep(skill_3_time * time_adjustment)
                            elif skill_2_ready:
                                autoit.send("2")
                                time.sleep(key_press_delay)
                                autoit.send("2")
                                time.sleep(skill_2_time * time_adjustment)
                elif skill_f5_ready:
                    if f1_timer_start is None:
                        autoit.send("{F5}")
                        time.sleep(key_press_delay)
                        autoit.send("{F5}")
                        f1_timer_start = timer()
                    else:
                        end_time = timer()
                        if end_time - f1_timer_start > f_time_max:
                            autoit.send("{F5}")
                            time.sleep(key_press_delay)
                            autoit.send("{F5}")
                            f1_timer_start = timer()
                        elif skill_ultimate_ready:
                            autoit.send("r")
                            time.sleep(key_press_delay)
                            autoit.send("r")
                else:
                    if skill_ultimate_ready:
                        autoit.send("r")
                        time.sleep(key_press_delay)
                        autoit.send("r")
                    if skill_5_focus_ready or skill_5_sword_ready:
                        autoit.send("5")
                        time.sleep(key_press_delay)
                        autoit.send("5")
                        time.sleep(0.25 * time_adjustment)
                    elif skill_heal_ready:
                        autoit.send("b")
                        time.sleep(key_press_delay)
                        autoit.send("b")
                        time.sleep(0.25 * time_adjustment)
                    elif skill_3_ready or skill_2_ready:
                        if skill_3_ready:
                            autoit.send("3")
                            time.sleep(key_press_delay)
                            autoit.send("3")
                            time.sleep(skill_3_time * time_adjustment)
                        elif skill_2_ready:
                            autoit.send("2")
                            time.sleep(key_press_delay)
                            autoit.send("2")
                            time.sleep(skill_2_time * time_adjustment)
                    else:
                        if weapon_swap_ready:
                            autoit.send("°")
                            time.sleep(key_press_delay)
                            autoit.send("°")
                            time.sleep(0.25 * time_adjustment)
                        else:
                            autoit.send("1")
                            time.sleep(key_press_delay)
                            autoit.send("1")
                            time.sleep(0.25 * time_adjustment)
        except Exception:
            time.sleep(0.1)


def read_text_from_image(image_path: str, tesseract_cmd: Optional[str] = None) -> str:
    try:
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        img = Image.open(image_path)
        return pytesseract.image_to_string(img)
    except Exception as exc:
        return f"Error: {exc}"


def char_get_name() -> str:
    ml = MumbleLink()
    try:
        link, _ = ml.read()
        while not link.uiTick:
            time.sleep(1)
            link, _ = ml.read()
        identity_str = link.identity
        try:
            identity_data = json.loads(identity_str)
            return identity_data.get("name", "Unknown Character")
        except json.JSONDecodeError:
            return "Unknown Character"
    finally:
        ml.close()


def get_character_list() -> list[str]:
    api_key = "0B7DC38C-23B0-D444-998C-53718A22155AFA9349A4-33DE-439C-9BF7-1AAD70DC39D5"
    url = "https://api.guildwars2.com/v2/characters/?access_token=" + api_key
    response = requests.get(url)
    parsed_items = json.loads(response.content)
    return sorted(parsed_items)


def remove_from_list(values: list[str], value: str) -> list[str]:
    if value in values:
        values.remove(value)
    return values


def is_shared_inv_open() -> bool:
    region = (1650, 748, 58, 42)
    screenshot = take_screenshot(region)
    screenshot.save("inv_open.png")
    time.sleep(0.1)
    locs = find_image_in_image("inv_open.png", "open_shared_inv.png")
    return bool(locs)


def is_shared_inv_closed() -> bool:
    region = (1650, 748, 58, 42)
    screenshot = take_screenshot(region)
    screenshot.save("inv_closed.png")
    time.sleep(0.1)
    locs = find_image_in_image("inv_closed.png", "closed_shared_inv.png")
    return bool(locs)


def farm_wvw() -> None:
    do_wvw()


def empty_out_character() -> None:
    autoit.auto_it_set_option("MouseClickDelay", 1)
    autoit.auto_it_set_option("MouseClickDownDelay", 1)
    autoit.auto_it_set_option("MouseClickDragDelay", 5)
    region = (2190, 577, 136, 38)
    screenshot = take_screenshot(region)
    screenshot.save("test.png")
    time.sleep(0.01)
    tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    extracted_text = read_text_from_image("test.png", tesseract_cmd)
    if "Inventory" not in extracted_text:
        autoit.send("i")
        time.sleep(0.5)
    region = (1447, 675, 190, 34)
    screenshot = take_screenshot(region)
    screenshot.save("test.png")
    time.sleep(0.01)
    extracted_text = read_text_from_image("test.png", tesseract_cmd)
    if "Account" not in extracted_text:
        autoit.mouse_click("left", 2070, 828, 1, 0)
        time.sleep(0.5)
    region = (1426, 755, 206, 60)
    screenshot = take_screenshot(region)
    screenshot.save("test.png")
    time.sleep(0.01)
    extracted_text = read_text_from_image("test.png", tesseract_cmd)
    if "Account" not in extracted_text:
        autoit.mouse_click("left", 1687, 775, 1, 0)
        time.sleep(1)
    for row in range(860, 1135, 65):
        for col in range(1468, 1678, 65):
            autoit.mouse_click("left", col, row, 2, 0)
            time.sleep(0.1)
    for row in range(1228, 1441, 65):
        for col in range(1468, 1678, 65):
            autoit.mouse_click("left", col, row, 2, 0)
            time.sleep(0.1)


def look_for_char(char_name: str) -> None:
    autoit.win_activate("Guild Wars 2")
    time.sleep(0.25)
    tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    if is_in_char_select_screen():
        time.sleep(0.1)
        autoit.mouse_move(1000, 1000, 0)
    else:
        autoit.mouse_click("left", 18, 18, 1, 0)
        time.sleep(0.5)
        autoit.mouse_click("left", 1906, 1134, 1, 0)
        time.sleep(0.5)
        autoit.mouse_click("left", 1906, 1143, 1, 0)
        while True:
            time.sleep(0.25)
            if is_in_char_select_screen():
                break
    for _ in range(72):
        region = (48, 1800, 300, 45)
        screenshot = take_screenshot(region)
        screenshot.save("char_name.png")
        time.sleep(0.1)
        current_char = read_text_from_image("char_name.png", tesseract_cmd)
        if char_name in current_char:
            autoit.send("{ENTER}")
            break
        else:
            autoit.send("{RIGHT}")


def alt_char_farm(
    update_status: Callable[[str], None],
    pause_event: Event,
    completion_callback: Optional[Callable[[dict], None]] = None,
    should_skip_character: Optional[Callable[[str], bool]] = None,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> None:
    def wait_if_paused() -> None:
        if pause_event.is_set():
            return
        pause_event.wait()
        autoit.win_activate("Guild Wars 2")
        time.sleep(0.2)

    login_counter = 0
    autoit.win_activate("Guild Wars 2")
    if not is_in_char_select_screen():
        autoit.mouse_click("left", 18, 18, 1, 0)
        time.sleep(0.5)
        autoit.mouse_click("left", 1906, 1134, 1, 0)
        time.sleep(0.5)
        autoit.mouse_click("left", 1906, 1143, 1, 0)
        while True:
            time.sleep(0.25)
            if is_in_char_select_screen():
                break
    character_list = get_character_list()
    processed_characters = 0
    emptied_any_character = False
    skipped_characters = 0
    consecutive_already = 0
    stop_after_logout = False
    stopped_due_to_repeats = False
    while character_list:
        wait_if_paused()
        if not _is_gw2_window_foreground():
            update_status(
                "Guild Wars 2 is not foreground; waiting before selecting a character."
            )
            time.sleep(0.5)
            continue
        empty_this_char = True
        login_counter += 1
        if not _click_character_selection_slot(3727, 2058):
            update_status(
                "Guild Wars 2 lost focus; waiting before selecting a character."
            )
            continue
        time.sleep(1)
        if not _click_character_selection_slot(3727, 2058):
            update_status(
                "Guild Wars 2 lost focus; waiting before selecting a character."
            )
            continue
        time.sleep(2.5)
        if login_counter % 20 == 0:
            time.sleep(15 if constants.EMPTY_CHARS else 180)
        elif login_counter % 10 == 0:
            time.sleep(15 if constants.EMPTY_CHARS else 60)
        if login_counter % 3 == 1:
            character_x = 3610
        elif login_counter % 3 == 2:
            character_x = 3490
        else:
            character_x = 3380
        if not _click_character_selection_slot(character_x, 2062):
            update_status(
                "Guild Wars 2 lost focus; waiting before selecting a character."
            )
            continue
        login_attempt_counter = 0
        while True:
            wait_if_paused()
            if not is_in_char_select_screen():
                time.sleep(1)
                break
            time.sleep(0.5)
            login_attempt_counter += 1
            if login_attempt_counter > 20:
                login_attempt_counter = 0
                if not _click_character_selection_slot(3610, 2062):
                    update_status(
                        "Guild Wars 2 is not foreground; waiting before retrying character selection."
                    )
                    time.sleep(0.5)
                    continue
        char_name = char_get_name()
        character_list = remove_from_list(character_list, char_name)
        already_farmed = False
        if should_skip_character is not None:
            try:
                already_farmed = bool(should_skip_character(char_name))
            except Exception:
                already_farmed = False
        for skip in constants.CHARS_TO_SKIP:
            if skip in char_name:
                empty_this_char = False
        if already_farmed:
            skipped_characters += 1
            consecutive_already += 1
            update_status(f"{char_name} already farmed today; skipping.")
            time.sleep(1)
            if progress_callback is not None:
                try:
                    progress_callback({"name": char_name, "status": "skipped-already"})
                except Exception:
                    pass
            if consecutive_already >= 3:
                update_status(
                    "Stopping early: encountered three characters already farmed today."
                )
                stop_after_logout = True
                stopped_due_to_repeats = True
        else:
            consecutive_already = 0
            wait_if_paused()
            autoit.send("f")
            time.sleep(1)
            if empty_this_char and constants.EMPTY_CHARS:
                wait_if_paused()
                empty_out_character()
                emptied_any_character = True
            processed_characters += 1
            if progress_callback is not None:
                try:
                    progress_callback(
                        {
                            "name": char_name,
                            "status": "farmed",
                            "emptied": bool(empty_this_char and constants.EMPTY_CHARS),
                        }
                    )
                except Exception:
                    pass
        chars_left = len(character_list)
        update_status(f"{chars_left} left to farm.")
        autoit.mouse_click("left", 18, 18, 1, 0)
        time.sleep(0.5)
        autoit.mouse_click("left", 1906, 1134, 1, 0)
        time.sleep(0.5)
        autoit.mouse_click("left", 1906, 1143, 1, 0)
        log_out_counter = 0
        while True:
            wait_if_paused()
            time.sleep(0.25)
            log_out_counter += 1
            if log_out_counter > 30:
                autoit.mouse_click("left", 18, 18, 1, 0)
                time.sleep(0.5)
                autoit.mouse_click("left", 1906, 1134, 1, 0)
                time.sleep(0.5)
                autoit.mouse_click("left", 1906, 1143, 1, 0)
            if is_in_char_select_screen():
                break
        if stop_after_logout:
            break
    for _ in range(3):
        play_beep()
        time.sleep(0.5)
    update_status("Farming done.")
    if constants.SHUTDOWN:
        autoit.shutdown(1)
        send_message("Shutdown successfully.")
    if completion_callback is not None:
        try:
            completion_callback(
                {
                    "characters_farmed": processed_characters,
                    "emptied": emptied_any_character,
                    "skipped_characters": skipped_characters,
                    "stopped_due_to_repeats": stopped_due_to_repeats,
                }
            )
        except Exception:
            pass


def clipboard_event_code() -> Optional[str]:
    data = get_next_event()
    if data is None:
        return None
    event, code = data
    pyperclip.copy(code)
    return str(event)
