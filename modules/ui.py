import os
import webbrowser
import customtkinter as ctk
from typing import Callable, Tuple
import cv2
from cv2_enumerate_cameras import enumerate_cameras
from PIL import Image, ImageOps
import tkinterdnd2 as tkdnd
import time
import json

import modules.globals
import modules.metadata
from modules.face_analyser import (
    get_one_face,
    get_unique_faces_from_target_image,
    get_unique_faces_from_target_video,
    add_blank_map,
    has_valid_map,
    simplify_maps,
)
from modules.capturer import get_video_frame, get_video_frame_total
from modules.processors.frame.core import get_frame_processors_modules
from modules.utilities import (
    is_image,
    is_video,
    resolve_relative_path,
    has_image_extension,
)

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_SCREEN_SCALE_FACTORS"] = "1"
os.environ["QT_SCALE_FACTOR"] = "1"

ROOT = None
POPUP = None
POPUP_LIVE = None
ROOT_HEIGHT = 800
ROOT_WIDTH = 1000

PREVIEW = None
PREVIEW_MAX_HEIGHT = 800
PREVIEW_MAX_WIDTH = 1400
PREVIEW_DEFAULT_WIDTH = 1280
PREVIEW_DEFAULT_HEIGHT = 720

POPUP_WIDTH = 700
POPUP_HEIGHT = 800
POPUP_SCROLL_WIDTH = 680
POPUP_SCROLL_HEIGHT = 600

POPUP_LIVE_WIDTH = 850
POPUP_LIVE_HEIGHT = 700
POPUP_LIVE_SCROLL_WIDTH = 830
POPUP_LIVE_SCROLL_HEIGHT = 600

MAPPER_PREVIEW_MAX_HEIGHT = 120
MAPPER_PREVIEW_MAX_WIDTH = 120

DEFAULT_BUTTON_WIDTH = 200
DEFAULT_BUTTON_HEIGHT = 40

RECENT_DIRECTORY_SOURCE = None
RECENT_DIRECTORY_TARGET = None
RECENT_DIRECTORY_OUTPUT = None

preview_label = None
preview_slider = None
source_label = None
target_label = None
status_label = None
popup_status_label = None
popup_status_label_live = None
source_label_dict = {}
source_label_dict_live = {}
target_label_dict_live = {}

img_ft, vid_ft = modules.globals.file_types


class ModernButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(
            font=("Roboto", 16, "bold"),
            corner_radius=15,
            border_width=2,
            border_color="#3a7ebf",
            hover_color="#2b5d8b",
            fg_color="#3a7ebf",
            text_color="white",
        )


class DragDropButton(ModernButton):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.drop_target_register(tkdnd.DND_FILES)
        self.dnd_bind("<<Drop>>", self.drop)

    def drop(self, event):
        file_path = event.data
        if file_path.startswith("{"):
            file_path = file_path[1:-1]
        self.handle_drop(file_path)

    def handle_drop(self, file_path):
        pass


class SourceButton(DragDropButton):
    def handle_drop(self, file_path):
        if is_image(file_path):
            modules.globals.source_path = file_path
            global RECENT_DIRECTORY_SOURCE
            RECENT_DIRECTORY_SOURCE = os.path.dirname(modules.globals.source_path)
            image = render_image_preview(modules.globals.source_path, (250, 250))
            source_label.configure(image=image)
            source_label.configure(text="")


class SourceMapperButton(DragDropButton):
    def __init__(self, master, map, button_num, **kwargs):
        super().__init__(master, **kwargs)
        self.map = map
        self.button_num = button_num

    def handle_drop(self, file_path):
        if is_image(file_path):
            update_popup_source(
                self.master.master, self.map, self.button_num, file_path
            )


class TargetButton(DragDropButton):
    def handle_drop(self, file_path):
        global RECENT_DIRECTORY_TARGET
        if is_image(file_path) or is_video(file_path):
            modules.globals.target_path = file_path
            RECENT_DIRECTORY_TARGET = os.path.dirname(modules.globals.target_path)
            if is_image(file_path):
                image = render_image_preview(modules.globals.target_path, (250, 250))
                target_label.configure(image=image)
                target_label.configure(text="")
            elif is_video(file_path):
                video_frame = render_video_preview(file_path, (250, 250))
                target_label.configure(image=video_frame)
                target_label.configure(text="")


class ModernLabel(ctk.CTkLabel):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(
            font=("Roboto", 16),
            corner_radius=10,
            fg_color="#2a2d2e",
            text_color="white",
        )


class DragDropLabel(ModernLabel):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.drop_target_register(tkdnd.DND_FILES)
        self.dnd_bind("<<Drop>>", self.drop)

    def drop(self, event):
        file_path = event.data
        if file_path.startswith("{"):
            file_path = file_path[1:-1]
        self.handle_drop(file_path)

    def handle_drop(self, file_path):
        pass


class SourceLabel(DragDropLabel):
    def handle_drop(self, file_path):
        if is_image(file_path):
            modules.globals.source_path = file_path
            global RECENT_DIRECTORY_SOURCE
            RECENT_DIRECTORY_SOURCE = os.path.dirname(modules.globals.source_path)
            image = render_image_preview(modules.globals.source_path, (250, 250))
            source_label.configure(image=image)
            source_label.configure(text="")


class TargetLabel(DragDropLabel):
    def handle_drop(self, file_path):
        global RECENT_DIRECTORY_TARGET
        if is_image(file_path) or is_video(file_path):
            modules.globals.target_path = file_path
            RECENT_DIRECTORY_TARGET = os.path.dirname(modules.globals.target_path)
            if is_image(file_path):
                image = render_image_preview(modules.globals.target_path, (250, 250))
                target_label.configure(image=image)
                target_label.configure(text="")
            elif is_video(file_path):
                video_frame = render_video_preview(file_path, (250, 250))
                target_label.configure(image=video_frame)
                target_label.configure(text="")


def save_switch_states():
    switch_states = {
        "keep_fps": modules.globals.keep_fps,
        "keep_audio": modules.globals.keep_audio,
        "keep_frames": modules.globals.keep_frames,
        "many_faces": modules.globals.many_faces,
        "map_faces": modules.globals.map_faces,
        "color_correction": modules.globals.color_correction,
        "nsfw_filter": modules.globals.nsfw_filter,  # Add this line
        "live_mirror": modules.globals.live_mirror,
        "live_resizable": modules.globals.live_resizable,
        "fp_ui": modules.globals.fp_ui,
        "show_fps": modules.globals.show_fps,
        "mouth_mask": modules.globals.mouth_mask,
        "show_mouth_mask_box": modules.globals.show_mouth_mask_box,
        "mask_down_size": modules.globals.mask_down_size,
        "mask_feather_ratio": modules.globals.mask_feather_ratio,
    }
    with open("switch_states.json", "w") as f:
        json.dump(switch_states, f)


