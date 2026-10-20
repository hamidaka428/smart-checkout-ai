import time
import cv2
import os

from hardware.sensor import UltrasonicScanner

try:
    from picamera2 import Picamera2
except ImportError:
    print("[Error] Picamera2 is missing.")
    print("Install it with:")
    print("sudo apt install python3-picamera2")
    exit(1)


# ============================================================
# SETTINGS
# ============================================================

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

ROI_WIDTH = 450
ROI_HEIGHT = 350

MIN_DISTANCE_CM = 5.0
MAX_DISTANCE_CM = 35.0

# ------------------------------------------------------------
# DATASET
# ------------------------------------------------------------

# Краен брой изображения за един продукт
TARGET_IMAGES = 100

# Размер на една серия
SERIES_SIZE = 20

# ------------------------------------------------------------
# CAPTURE
# ------------------------------------------------------------

# Интервал между проверките за нов кадър
CAPTURE_INTERVAL = 0.4

# Изчакване след засичане на продукта
# преди да започнем да записваме
PRE_CAPTURE_DELAY = 1.5

# Изчакване продуктът да бъде махнат
REMOVE_DELAY = 1.5

# ------------------------------------------------------------
# IMAGE DIFFERENCE
# ------------------------------------------------------------

# Минимална разлика между два последователни
# записани кадъра.
#
# По-ниска стойност:
# -> приемаме повече кадри
#
# По-висока стойност:
# -> приемаме само по-различни кадри
MIN_IMAGE_DIFFERENCE = 4.0


# ============================================================
# COLLECTION SERIES
# ============================================================

SERIES_INSTRUCTIONS = [
    {
        "name": "FRONT / NORMAL",
        "description": [
            "Place the product normally.",
            "Show the main/front side.",
            "Keep your hand outside the green box.",
            "Make small position changes."
        ]
    },
    {
        "name": "BACK",
        "description": [
            "Turn the product around.",
            "Show the back side.",
            "Keep your hand outside the green box.",
            "Change the position slightly."
        ]
    },
    {
        "name": "DIFFERENT ANGLES",
        "description": [
            "Rotate the product gradually.",
            "Use different viewing angles.",
            "Tilt the product slightly.",
            "Remove your hand before capture."
        ]
    },
    {
        "name": "DISTANCE / ORIENTATION",
        "description": [
            "Change the distance inside the ROI.",
            "Use horizontal and vertical positions.",
            "Move the product slightly.",
            "Keep the whole product visible."
        ]
    },
    {
        "name": "REAL WORLD VARIATIONS",
        "description": [
            "Use natural random positions.",
            "Try different orientations.",
            "Use realistic placement angles.",
            "Avoid covering the product with your hand."
        ]
    }
]


# ============================================================
# ROI
# ============================================================

def get_roi_coordinates(frame):
    """
    Изчислява координатите на централния ROI.
    """

    height, width, _ = frame.shape

    top_left = (
        int(width / 2 - ROI_WIDTH / 2),
        int(height / 2 - ROI_HEIGHT / 2)
    )

    bottom_right = (
        int(width / 2 + ROI_WIDTH / 2),
        int(height / 2 + ROI_HEIGHT / 2)
    )

    return top_left, bottom_right


# ============================================================
# DATASET FUNCTIONS
# ============================================================

def get_existing_images(save_dir):
    """
    Връща всички изображения в dataset папката.
    """

    if not os.path.exists(save_dir):
        return []

    files = []

    for filename in os.listdir(save_dir):

        full_path = os.path.join(
            save_dir,
            filename
        )

        if not os.path.isfile(full_path):
            continue

        extension = os.path.splitext(
            filename
        )[1].lower()

        if extension in [
            ".jpg",
            ".jpeg",
            ".png"
        ]:
            files.append(filename)

    return files


