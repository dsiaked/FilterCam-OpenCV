"""
Video Recorder using OpenCV
----------------------------
Modes  : PREVIEW (default) / RECORD
Hotkeys:
  SPACE  - Toggle PREVIEW <-> RECORD mode
  ESC    - Exit program
  F      - Toggle horizontal flip
  B / b  - Increase / Decrease brightness  (+10 / -10, range -100 ~ 100)
  C / c  - Increase / Decrease contrast    (+0.1 / -0.1, range 0.1 ~ 3.0)
"""

import cv2
import datetime
import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Video Recorder using OpenCV"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="0",
        help="Camera index (0, 1, …) or RTSP URL for an IP camera "
             "(e.g. rtsp://user:pass@192.168.x.x/stream)",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=30.0,
        help="Recording frame rate (default: 30)",
    )
    parser.add_argument(
        "--fourcc",
        type=str,
        default="XVID",
        help="FourCC codec code (default: XVID). "
             "Other options: MP4V, MJPG, H264",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=640,
        help="Capture frame width  (default: 640)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=480,
        help="Capture frame height (default: 480)",
    )
    return parser


def open_capture(source_str: str, width: int, height: int) -> cv2.VideoCapture:
    """Open VideoCapture from an integer device index or an IP-camera URL."""
    source = int(source_str) if source_str.isdigit() else source_str
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open source: {source_str}")
        sys.exit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    return cap


def apply_filters(
    frame,
    flip_h: bool,
    brightness: int,
    contrast: float,
):
    """Apply flip / brightness / contrast filters to a frame."""
    if flip_h:
        frame = cv2.flip(frame, 1)
    # cv2.convertScaleAbs: dst = saturate(contrast * src + brightness)
    frame = cv2.convertScaleAbs(frame, alpha=contrast, beta=brightness)
    return frame


def draw_overlay(display, is_recording: bool, brightness: int, contrast: float, flip_h: bool):
    """Draw mode indicator and filter status on the display frame."""
    h = display.shape[0]

    if is_recording:
        # Red filled circle — recording indicator
        cv2.circle(display, (30, 30), 15, (0, 0, 255), -1)
        cv2.putText(
            display, "REC",
            (52, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2,
        )
    else:
        cv2.putText(
            display, "PREVIEW",
            (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 220, 0), 2,
        )

    # Filter status (bottom-left corner)
    status_lines = [
        f"Flip     : {'ON' if flip_h else 'OFF'}",
        f"Contrast : {contrast:.1f}",
        f"Brightness: {brightness:+d}",
    ]
    for i, text in enumerate(reversed(status_lines)):
        y = h - 10 - i * 22
        cv2.putText(
            display, text,
            (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1,
        )

    # Key hint (top-right area)
    hint = "SPACE:Rec/Stop  F:Flip  B/b:Bright  C/c:Contrast  ESC:Exit"
    cv2.putText(
        display, hint,
        (10, h - 10 - len(status_lines) * 22 - 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1,
    )


def main():
    parser = build_parser()
    args = parser.parse_args()

    cap = open_capture(args.source, args.width, args.height)
    fourcc = cv2.VideoWriter_fourcc(*args.fourcc.upper().ljust(4)[:4])

    # ── State ───────────────────────────────────────────────────────────────
    is_recording = False
    writer: cv2.VideoWriter | None = None

    # Filter state
    flip_h = False
    brightness = 0      # integer -100 ~ 100
    contrast = 1.0      # float   0.1  ~ 3.0

    print("=" * 55)
    print("  Video Recorder  (OpenCV)")
    print("=" * 55)
    print("  SPACE       Toggle RECORD / PREVIEW")
    print("  ESC         Exit")
    print("  F           Flip horizontal")
    print("  B / b       Brightness  +10 / -10")
    print("  C / c       Contrast    +0.1 / -0.1")
    print("=" * 55)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to grab frame — exiting.")
            break

        # Apply filters
        frame = apply_filters(frame, flip_h, brightness, contrast)

        # Write to file if recording
        if is_recording and writer is not None:
            writer.write(frame)

        # Build display copy with overlay
        display = frame.copy()
        draw_overlay(display, is_recording, brightness, contrast, flip_h)

        cv2.imshow("Video Recorder", display)

        key = cv2.waitKey(1) & 0xFF

        # ── Key handling ─────────────────────────────────────────────────
        if key == 27:  # ESC
            print("[INFO] Exiting …")
            break

        elif key == 32:  # SPACE — toggle record
            if is_recording:
                is_recording = False
                if writer is not None:
                    writer.release()
                    writer = None
                print("[INFO] Recording stopped.")
            else:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"recording_{timestamp}.avi"
                h_frame, w_frame = frame.shape[:2]
                writer = cv2.VideoWriter(
                    filename, fourcc, args.fps, (w_frame, h_frame)
                )
                is_recording = True
                print(f"[INFO] Recording started → {filename}")

        elif key in (ord("f"), ord("F")):
            flip_h = not flip_h
            print(f"[INFO] Flip: {'ON' if flip_h else 'OFF'}")

        elif key == ord("B"):
            brightness = min(100, brightness + 10)
            print(f"[INFO] Brightness: {brightness:+d}")

        elif key == ord("b"):
            brightness = max(-100, brightness - 10)
            print(f"[INFO] Brightness: {brightness:+d}")

        elif key == ord("C"):
            contrast = min(3.0, round(contrast + 0.1, 1))
            print(f"[INFO] Contrast: {contrast:.1f}")

        elif key == ord("c"):
            contrast = max(0.1, round(contrast - 0.1, 1))
            print(f"[INFO] Contrast: {contrast:.1f}")

    # ── Cleanup ──────────────────────────────────────────────────────────────
    if is_recording and writer is not None:
        writer.release()
    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] Done.")


if __name__ == "__main__":
    main()