def load_switch_states():
    try:
        with open("switch_states.json", "r") as f:
            switch_states = json.load(f)
        modules.globals.keep_fps = switch_states.get("keep_fps", True)
        modules.globals.keep_audio = switch_states.get("keep_audio", True)
        modules.globals.keep_frames = switch_states.get("keep_frames", False)
        modules.globals.many_faces = switch_states.get("many_faces", False)
        modules.globals.map_faces = switch_states.get("map_faces", False)
        modules.globals.color_correction = switch_states.get("color_correction", False)
        modules.globals.nsfw_filter = switch_states.get("nsfw_filter", False)
        modules.globals.live_mirror = switch_states.get("live_mirror", False)
        modules.globals.live_resizable = switch_states.get("live_resizable", False)
        modules.globals.fp_ui = switch_states.get("fp_ui", {"face_enhancer": False})
        modules.globals.show_fps = switch_states.get("show_fps", False)
        modules.globals.mouth_mask = switch_states.get("mouth_mask", False)
        modules.globals.show_mouth_mask_box = switch_states.get(
            "show_mouth_mask_box", False
        )
        modules.globals.mask_down_size = switch_states.get("mask_down_size", 0.5)
        modules.globals.mask_feather_ratio = switch_states.get("mask_feather_ratio", 8)
    except FileNotFoundError:
        # If the file doesn't exist, use default values
        pass


def init(start: Callable[[], None], destroy: Callable[[], None]) -> tkdnd.TkinterDnD.Tk:
    global ROOT, PREVIEW, donate_frame

    ROOT = create_root(start, destroy)
    PREVIEW = create_preview(ROOT)

    return ROOT