def get_next_image_number(product_name, save_dir):
    """
    Намира следващия свободен номер.

    Например:

    RPI_PHONE_0.jpg
    RPI_PHONE_1.jpg
    RPI_PHONE_2.jpg

    -> връща 3
    """

    existing_files = get_existing_images(
        save_dir
    )

    highest_number = -1

    prefix = product_name + "_"

    for filename in existing_files:

        name = os.path.splitext(
            filename
        )[0]

        if not name.startswith(prefix):
            continue

        number_text = name[len(prefix):]

        if number_text.isdigit():

            number = int(number_text)

            if number > highest_number:
                highest_number = number

    return highest_number + 1


# ============================================================
# SERIES FUNCTIONS
# ============================================================

def get_series_number(images_taken):
    """
    Определя текущата серия според броя изображения.

    0-19   -> серия 1
    20-39  -> серия 2
    40-59  -> серия 3
    60-79  -> серия 4
    80-99  -> серия 5
    """

    series_number = (
        images_taken // SERIES_SIZE
    ) + 1

    if series_number > len(
        SERIES_INSTRUCTIONS
    ):
        series_number = len(
            SERIES_INSTRUCTIONS
        )

    return series_number


def show_series_instructions(series_number):
    """
    Показва инструкциите за текущата серия.
    """

    series = SERIES_INSTRUCTIONS[
        series_number - 1
    ]

    print("\n")
    print("=" * 60)

    print(
        f"SERIES {series_number}/"
        f"{len(SERIES_INSTRUCTIONS)}"
    )

    print("=" * 60)

    print(
        series["name"]
    )

    print("-" * 60)

    for instruction in series["description"]:

        print(
            f"- {instruction}"
        )

    print("=" * 60)

    input(
        "\nPress ENTER when you are ready..."
    )


# ============================================================
# IMAGE DIFFERENCE
# ============================================================

def calculate_image_difference(
    image1,
    image2
):
    """
    Изчислява средната абсолютна разлика
    между два изображения.
    """

    if image1 is None or image2 is None:
        return 255.0

    if image1.size == 0 or image2.size == 0:
        return 255.0

    small1 = cv2.resize(
        image1,
        (160, 120)
    )

    small2 = cv2.resize(
        image2,
        (160, 120)
    )

    gray1 = cv2.cvtColor(
        small1,
        cv2.COLOR_BGR2GRAY
    )

    gray2 = cv2.cvtColor(
        small2,
        cv2.COLOR_BGR2GRAY
    )

    gray1 = cv2.GaussianBlur(
        gray1,
        (5, 5),
        0
    )

    gray2 = cv2.GaussianBlur(
        gray2,
        (5, 5),
        0
    )

    difference = cv2.absdiff(
        gray1,
        gray2
    )

    return float(
        difference.mean()
    )


def is_different_enough(
    new_image,
    previous_image
):
    """
    Проверява дали новият кадър
    е достатъчно различен.
    """

    if previous_image is None:

        return True, 255.0

    difference = calculate_image_difference(
        new_image,
        previous_image
    )

    return (
        difference >= MIN_IMAGE_DIFFERENCE,
        difference
    )


# ============================================================
# SENSOR
# ============================================================

def is_product_detected(scanner):
    """
    Проверява дали продуктът е между
    минималната и максималната дистанция.
    """

    distance = scanner.get_raw_distance_cm()

    detected = (
        MIN_DISTANCE_CM
        < distance
        < MAX_DISTANCE_CM
    )

    return detected, distance


# ============================================================
# UI
# ============================================================

def draw_roi(
    frame,
    top_left,
    bottom_right,
    color,
    thickness=2
):
    """
    Рисува ROI правоъгълника.
    """

    cv2.rectangle(
        frame,
        top_left,
        bottom_right,
        color,
        thickness
    )