def create_root(
    start: Callable[[], None], destroy: Callable[[], None]
) -> tkdnd.TkinterDnD.Tk:
    global source_label, target_label, status_label, donate_frame, show_fps_switch

    load_switch_states()

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = tkdnd.TkinterDnD.Tk()
    root.title(
        f"{modules.metadata.name} {modules.metadata.version} {modules.metadata.edition}"
    )
    root.configure(bg="#1a1a1a")
    root.protocol("WM_DELETE_WINDOW", lambda: destroy())
    root.resizable(True, True)
    root.attributes("-alpha", 1.0)

    main_frame = ctk.CTkFrame(root, fg_color="#1a1a1a")
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Create two vertical frames for source and target
    source_frame = ctk.CTkFrame(main_frame, fg_color="#2a2d2e", corner_radius=15)
    source_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    target_frame = ctk.CTkFrame(main_frame, fg_color="#2a2d2e", corner_radius=15)
    target_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

    # Create a middle frame for swap button
    middle_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a1a")
    middle_frame.grid(row=0, column=1, padx=5, pady=10, sticky="ns")

    source_label = SourceLabel(
        source_frame,
        text="Drag & Drop\nSource Image Here",
        justify="center",
        width=250,
        height=250,
    )
    source_label.pack(pady=(20, 10))

    target_label = TargetLabel(
        target_frame,
        text="Drag & Drop\nTarget Image/Video Here",
        justify="center",
        width=250,
        height=250,
    )
    target_label.pack(pady=(20, 10))

    select_face_button = SourceButton(
        source_frame,
        text="Select a face",
        cursor="hand2",
        command=lambda: select_source_path(),
    )
    select_face_button.pack(pady=10)

    select_target_button = TargetButton(
        target_frame,
        text="Select a target",
        cursor="hand2",
        command=lambda: select_target_path(),
    )
    select_target_button.pack(pady=10)

    swap_faces_button = ModernButton(
        middle_frame,
        text="↔",
        cursor="hand2",
        command=lambda: swap_faces_paths(),
        width=50,
        height=50,
    )
    swap_faces_button.pack(expand=True)

    options_frame = ctk.CTkFrame(main_frame, fg_color="#2a2d2e", corner_radius=15)
    options_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

    # Create two columns for options
    left_column = ctk.CTkFrame(options_frame, fg_color="#2a2d2e")
    left_column.pack(side="left", padx=20, expand=True)

    right_column = ctk.CTkFrame(options_frame, fg_color="#2a2d2e")
    right_column.pack(side="right", padx=20, expand=True)

    # Left column - Video/Processing Options
    keep_fps_value = ctk.BooleanVar(value=modules.globals.keep_fps)
    keep_fps_checkbox = ctk.CTkSwitch(
        left_column,
        text="Keep fps",
        variable=keep_fps_value,
        cursor="hand2",
        command=lambda: (
            setattr(modules.globals, "keep_fps", keep_fps_value.get()),
            save_switch_states(),
        ),
        progress_color="#3a7ebf",
        font=("Roboto", 14, "bold"),
    )
    keep_fps_checkbox.pack(pady=5, anchor="w")

    keep_audio_value = ctk.BooleanVar(value=modules.globals.keep_audio)
    keep_audio_switch = ctk.CTkSwitch(
        left_column,
        text="Keep audio",
        variable=keep_audio_value,
        cursor="hand2",
        command=lambda: (
            setattr(modules.globals, "keep_audio", keep_audio_value.get()),
            save_switch_states(),
        ),
        progress_color="#3a7ebf",
        font=("Roboto", 14, "bold"),
    )
    keep_audio_switch.pack(pady=5, anchor="w")

    keep_frames_value = ctk.BooleanVar(value=modules.globals.keep_frames)
    keep_frames_switch = ctk.CTkSwitch(
        left_column,
        text="Keep frames",
        variable=keep_frames_value,
        cursor="hand2",
        command=lambda: (
            setattr(modules.globals, "keep_frames", keep_frames_value.get()),
            save_switch_states(),
        ),
        progress_color="#3a7ebf",
        font=("Roboto", 14, "bold"),
    )
    keep_frames_switch.pack(pady=5, anchor="w")

    # Face Processing Options
    enhancer_value = ctk.BooleanVar(value=modules.globals.fp_ui["face_enhancer"])
    enhancer_switch = ctk.CTkSwitch(
        left_column,
        text="Face Enhancer",
        variable=enhancer_value,
        cursor="hand2",
        command=lambda: (
            update_tumbler("face_enhancer", enhancer_value.get()),
            save_switch_states(),
        ),
        progress_color="#3a7ebf",
        font=("Roboto", 14, "bold"),
    )
    enhancer_switch.pack(pady=5, anchor="w")

    color_correction_value = ctk.BooleanVar(value=modules.globals.color_correction)
    color_correction_switch = ctk.CTkSwitch(
        left_column,
        text="Fix Blueish Cam",
        variable=color_correction_value,
        cursor="hand2",
        command=lambda: (
            setattr(modules.globals, "color_correction", color_correction_value.get()),
            save_switch_states(),
        ),
        progress_color="#3a7ebf",
        font=("Roboto", 14, "bold"),
    )
    color_correction_switch.pack(pady=5, anchor="w")

    # Right column - Face Detection & Masking Options
    many_faces_value = ctk.BooleanVar(value=modules.globals.many_faces)
    many_faces_switch = ctk.CTkSwitch(
        right_column,
        text="Many faces",
        variable=many_faces_value,
        cursor="hand2",
        command=lambda: (
            setattr(modules.globals, "many_faces", many_faces_value.get()),
            save_switch_states(),
        ),
        progress_color="#3a7ebf",
        font=("Roboto", 14, "bold"),
    )
    many_faces_switch.pack(pady=5, anchor="w")

    show_fps_value = ctk.BooleanVar(value=modules.globals.show_fps)
    show_fps_switch = ctk.CTkSwitch(
        right_column,
        text="Show FPS",
        variable=show_fps_value,
        cursor="hand2",
        command=lambda: (
            setattr(modules.globals, "show_fps", show_fps_value.get()),
            save_switch_states(),
        ),
        progress_color="#3a7ebf",
        font=("Roboto", 14, "bold"),
    )
    show_fps_switch.pack(pady=5, anchor="w")

    map_faces = ctk.BooleanVar(value=modules.globals.map_faces)
    map_faces_switch = ctk.CTkSwitch(
        right_column,
        text="Map faces",
        variable=map_faces,
        cursor="hand2",
        command=lambda: (
            setattr(modules.globals, "map_faces", map_faces.get()),
            save_switch_states(),
        ),
        progress_color="#3a7ebf",
        font=("Roboto", 14, "bold"),
    )
    map_faces_switch.pack(pady=5, anchor="w")

    # Face Opacity Controls
    opacity_frame = ctk.CTkFrame(right_column, fg_color="#2a2d2e")
    opacity_frame.pack(pady=5, anchor="w", fill="x")

    opacity_switch = ctk.CTkSwitch(
        opacity_frame,
        text="Face Opacity",
        variable=ctk.BooleanVar(value=modules.globals.opacity_switch),
        cursor="hand2",
        command=lambda: setattr(
            modules.globals, "opacity_switch", not modules.globals.opacity_switch
        ),
        progress_color="#3a7ebf",
        font=("Roboto", 14, "bold"),
    )
    opacity_switch.pack(side="left", padx=(0, 10))

    opacity_slider = ctk.CTkSlider(
        opacity_frame,
        from_=0,
        to=100,
        number_of_steps=100,
        command=update_opacity,
        fg_color=("gray75", "gray25"),
        progress_color="#3a7ebf",
        button_color="#3a7ebf",
        button_hover_color="#2b5d8b",
    )
    opacity_slider.pack(side="left", fill="x", expand=True)
    opacity_slider.set(modules.globals.face_opacity)

    # Mouth Mask Controls
    mouth_mask_var = ctk.BooleanVar(value=modules.globals.mouth_mask)
    mouth_mask_switch = ctk.CTkSwitch(
        right_column,
        text="Mouth Mask",
        variable=mouth_mask_var,
        cursor="hand2",
        command=lambda: (
            setattr(modules.globals, "mouth_mask", mouth_mask_var.get()),
            save_switch_states(),
        ),
        progress_color="#3a7ebf",
        font=("Roboto", 14, "bold"),
    )
    mouth_mask_switch.pack(pady=5, anchor="w")

    show_mouth_mask_box_var = ctk.BooleanVar(value=modules.globals.show_mouth_mask_box)
    show_mouth_mask_box_switch = ctk.CTkSwitch(
        right_column,
        text="Show Mouth Box",
        variable=show_mouth_mask_box_var,
        cursor="hand2",
        command=lambda: (
            setattr(
                modules.globals, "show_mouth_mask_box", show_mouth_mask_box_var.get()
            ),
            save_switch_states(),
        ),
        progress_color="#3a7ebf",
        font=("Roboto", 14, "bold"),
    )
    show_mouth_mask_box_switch.pack(pady=5, anchor="w")

    # Mask Size Controls
    mask_down_size_label = ctk.CTkLabel(
        right_column, text="Mask Size:", font=("Roboto", 12)
    )
    mask_down_size_label.pack(pady=(5, 0), anchor="w")

    mask_down_size_slider = ctk.CTkSlider(
        right_column,
        from_=0.1,
        to=1.0,
        number_of_steps=9,
        command=lambda value: [
            setattr(modules.globals, "mask_down_size", value),
            save_switch_states(),
        ],
    )
    mask_down_size_slider.set(modules.globals.mask_down_size)
    mask_down_size_slider.pack(pady=(0, 5), fill="x")

    # Mask Feather Controls
    mask_feather_label = ctk.CTkLabel(
        right_column, text="Mask Feather:", font=("Roboto", 12)
    )
    mask_feather_label.pack(pady=(5, 0), anchor="w")

    mask_feather_slider = ctk.CTkSlider(
        right_column,
        from_=4,
        to=16,
        number_of_steps=12,
        command=lambda value: [
            setattr(modules.globals, "mask_feather_ratio", int(value)),
            save_switch_states(),
        ],
    )
    mask_feather_slider.set(modules.globals.mask_feather_ratio)
    mask_feather_slider.pack(pady=(0, 5), fill="x")

    button_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a1a")
    button_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

    start_button = ModernButton(
        button_frame,
        text="Start",
        cursor="hand2",
        command=lambda: [
            (
                donate_frame.destroy()
                if "donate_frame" in globals() and donate_frame.winfo_exists()
                else None
            ),
            analyze_target(start, root),
        ],
        fg_color="#4CAF50",
        hover_color="#45a049",
    )
    start_button.pack(side="left", padx=10, expand=True)

    preview_button = ModernButton(
        button_frame, text="Preview", cursor="hand2", command=lambda: toggle_preview()
    )
    preview_button.pack(side="left", padx=10, expand=True)

    stop_button = ModernButton(
        button_frame,
        text="Destroy",
        cursor="hand2",
        command=lambda: destroy(),
        fg_color="#f44336",
        hover_color="#d32f2f",
    )
    stop_button.pack(side="left", padx=10, expand=True)

    # Camera Selection
    camera_frame = ctk.CTkFrame(main_frame, fg_color="#2a2d2e", corner_radius=15)
    camera_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="ew")

    camera_label = ctk.CTkLabel(
        camera_frame, text="Select Camera:", font=("Roboto", 14)
    )
    camera_label.pack(side="left", padx=(20, 10), pady=10)

    available_cameras = get_available_cameras()
    available_camera_indices, available_camera_strings = available_cameras
    camera_variable = ctk.StringVar(
        value=(
            available_camera_strings[0]
            if available_camera_strings
            else "No cameras found"
        )
    )
    camera_optionmenu = ctk.CTkOptionMenu(
        camera_frame,
        variable=camera_variable,
        values=available_camera_strings,
        width=200,
        font=("Roboto", 14),
    )
    camera_optionmenu.pack(side="left", padx=10, pady=10)

    live_button = ModernButton(
        camera_frame,
        text="Live",
        cursor="hand2",
        command=lambda: [
            (
                donate_frame.destroy()
                if "donate_frame" in globals() and donate_frame.winfo_exists()
                else None
            ),
            webcam_preview(
                root,
                available_camera_indices[
                    available_camera_strings.index(camera_variable.get())
                ],
            ),
        ],
    )
    live_button.pack(side="left", padx=10, pady=10)

    status_label = ModernLabel(
        main_frame, text=None, justify="center", fg_color="#1a1a1a"
    )
    status_label.grid(row=4, column=0, columnspan=3, pady=10, sticky="ew")

    donate_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a1a")
    donate_frame.grid(row=4, column=0, columnspan=3, pady=5, sticky="ew")

    donate_label = ModernLabel(
        donate_frame,
        text="Donate",
        justify="center",
        cursor="hand2",
        fg_color="#1870c4",
        text_color="#1870c4",
    )
    donate_label.pack(side="left", expand=True)
    donate_label.bind(
        "<Button>", lambda event: webbrowser.open("https://paypal.me/hacksider")
    )

    remove_donate_button = ModernButton(
        donate_frame,
        text="X",
        cursor="hand2",
        command=lambda: donate_frame.destroy(),
        width=30,
        height=30,
        fg_color="#f44336",
        hover_color="#d32f2f",
    )
    remove_donate_button.pack(side="right", padx=(10, 0))

    main_frame.grid_columnconfigure((0, 2), weight=1)
    main_frame.grid_rowconfigure((0, 1, 2), weight=1)

    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)

    return root