def put_text(
    frame,
    text,
    position,
    color=(255, 255, 255),
    size=0.65
):
    """
    Показва текст върху камерата.
    """

    cv2.putText(
        frame,
        text,
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        size,
        color,
        2
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)

    print(
        "      SMART CHECKOUT AI DATASET COLLECTOR v4"
    )

    print("=" * 60)

    # --------------------------------------------------------
    # PRODUCT NAME
    # --------------------------------------------------------

    product_name = input(
        "\nEnter product name "
        "(must match database / AI label): "
    ).strip().upper()

    if not product_name:

        print(
            "[Error] Product name cannot be empty."
        )

        return

    # --------------------------------------------------------
    # DATASET DIRECTORY
    # --------------------------------------------------------

    save_dir = os.path.join(
        "dataset",
        product_name
    )

    os.makedirs(
        save_dir,
        exist_ok=True
    )

    existing_files = get_existing_images(
        save_dir
    )

    existing_count = len(
        existing_files
    )

    next_image_number = get_next_image_number(
        product_name,
        save_dir
    )

    # --------------------------------------------------------
    # DATASET INFORMATION
    # --------------------------------------------------------

    print("\n[Dataset]")

    print(
        f"Product:       {product_name}"
    )

    print(
        f"Folder:        {save_dir}"
    )

    print(
        f"Existing:      {existing_count}"
    )

    print(
        f"Target total:  {TARGET_IMAGES}"
    )

    print(
        f"Remaining:     "
        f"{max(0, TARGET_IMAGES - existing_count)}"
    )

    # --------------------------------------------------------
    # ALREADY COMPLETE
    # --------------------------------------------------------

    if existing_count >= TARGET_IMAGES:

        print(
            "\n[INFO] Dataset already complete."
        )

        print(
            f"{existing_count}/{TARGET_IMAGES} images."
        )

        return

    # --------------------------------------------------------
    # CURRENT SERIES
    # --------------------------------------------------------

    current_series = get_series_number(
        existing_count
    )

    show_series_instructions(
        current_series
    )

    # --------------------------------------------------------
    # HARDWARE
    # --------------------------------------------------------

    print(
        "\n[Hardware] Initializing ultrasonic sensor..."
    )

    scanner = UltrasonicScanner(
        trigger_pin=23,
        echo_pin=24,
        threshold_cm=MAX_DISTANCE_CM
    )

    print(
        "[Camera] Initializing Picamera2..."
    )

    picam2 = Picamera2()

    config = picam2.create_preview_configuration(
        main={
            "size": (
                CAMERA_WIDTH,
                CAMERA_HEIGHT
            )
        }
    )

    picam2.configure(
        config
    )

    picam2.start()

    time.sleep(2)

    # --------------------------------------------------------
    # STATE
    # --------------------------------------------------------

    images_taken = existing_count

    is_capturing = False

    waiting_for_removal = False

    waiting_for_next_series = False

    capture_start_time = 0

    last_capture_time = 0

    removal_start_time = 0

    previous_saved_image = None

    accepted_frames = 0

    rejected_similar_frames = 0

    # Запомняме серията, в която се намираме
    current_series = get_series_number(
        images_taken
    )

    # --------------------------------------------------------
    # READY
    # --------------------------------------------------------

    print("\n" + "=" * 60)

    print(
        "SYSTEM READY"
    )

    print("=" * 60)

    print(
        f"Product: {product_name}"
    )

    print(
        f"Series: "
        f"{current_series}/"
        f"{len(SERIES_INSTRUCTIONS)}"
    )

    print(
        f"Dataset: "
        f"{images_taken}/"
        f"{TARGET_IMAGES}"
    )

    print(
        "\nPlace the product inside the green box."
    )

    print(
        "The ultrasonic sensor will start automatically."
    )

    print("\nControls:")

    print(
        "  Q     - Quit"
    )

    print(
        "  SPACE - Start manually"
    )

    print("=" * 60)

    # ========================================================
    # MAIN LOOP
    # ========================================================

    try:

        while True:

            # ------------------------------------------------
            # CAMERA FRAME
            # ------------------------------------------------

            frame = picam2.capture_array()

            frame = cv2.cvtColor(
                frame,
                cv2.COLOR_RGB2BGR
            )

            top_left, bottom_right = (
                get_roi_coordinates(
                    frame
                )
            )

            current_time = time.time()

            # ------------------------------------------------
            # DATASET COMPLETE
            # ------------------------------------------------

            if (
                images_taken
                >= TARGET_IMAGES
            ):

                draw_roi(
                    frame,
                    top_left,
                    bottom_right,
                    (0, 255, 0),
                    3
                )

                put_text(
                    frame,
                    "DATASET COMPLETE!",
                    (20, 40),
                    (0, 255, 0),
                    0.8
                )

                put_text(
                    frame,
                    f"{images_taken}/"
                    f"{TARGET_IMAGES}",
                    (20, 75),
                    (0, 255, 0),
                    0.7
                )

                put_text(
                    frame,
                    "Press Q to exit",
                    (20, 110),
                    (255, 255, 255),
                    0.6
                )

                cv2.imshow(
                    "Smart Checkout Dataset Collector",
                    frame
                )

                key = (
                    cv2.waitKey(1)
                    & 0xFF
                )

                if key == ord("q"):
                    break

                continue

            # ------------------------------------------------
            # NEXT SERIES
            # ------------------------------------------------

            if waiting_for_next_series:

                draw_roi(
                    frame,
                    top_left,
                    bottom_right,
                    (255, 255, 0),
                    3
                )

                put_text(
                    frame,
                    "CHANGE PRODUCT POSITION",
                    (20, 40),
                    (255, 255, 0),
                    0.7
                )

                put_text(
                    frame,
                    f"Next series: "
                    f"{current_series}/"
                    f"{len(SERIES_INSTRUCTIONS)}",
                    (20, 75),
                    (255, 255, 255),
                    0.6
                )

                put_text(
                    frame,
                    "Press SPACE when ready",
                    (20, 110),
                    (255, 255, 255),
                    0.6
                )

                cv2.imshow(
                    "Smart Checkout Dataset Collector",
                    frame
                )

                key = (
                    cv2.waitKey(1)
                    & 0xFF
                )

                if key == ord("q"):

                    break

                if key == 32:

                    waiting_for_next_series = False

                    previous_saved_image = None

                    show_series_instructions(
                        current_series
                    )

                continue

            # ------------------------------------------------
            # WAITING FOR PRODUCT REMOVAL
            # ------------------------------------------------

            if waiting_for_removal:

                draw_roi(
                    frame,
                    top_left,
                    bottom_right,
                    (0, 255, 255),
                    3
                )

                put_text(
                    frame,
                    "REMOVE PRODUCT",
                    (
                        top_left[0],
                        top_left[1] - 15
                    ),
                    (0, 255, 255),
                    0.7
                )

                put_text(
                    frame,
                    f"Images: "
                    f"{images_taken}/"
                    f"{TARGET_IMAGES}",
                    (20, 40),
                    (255, 255, 255),
                    0.65
                )

                detected, distance = (
                    is_product_detected(
                        scanner
                    )
                )

                if not detected:

                    if removal_start_time == 0:

                        removal_start_time = (
                            current_time
                        )

                    if (
                        current_time
                        - removal_start_time
                        >= REMOVE_DELAY
                    ):

                        waiting_for_removal = False

                        removal_start_time = 0

                        # ------------------------------------------------
                        # CHECK FOR NEXT SERIES
                        # ------------------------------------------------

                        new_series = get_series_number(
                            images_taken
                        )

                        if (
                            new_series
                            != current_series
                            and images_taken
                            < TARGET_IMAGES
                        ):

                            current_series = (
                                new_series
                            )

                            waiting_for_next_series = True

                            print(
                                "\n"
                                + "=" * 60
                            )

                            print(
                                f"SERIES "
                                f"{current_series}/"
                                f"{len(SERIES_INSTRUCTIONS)}"
                            )

                            print(
                                "Previous series complete."
                            )

                            print(
                                "Change the product position."
                            )

                            print(
                                "=" * 60
                            )

                        else:

                            print(
                                "\n[Sensor] "
                                "Product removed."
                            )

                            print(
                                "[Sensor] "
                                "Ready for next capture."
                            )

                else:

                    removal_start_time = 0

                cv2.imshow(
                    "Smart Checkout Dataset Collector",
                    frame
                )

                key = (
                    cv2.waitKey(1)
                    & 0xFF
                )

                if key == ord("q"):
                    break

                continue

            # ------------------------------------------------
            # CAPTURE MODE
            # ------------------------------------------------

            if is_capturing:

                draw_roi(
                    frame,
                    top_left,
                    bottom_right,
                    (0, 0, 255),
                    3
                )

                put_text(
                    frame,
                    "CAPTURING",
                    (
                        top_left[0],
                        top_left[1] - 45
                    ),
                    (0, 0, 255),
                    0.8
                )

                put_text(
                    frame,
                    f"Series "
                    f"{current_series}/"
                    f"{len(SERIES_INSTRUCTIONS)}",
                    (
                        top_left[0],
                        top_left[1] - 15
                    ),
                    (0, 0, 255),
                    0.65
                )

                put_text(
                    frame,
                    f"{images_taken}/"
                    f"{TARGET_IMAGES}",
                    (20, 40),
                    (255, 255, 255),
                    0.65
                )

                # --------------------------------------------
                # PRE-CAPTURE DELAY
                # --------------------------------------------

                if (
                    current_time
                    - capture_start_time
                    >= PRE_CAPTURE_DELAY
                ):

                    # ----------------------------------------
                    # CAPTURE INTERVAL
                    # ----------------------------------------

                    if (
                        current_time
                        - last_capture_time
                        >= CAPTURE_INTERVAL
                    ):

                        roi_frame = frame[
                            top_left[1]:
                            bottom_right[1],

                            top_left[0]:
                            bottom_right[0]
                        ]

                        if (
                            roi_frame is not None
                            and roi_frame.size > 0
                        ):

                            # --------------------------------
                            # DIFFERENCE CHECK
                            # --------------------------------

                            different, difference = (
                                is_different_enough(
                                    roi_frame,
                                    previous_saved_image
                                )
                            )

                            if different:

                                filename = (
                                    f"{product_name}_"
                                    f"{next_image_number}.jpg"
                                )

                                img_path = os.path.join(
                                    save_dir,
                                    filename
                                )

                                success = cv2.imwrite(
                                    img_path,
                                    roi_frame
                                )

                                if success:

                                    images_taken += 1

                                    next_image_number += 1

                                    accepted_frames += 1

                                    previous_saved_image = (
                                        roi_frame.copy()
                                    )

                                    print(
                                        f"[ACCEPT] "
                                        f"{images_taken}/"
                                        f"{TARGET_IMAGES} "
                                        f"| Series "
                                        f"{current_series} "
                                        f"| diff="
                                        f"{difference:.2f} "
                                        f"| {filename}"
                                    )

                                else:

                                    print(
                                        "[ERROR] "
                                        "Could not save image."
                                    )

                            else:

                                rejected_similar_frames += 1

                                print(
                                    f"[SKIP] "
                                    f"Too similar "
                                    f"| Series "
                                    f"{current_series} "
                                    f"| diff="
                                    f"{difference:.2f}"
                                )

                        last_capture_time = (
                            current_time
                        )

                        # ------------------------------------
                        # SERIES COMPLETE
                        # ------------------------------------

                        images_in_current_series = (
                            images_taken
                            % SERIES_SIZE
                        )

                        if (
                            images_in_current_series
                            == 0
                            and images_taken > 0
                        ):

                            print(
                                "\n"
                                + "=" * 60
                            )

                            print(
                                f"SERIES "
                                f"{current_series} COMPLETE"
                            )

                            print(
                                "=" * 60
                            )

                            is_capturing = False

                            waiting_for_removal = True

                            removal_start_time = 0

                            continue

                        # ------------------------------------
                        # FINAL DATASET COMPLETE
                        # ------------------------------------

                        if (
                            images_taken
                            >= TARGET_IMAGES
                        ):

                            print(
                                "\n"
                                + "=" * 60
                            )

                            print(
                                "DATASET COLLECTION COMPLETE!"
                            )

                            print(
                                "=" * 60
                            )

                            is_capturing = False

                            waiting_for_removal = True

                            removal_start_time = 0

            # ------------------------------------------------
            # WAITING MODE
            # ------------------------------------------------

            else:

                draw_roi(
                    frame,
                    top_left,
                    bottom_right,
                    (0, 255, 0),
                    3
                )

                put_text(
                    frame,
                    "WAITING FOR PRODUCT",
                    (
                        top_left[0],
                        top_left[1] - 15
                    ),
                    (0, 255, 0),
                    0.7
                )

                put_text(
                    frame,
                    f"Series "
                    f"{current_series}/"
                    f"{len(SERIES_INSTRUCTIONS)}",
                    (20, 40),
                    (255, 255, 255),
                    0.65
                )

                put_text(
                    frame,
                    f"Images: "
                    f"{images_taken}/"
                    f"{TARGET_IMAGES}",
                    (20, 75),
                    (255, 255, 255),
                    0.65
                )

                detected, distance = (
                    is_product_detected(
                        scanner
                    )
                )

                put_text(
                    frame,
                    f"Distance: "
                    f"{distance:.1f} cm",
                    (20, 110),
                    (255, 255, 255),
                    0.6
                )

                if detected:

                    print(
                        "\n[Sensor] "
                        "Product detected!"
                    )

                    print(
                        f"[Sensor] "
                        f"Distance: "
                        f"{distance:.1f} cm"
                    )

                    print(
                        "[Collector] "
                        "Preparing capture..."
                    )

                    is_capturing = True

                    capture_start_time = (
                        current_time
                    )

                    last_capture_time = 0

                    previous_saved_image = None

            # ------------------------------------------------
            # DISPLAY
            # ------------------------------------------------

            cv2.imshow(
                "Smart Checkout Dataset Collector",
                frame
            )

            key = (
                cv2.waitKey(1)
                & 0xFF
            )

            # ------------------------------------------------
            # QUIT
            # ------------------------------------------------

            if key == ord("q"):

                print(
                    "\n[User] "
                    "Collector stopped."
                )

                break

            # ------------------------------------------------
            # MANUAL START
            # ------------------------------------------------

            elif key == 32:

                if not is_capturing:

                    print(
                        "\n[Manual] "
                        "Starting capture..."
                    )

                    is_capturing = True

                    capture_start_time = (
                        current_time
                    )

                    last_capture_time = 0

                    previous_saved_image = None

    except KeyboardInterrupt:

        print(
            "\n[System] Interrupted."
        )

    finally:

        print(
            "\n[System] Cleaning up..."
        )

        picam2.stop()

        cv2.destroyAllWindows()

        print(
            "\n"
            + "=" * 60
        )

        print(
            "COLLECTION SUMMARY"
        )

        print(
            "=" * 60
        )

        print(
            f"Product:             "
            f"{product_name}"
        )

        print(
            f"Images saved:        "
            f"{images_taken}"
        )

        print(
            f"Target:              "
            f"{TARGET_IMAGES}"
        )

        print(
            f"Accepted frames:     "
            f"{accepted_frames}"
        )

        print(
            f"Rejected similar:    "
            f"{rejected_similar_frames}"
        )

        print(
            f"Difference threshold:"
            f" {MIN_IMAGE_DIFFERENCE}"
        )

        print(
            "=" * 60
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