def analyze_target(start: Callable[[], None], root: ctk.CTk):
    if POPUP is not None and POPUP.winfo_exists():
        update_status("Please complete pop-up or close it.")
        return

    if modules.globals.map_faces:
        modules.globals.souce_target_map = []

        if is_image(modules.globals.target_path):
            update_status("Getting unique faces")
            get_unique_faces_from_target_image()
        elif is_video(modules.globals.target_path):
            update_status("Getting unique faces")
            get_unique_faces_from_target_video()
        else:
            update_status("Invalid target file. Please select an image or video.")
            return

        if len(modules.globals.souce_target_map) > 0:
            create_source_target_popup(start, root, modules.globals.souce_target_map)
        else:
            update_status("No faces found in target")
    else:
        select_output_path(start)


def create_source_target_popup(
    start: Callable[[], None], root: ctk.CTk, map: list
) -> None:
    global POPUP, popup_status_label

    POPUP = ctk.CTkToplevel(root)
    POPUP.title("Source x Target Mapper")
    POPUP.geometry(f"{POPUP_WIDTH}x{POPUP_HEIGHT}")
    POPUP.focus()
    POPUP.resizable(True, True)

    def on_submit_click(start):
        if has_valid_map():
            POPUP.destroy()
            select_output_path(start)
        else:
            update_pop_status("At least 1 source with target is required!")

    scrollable_frame = ctk.CTkScrollableFrame(
        POPUP, width=POPUP_SCROLL_WIDTH, height=POPUP_SCROLL_HEIGHT
    )
    scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def on_button_click(map, button_num):
        update_popup_source(scrollable_frame, map, button_num)

    # Create a frame to hold the table
    table_frame = ctk.CTkFrame(scrollable_frame)
    table_frame.pack(expand=True)

    for item in map:
        id = item["id"]

        row_frame = ctk.CTkFrame(table_frame)
        row_frame.pack(fill="x", pady=5)

        source_button = SourceMapperButton(
            row_frame,
            map,
            id,
            text="Select source image",
            command=lambda id=id: on_button_click(map, id),
            width=DEFAULT_BUTTON_WIDTH,
            height=DEFAULT_BUTTON_HEIGHT,
            fg_color=("gray75", "gray25"),
            hover_color=("gray85", "gray35"),
            corner_radius=10,
        )
        source_button.pack(side="left", padx=(0, 10))

        source_image = ctk.CTkLabel(
            row_frame,
            text=f"S-{id}",
            width=MAPPER_PREVIEW_MAX_WIDTH,
            height=MAPPER_PREVIEW_MAX_HEIGHT,
            font=("Arial", 14, "bold"),
        )
        source_image.pack(side="left", padx=(0, 10))

        x_label = ctk.CTkLabel(
            row_frame,
            text=f"X",
            width=30,
            font=("Arial", 14, "bold"),
        )
        x_label.pack(side="left", padx=(0, 10))

        image = Image.fromarray(cv2.cvtColor(item["target"]["cv2"], cv2.COLOR_BGR2RGB))
        image = image.resize(
            (MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS
        )
        tk_image = ctk.CTkImage(image, size=image.size)

        target_image = ctk.CTkLabel(
            row_frame,
            text=f"T-{id}",
            width=MAPPER_PREVIEW_MAX_WIDTH,
            height=MAPPER_PREVIEW_MAX_HEIGHT,
            font=("Arial", 14, "bold"),
        )
        target_image.pack(side="left")
        target_image.configure(image=tk_image)

    popup_status_label = ctk.CTkLabel(
        POPUP, text=None, justify="center", font=("Arial", 14, "bold")
    )
    popup_status_label.pack(pady=10)

    submit_button = ctk.CTkButton(
        POPUP,
        text="Submit",
        command=lambda: on_submit_click(start),
        fg_color=("DodgerBlue", "DodgerBlue"),
        hover_color=("RoyalBlue", "RoyalBlue"),
        corner_radius=10,
        font=("Arial", 16, "bold"),
        width=200,
        height=50,
    )
    submit_button.pack(pady=10)

    POPUP.update()
    POPUP.minsize(POPUP.winfo_width(), POPUP.winfo_height())


def update_popup_source(
    scrollable_frame: ctk.CTkScrollableFrame,
    map: list,
    button_num: int,
    source_path: str = None,
) -> list:
    global source_label_dict, RECENT_DIRECTORY_SOURCE

    if source_path is None:
        source_path = ctk.filedialog.askopenfilename(
            title="select an source image",
            initialdir=RECENT_DIRECTORY_SOURCE,
            filetypes=[img_ft],
        )

    if "source" in map[button_num]:
        map[button_num].pop("source")
        if button_num in source_label_dict:
            source_label_dict[button_num].destroy()
            del source_label_dict[button_num]

    if source_path == "":
        return map
    else:
        RECENT_DIRECTORY_SOURCE = os.path.dirname(source_path)
        cv2_img = cv2.imread(source_path)
        face = get_one_face(cv2_img)

        if face:
            x_min, y_min, x_max, y_max = face["bbox"]

            map[button_num]["source"] = {
                "cv2": cv2_img[int(y_min) : int(y_max), int(x_min) : int(x_max)],
                "face": face,
            }

            image = Image.fromarray(
                cv2.cvtColor(map[button_num]["source"]["cv2"], cv2.COLOR_BGR2RGB)
            )
            image = image.resize(
                (MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS
            )
            tk_image = ctk.CTkImage(image, size=image.size)

            source_image = ctk.CTkLabel(
                scrollable_frame.winfo_children()[button_num],
                text=f"S-{button_num}",
                width=MAPPER_PREVIEW_MAX_WIDTH,
                height=MAPPER_PREVIEW_MAX_HEIGHT,
                font=("Arial", 14, "bold"),
            )
            source_image.pack(
                side="left",
                padx=(0, 10),
                after=scrollable_frame.winfo_children()[button_num].winfo_children()[0],
            )
            source_image.configure(image=tk_image)
            source_label_dict[button_num] = source_image
        else:
            update_pop_status("Face could not be detected in last upload!")
        return map


def create_preview(parent: ctk.CTkToplevel) -> ctk.CTkToplevel:
    global preview_label, preview_slider

    preview = ctk.CTkToplevel(parent)
    preview.withdraw()
    preview.title("Preview")
    preview.configure()
    preview.protocol("WM_DELETE_WINDOW", lambda: toggle_preview())
    preview.resizable(width=True, height=True)

    preview_label = ctk.CTkLabel(preview, text=None, font=("Arial", 14, "bold"))
    preview_label.pack(fill="both", expand=True)

    preview_slider = ctk.CTkSlider(
        preview,
        from_=0,
        to=0,
        command=lambda frame_value: update_preview(int(frame_value)),
        fg_color=("gray75", "gray25"),
        progress_color=("DodgerBlue", "DodgerBlue"),
        button_color=("DodgerBlue", "DodgerBlue"),
        button_hover_color=("RoyalBlue", "RoyalBlue"),
    )
    preview_slider.pack(fill="x", padx=20, pady=10)

    # Add keyboard bindings for left and right arrow keys
    preview.bind("<Left>", lambda event: navigate_frames(-1))
    preview.bind("<Right>", lambda event: navigate_frames(1))

    return preview


def update_status(text: str) -> None:
    status_label.configure(text=text)
    ROOT.update()


def update_pop_status(text: str) -> None:
    popup_status_label.configure(text=text)


def update_pop_live_status(text: str) -> None:
    popup_status_label_live.configure(text=text)


def update_tumbler(var: str, value: bool) -> None:
    modules.globals.fp_ui[var] = value


def select_source_path() -> None:
    global RECENT_DIRECTORY_SOURCE, img_ft, vid_ft

    PREVIEW.withdraw()
    source_path = ctk.filedialog.askopenfilename(
        title="select an source image",
        initialdir=RECENT_DIRECTORY_SOURCE,
        filetypes=[img_ft],
    )
    if is_image(source_path):
        modules.globals.source_path = source_path
        RECENT_DIRECTORY_SOURCE = os.path.dirname(modules.globals.source_path)
        image = render_image_preview(modules.globals.source_path, (200, 200))
        source_label.configure(image=image)
        source_label.configure(text="")
    else:
        modules.globals.source_path = None
        source_label.configure(image=None)
        source_label.configure(text="Drag & Drop\nSource Image Here")


def swap_faces_paths() -> None:
    global RECENT_DIRECTORY_SOURCE, RECENT_DIRECTORY_TARGET

    source_path = modules.globals.source_path
    target_path = modules.globals.target_path

    if not is_image(source_path) or not is_image(target_path):
        return

    modules.globals.source_path = target_path
    modules.globals.target_path = source_path

    RECENT_DIRECTORY_SOURCE = os.path.dirname(modules.globals.source_path)
    RECENT_DIRECTORY_TARGET = os.path.dirname(modules.globals.target_path)

    PREVIEW.withdraw()

    source_image = render_image_preview(modules.globals.source_path, (200, 200))
    source_label.configure(image=source_image)
    source_label.configure(text="")

    target_image = render_image_preview(modules.globals.target_path, (200, 200))
    target_label.configure(image=target_image)
    target_label.configure(text="")


def select_target_path() -> None:
    global RECENT_DIRECTORY_TARGET, img_ft, vid_ft

    PREVIEW.withdraw()
    target_path = ctk.filedialog.askopenfilename(
        title="select an target image or video",
        initialdir=RECENT_DIRECTORY_TARGET,
        filetypes=[img_ft, vid_ft],
    )
    if is_image(target_path):
        modules.globals.target_path = target_path
        RECENT_DIRECTORY_TARGET = os.path.dirname(modules.globals.target_path)
        image = render_image_preview(modules.globals.target_path, (200, 200))
        target_label.configure(image=image)
        target_label.configure(text="")
    elif is_video(target_path):
        modules.globals.target_path = target_path
        RECENT_DIRECTORY_TARGET = os.path.dirname(modules.globals.target_path)
        video_frame = render_video_preview(target_path, (200, 200))
        target_label.configure(image=video_frame)
        target_label.configure(text="")
    else:
        modules.globals.target_path = None
        target_label.configure(image=None)
        target_label.configure(text="Drag & Drop Target Image/Video Here")


def select_output_path(start: Callable[[], None]) -> None:
    global RECENT_DIRECTORY_OUTPUT, img_ft, vid_ft

    if is_image(modules.globals.target_path):
        output_path = ctk.filedialog.asksaveasfilename(
            title="save image output file",
            filetypes=[img_ft],
            defaultextension=".png",
            initialfile="output.png",
            initialdir=RECENT_DIRECTORY_OUTPUT,
        )
    elif is_video(modules.globals.target_path):
        output_path = ctk.filedialog.asksaveasfilename(
            title="save video output file",
            filetypes=[vid_ft],
            defaultextension=".mp4",
            initialfile="output.mp4",
            initialdir=RECENT_DIRECTORY_OUTPUT,
        )
    else:
        output_path = None
    if output_path:
        modules.globals.output_path = output_path
        RECENT_DIRECTORY_OUTPUT = os.path.dirname(modules.globals.output_path)
        start()


def check_and_ignore_nsfw(target, destroy: Callable = None) -> bool:
    """Check if the target is NSFW.
    TODO: Consider to make blur the target.
    """
    from numpy import ndarray
    from modules.predicter import predict_image, predict_video, predict_frame

    if type(target) is str:  # image/video file path
        check_nsfw = predict_image if has_image_extension(target) else predict_video
    elif type(target) is ndarray:  # frame object
        check_nsfw = predict_frame
    if check_nsfw and check_nsfw(target):
        if destroy:
            destroy(
                to_quit=False
            )  # Do not need to destroy the window frame if the target is NSFW
        update_status("Processing ignored!")
        return True
    else:
        return False


def fit_image_to_size(image, width: int, height: int):
    if width is None and height is None:
        return image
    h, w, _ = image.shape
    ratio_h = 0.0
    ratio_w = 0.0
    if width > height:
        ratio_h = height / h
    else:
        ratio_w = width / w
    ratio = max(ratio_w, ratio_h)
    new_size = (int(ratio * w), int(ratio * h))
    return cv2.resize(image, dsize=new_size)


def render_image_preview(image_path: str, size: Tuple[int, int]) -> ctk.CTkImage:
    image = Image.open(image_path)
    if size:
        image = ImageOps.fit(image, size, Image.LANCZOS)
    return ctk.CTkImage(image, size=image.size)


def render_video_preview(
    video_path: str, size: Tuple[int, int], frame_number: int = 0
) -> ctk.CTkImage:
    capture = cv2.VideoCapture(video_path)
    if frame_number:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    has_frame, frame = capture.read()
    if has_frame:
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if size:
            image = ImageOps.fit(image, size, Image.LANCZOS)
        return ctk.CTkImage(image, size=image.size)
    capture.release()
    cv2.destroyAllWindows()


def toggle_preview() -> None:
    if PREVIEW.state() == "normal":
        PREVIEW.withdraw()
    elif modules.globals.source_path and modules.globals.target_path:
        try:
            init_preview()
            update_preview()
        except Exception as e:
            print(f"Error initializing preview: {str(e)}")
            # Optionally, show an error message to the user
            update_status(f"Error initializing preview: {str(e)}")


def init_preview() -> None:
    global preview_slider

    if is_image(modules.globals.target_path):
        if hasattr(preview_slider, "pack_forget"):
            preview_slider.pack_forget()
    elif is_video(modules.globals.target_path):
        video_frame_total = get_video_frame_total(modules.globals.target_path)

        # Check if preview_slider exists and is a valid widget
        if hasattr(preview_slider, "winfo_exists") and preview_slider.winfo_exists():
            try:
                preview_slider.configure(to=video_frame_total)
                preview_slider.pack(fill="x")
                preview_slider.set(0)
            except tk.TclError:
                print("Error: Preview slider widget not available. Recreating it.")
                create_preview_slider()
        else:
            print("Preview slider not found. Creating a new one.")
            create_preview_slider()


def create_preview_slider():
    global preview_slider, PREVIEW

    # Ensure PREVIEW window exists
    if not hasattr(PREVIEW, "winfo_exists") or not PREVIEW.winfo_exists():
        print("Error: Preview window does not exist.")
        return

    # Create a new slider
    preview_slider = ctk.CTkSlider(
        PREVIEW,
        from_=0,
        to=get_video_frame_total(modules.globals.target_path),
        command=lambda frame_value: update_preview(int(frame_value)),
        fg_color=("gray75", "gray25"),
        progress_color=("DodgerBlue", "DodgerBlue"),
        button_color=("DodgerBlue", "DodgerBlue"),
        button_hover_color=("RoyalBlue", "RoyalBlue"),
    )
    preview_slider.pack(fill="x", padx=20, pady=10)


def navigate_frames(direction: int) -> None:
    current_frame = int(preview_slider.get())
    new_frame = max(0, min(current_frame + direction, int(preview_slider.cget("to"))))
    preview_slider.set(new_frame)
    update_preview(new_frame)


def update_preview(frame_number: int = 0) -> None:
    if modules.globals.source_path and modules.globals.target_path:
        update_status("Processing...")

        temp_frame = None
        if is_video(modules.globals.target_path):
            temp_frame = get_video_frame(modules.globals.target_path, frame_number)
        elif is_image(modules.globals.target_path):
            temp_frame = cv2.imread(modules.globals.target_path)

        if temp_frame is None:
            print("Error: temp_frame is None")
            update_status("Error: Could not read frame from video or image.")
            return

        if modules.globals.nsfw_filter and check_and_ignore_nsfw(temp_frame):
            return

        for frame_processor in get_frame_processors_modules(
            modules.globals.frame_processors
        ):
            temp_frame = frame_processor.process_frame(
                get_one_face(cv2.imread(modules.globals.source_path)), temp_frame
            )

        image = Image.fromarray(cv2.cvtColor(temp_frame, cv2.COLOR_BGR2RGB))
        image = ImageOps.contain(
            image, (PREVIEW_MAX_WIDTH, PREVIEW_MAX_HEIGHT), Image.LANCZOS
        )
        image = ctk.CTkImage(image, size=image.size)
        preview_label.configure(image=image)
        update_status("Processing succeed!")
        PREVIEW.deiconify()


def webcam_preview(root: ctk.CTk, camera_index: int):
    if not modules.globals.map_faces:
        if modules.globals.source_path is None:
            # No image selected
            return
        create_webcam_preview(camera_index)
    else:
        modules.globals.souce_target_map = []
        create_source_target_popup_for_webcam(root, modules.globals.souce_target_map)


def get_available_cameras():
    """Returns a list of available camera names and indices."""
    camera_indices = []
    camera_names = []

    for camera in enumerate_cameras():
        cap = cv2.VideoCapture(camera.index)
        if cap.isOpened():
            camera_indices.append(camera.index)
            camera_names.append(camera.name)
            cap.release()
    return (camera_indices, camera_names)


# Add this function to update the opacity value
def update_opacity(value):
    modules.globals.face_opacity = int(value)


def create_webcam_preview(camera_index: int):
    global preview_label, PREVIEW

    camera = cv2.VideoCapture(camera_index)
    if not camera.isOpened():
        update_status(f"Error: Could not open camera with index {camera_index}")
        return

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, PREVIEW_DEFAULT_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, PREVIEW_DEFAULT_HEIGHT)
    camera.set(cv2.CAP_PROP_FPS, 60)

    PREVIEW.deiconify()

    # Clear any existing widgets in the PREVIEW window
    for widget in PREVIEW.winfo_children():
        widget.destroy()

    # Create a main frame to contain all widgets
    main_frame = ctk.CTkFrame(PREVIEW)
    main_frame.pack(fill="both", expand=True)

    # Create a frame for the preview label
    preview_frame = ctk.CTkFrame(main_frame)
    preview_frame.pack(fill="both", expand=True, padx=10, pady=10)

    preview_label = ctk.CTkLabel(preview_frame, text="")
    preview_label.pack(fill="both", expand=True)

    # Initialize frame processors
    frame_processors = get_frame_processors_modules(modules.globals.frame_processors)

    # Variables for source image and FPS calculation
    source_image = None
    prev_time = time.time()
    fps_update_interval = 0.5
    frame_count = 0
    fps = 0

    # Function to update frame size when the window is resized
    def update_frame_size(event):
        nonlocal temp_frame
        if modules.globals.live_resizable:
            temp_frame = fit_image_to_size(temp_frame, event.width, event.height)

    preview_frame.bind("<Configure>", update_frame_size)

    # Main loop for capturing and processing frames
    while camera.isOpened() and PREVIEW.state() != "withdrawn":
        ret, frame = camera.read()
        if not ret:
            break

        temp_frame = frame.copy()

        # Apply mirroring if enabled
        if modules.globals.live_mirror:
            temp_frame = cv2.flip(temp_frame, 1)

        # Resize frame if enabled
        if modules.globals.live_resizable:
            temp_frame = fit_image_to_size(
                temp_frame, PREVIEW.winfo_width(), PREVIEW.winfo_height()
            )

        # Process frame based on face mapping mode
        if not modules.globals.map_faces:
            # Update source image if path has changed
            if modules.globals.source_path and (
                source_image is None
                or modules.globals.source_path != source_image["location"]
            ):
                source_image = get_one_face(cv2.imread(modules.globals.source_path))
                source_image["location"] = modules.globals.source_path

            # Apply frame processors (e.g., face swapping, enhancement)
            for frame_processor in frame_processors:
                temp_frame = frame_processor.process_frame(source_image, temp_frame)
        else:
            modules.globals.target_path = None
            for frame_processor in frame_processors:
                temp_frame = frame_processor.process_frame_v2(temp_frame)

        # Calculate and display FPS
        current_time = time.time()
        frame_count += 1
        if current_time - prev_time >= fps_update_interval:
            fps = frame_count / (current_time - prev_time)
            frame_count = 0
            prev_time = current_time

        if modules.globals.show_fps:
            cv2.putText(
                temp_frame,
                f"FPS: {fps:.1f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

        # Convert frame to RGB and display in preview label
        image = cv2.cvtColor(temp_frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(image)
        image = ImageOps.contain(
            image, (temp_frame.shape[1], temp_frame.shape[0]), Image.LANCZOS
        )
        image = ctk.CTkImage(image, size=image.size)
        preview_label.configure(image=image)
        ROOT.update()

    # Release camera and close preview window
    camera.release()
    PREVIEW.withdraw()


def create_source_target_popup_for_webcam(root: ctk.CTk, map: list) -> None:
    global POPUP_LIVE, popup_status_label_live

    POPUP_LIVE = ctk.CTkToplevel(root)
    POPUP_LIVE.title("Source x Target Mapper")
    POPUP_LIVE.geometry(f"{POPUP_LIVE_WIDTH}x{POPUP_LIVE_HEIGHT}")
    POPUP_LIVE.focus()

    def on_submit_click():
        if has_valid_map():
            POPUP_LIVE.destroy()
            simplify_maps()
            # Get the selected camera index
            selected_camera = camera_variable.get()
            camera_index = available_camera_indices[
                available_camera_strings.index(selected_camera)
            ]
            create_webcam_preview(camera_index)
        else:
            update_pop_live_status("At least 1 source with target is required!")

    def on_add_click():
        add_blank_map()
        refresh_data(map)
        update_pop_live_status("Please provide mapping!")

    popup_status_label_live = ctk.CTkLabel(POPUP_LIVE, text=None, justify="center")
    popup_status_label_live.grid(row=1, column=0, pady=15)

    add_button = ctk.CTkButton(
        POPUP_LIVE,
        text="Add",
        command=lambda: on_add_click(),
        fg_color=("gray75", "gray25"),
        hover_color=("gray85", "gray35"),
        corner_radius=10,
    )
    add_button.place(relx=0.2, rely=0.92, relwidth=0.2, relheight=0.05)

    close_button = ctk.CTkButton(
        POPUP_LIVE,
        text="Submit",
        command=lambda: on_submit_click(),
        fg_color=("DodgerBlue", "DodgerBlue"),
        hover_color=("RoyalBlue", "RoyalBlue"),
        corner_radius=10,
    )
    close_button.place(relx=0.6, rely=0.92, relwidth=0.2, relheight=0.05)

    # Add camera selection
    camera_frame = ctk.CTkFrame(POPUP_LIVE)
    camera_frame.grid(row=2, column=0, pady=15)

    camera_label = ctk.CTkLabel(camera_frame, text="Select Camera:")
    camera_label.pack(side="left", padx=(0, 10))

    available_cameras = get_available_cameras()
    available_camera_indices, available_camera_strings = available_cameras
    camera_variable = ctk.StringVar(
        value=(
            available_camera_strings[0]
            if available_camera_strings
            else "No cameras found"
        )
    )
    camera_optionmenu = ctk.CTkOptionMenu(
        camera_frame, variable=camera_variable, values=available_camera_strings
    )
    camera_optionmenu.pack(side="left")

    refresh_data(map)  # Initial data refresh


def refresh_data(map: list):
    global POPUP_LIVE

    # Destroy existing widgets in the scrollable frame
    for widget in POPUP_LIVE.winfo_children():
        if isinstance(widget, ctk.CTkScrollableFrame):
            widget.destroy()

    scrollable_frame = ctk.CTkScrollableFrame(
        POPUP_LIVE, width=POPUP_LIVE_SCROLL_WIDTH, height=POPUP_LIVE_SCROLL_HEIGHT
    )
    scrollable_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

    def on_sbutton_click(map, button_num):
        map = update_webcam_source(scrollable_frame, map, button_num)

    def on_tbutton_click(map, button_num):
        map = update_webcam_target(scrollable_frame, map, button_num)

    for item in map:
        id = item["id"]

        row_frame = ctk.CTkFrame(scrollable_frame)
        row_frame.pack(fill="x", pady=5)

        source_button = SourceMapperButton(  # Use SourceMapperButton here
            row_frame,
            map,
            id,
            text="Select source image",
            command=lambda id=id: on_sbutton_click(map, id),
            width=DEFAULT_BUTTON_WIDTH,
            height=DEFAULT_BUTTON_HEIGHT,
            fg_color=("gray75", "gray25"),
            hover_color=("gray85", "gray35"),
            corner_radius=10,
        )
        source_button.pack(side="left", padx=(0, 10))

        source_image_label = ctk.CTkLabel(  # Create a label for source image
            row_frame,
            text=f"S-{id}",
            width=MAPPER_PREVIEW_MAX_WIDTH,
            height=MAPPER_PREVIEW_MAX_HEIGHT,
        )
        source_image_label.pack(side="left", padx=(0, 10))

        if "source" in item:
            image = Image.fromarray(
                cv2.cvtColor(item["source"]["cv2"], cv2.COLOR_BGR2RGB)
            )
            image = image.resize(
                (MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS
            )
            tk_image = ctk.CTkImage(image, size=image.size)
            source_image_label.configure(image=tk_image)

        x_label = ctk.CTkLabel(
            row_frame,
            text=f"X",
            width=30,
        )
        x_label.pack(side="left", padx=(0, 10))

        target_button = DragDropButton(  # Use DragDropButton for target
            row_frame,
            text="Select target image",
            command=lambda id=id: on_tbutton_click(map, id),
            width=DEFAULT_BUTTON_WIDTH,
            height=DEFAULT_BUTTON_HEIGHT,
            fg_color=("gray75", "gray25"),
            hover_color=("gray85", "gray35"),
            corner_radius=10,
        )

        target_button.handle_drop = lambda file_path, id=id: update_webcam_target(
            scrollable_frame, map, id, file_path
        )  # Add handle_drop for drag and drop
        target_button.pack(side="left", padx=(0, 10))

        target_image_label = ctk.CTkLabel(  # Create a label for target image
            row_frame,
            text=f"T-{id}",
            width=MAPPER_PREVIEW_MAX_WIDTH,
            height=MAPPER_PREVIEW_MAX_HEIGHT,
        )
        target_image_label.pack(side="left")

        if "target" in item:
            image = Image.fromarray(
                cv2.cvtColor(item["target"]["cv2"], cv2.COLOR_BGR2RGB)
            )
            image = image.resize(
                (MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS
            )
            tk_image = ctk.CTkImage(image, size=image.size)
            target_image_label.configure(image=tk_image)


def update_webcam_source(
    scrollable_frame: ctk.CTkScrollableFrame, map: list, button_num: int
) -> list:
    global source_label_dict_live

    source_path = ctk.filedialog.askopenfilename(
        title="select an source image",
        initialdir=RECENT_DIRECTORY_SOURCE,
        filetypes=[img_ft],
    )

    if "source" in map[button_num]:
        map[button_num].pop("source")
        if button_num in source_label_dict_live:
            source_label_dict_live[button_num].destroy()
            del source_label_dict_live[button_num]

    if source_path == "":
        return map
    else:
        cv2_img = cv2.imread(source_path)
        face = get_one_face(cv2_img)

        if face:
            x_min, y_min, x_max, y_max = face["bbox"]

            map[button_num]["source"] = {
                "cv2": cv2_img[int(y_min) : int(y_max), int(x_min) : int(x_max)],
                "face": face,
            }

            image = Image.fromarray(
                cv2.cvtColor(map[button_num]["source"]["cv2"], cv2.COLOR_BGR2RGB)
            )
            image = image.resize(
                (MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS
            )
            tk_image = ctk.CTkImage(image, size=image.size)

            # Find the source image label in the row frame
            row_frame = scrollable_frame.winfo_children()[button_num]
            source_image_label = row_frame.winfo_children()[1]

            source_image_label.configure(image=tk_image)
            source_label_dict_live[button_num] = source_image_label
        else:
            update_pop_live_status("Face could not be detected in last upload!")
        return map


def update_webcam_target(
    scrollable_frame: ctk.CTkScrollableFrame,
    map: list,
    button_num: int,
    target_path: str = None,
) -> list:
    global target_label_dict_live

    if target_path is None:
        target_path = ctk.filedialog.askopenfilename(
            title="select an target image",
            initialdir=RECENT_DIRECTORY_SOURCE,
            filetypes=[img_ft],
        )

    if "target" in map[button_num]:
        map[button_num].pop("target")
        if button_num in target_label_dict_live:
            target_label_dict_live[button_num].destroy()
            del target_label_dict_live[button_num]

    if target_path == "":
        return map
    else:
        cv2_img = cv2.imread(target_path)
        face = get_one_face(cv2_img)

        if face:
            x_min, y_min, x_max, y_max = face["bbox"]

            map[button_num]["target"] = {
                "cv2": cv2_img[int(y_min) : int(y_max), int(x_min) : int(x_max)],
                "face": face,
            }

            image = Image.fromarray(
                cv2.cvtColor(map[button_num]["target"]["cv2"], cv2.COLOR_BGR2RGB)
            )
            image = image.resize(
                (MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS
            )
            tk_image = ctk.CTkImage(image, size=image.size)

            # Find the target image label in the row frame
            row_frame = scrollable_frame.winfo_children()[button_num]
            target_image_label = row_frame.winfo_children()[4]

            target_image_label.configure(image=tk_image)
            target_label_dict_live[button_num] = target_image_label
        else:
            update_pop_live_status("Face could not be detected in last upload!")
        return map
