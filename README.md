# Smart Checkout AI

An autonomous self-checkout prototype built with Raspberry Pi 5, computer vision, and Edge AI.

The system detects products using a camera, classifies them with a TensorFlow Lite model, retrieves product information from a local PHP API, and displays the name and price on an LCD. It also provides Bulgarian voice feedback, adds recognised products to the cart, and generates a receipt when the customer finishes the checkout.

## Demo

[**▶ Watch the Smart Checkout AI demo**](https://youtu.be/6w_1xqbzkQ8)

## Features

- **Computer vision:** Detects objects by comparing camera frames against an empty-scene background.
- **Edge AI:** Classifies 15 product categories using a TensorFlow Lite model.
- **Live feedback:** Displays product information on an LCD and provides buzzer and Bulgarian voice feedback.
- **Checkout:** Adds recognised products to the cart and completes the session using a physical button.
- **Receipt generation:** Produces a receipt with subtotal, VAT, and total.
- **Product backend:** Uses a PHP API and MariaDB for product lookup and order storage.
- **Dataset collection:** Includes scripts for collecting labelled images for model training.

## Hardware

| Component | Interface |
|---|---|
| Raspberry Pi 5 | Main computing platform |
| Raspberry Pi Camera Module 3 | CSI |
| HC-SR04 ultrasonic sensor | GPIO 23 / GPIO 24 |
| 16×2 LCD with PCF8574 | I²C, address `0x27` |
| Buzzer | GPIO 26 |
| Finish button | GPIO 25 |

Product detection is camera-based. The ultrasonic sensor remains part of the hardware setup but is not the primary product detection mechanism.

## AI Model

The TensorFlow Lite model accepts 224 × 224 input images and recognises 15 trained product classes. Predictions below the configured 85% confidence threshold are rejected.

The training dataset contains 1,500 images, with 100 images per class. A small sample is included in the repository; the full dataset is excluded.

## Technologies

Python · OpenCV · TensorFlow Lite · Raspberry Pi OS · Picamera2 · GPIO Zero · PHP · MariaDB · I²C

## Project Structure

```text
smart_checkout/
├── main.py
├── ai/
│   └── model/
├── hardware/
├── utils/
├── backend/
├── dataset_sample/
├── docs/
└── requirements.txt
```

## Installation

On Raspberry Pi OS, enable the camera and I²C interfaces first.

```bash
sudo apt update
sudo apt install python3-picamera2 python3-opencv
```

Clone the repository and enter its directory:

```bash
git clone https://github.com/hamidaka428/smart-checkout-ai.git
cd smart-checkout-ai
```

Create a virtual environment that can access system-installed Picamera2 packages:

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt
```

This command assumes your repository is named `smart-checkout-ai` under [@hamidaka428](https://github.com/hamidaka428). If you choose a different repository name, update the URL and directory name accordingly. Verify that the dependencies in `requirements.txt` are compatible with your Raspberry Pi OS and Python version.

## Usage

Run the camera and model check:

```bash
python test_ai.py
```

Start the checkout system:

```bash
python main.py
```

Place one product inside the camera's scanning area. Press the physical **Finish** button to complete checkout, or press `q` to exit the application.

## Collecting Training Data

The repository includes scripts for collecting labelled product images:

```bash
python collect_data.py
python auto_collect.py
```

Check each script's configuration and on-screen instructions before running it.

## Backend

The application uses a local PHP and MariaDB backend for product lookup and order storage. See [`backend/README.md`](backend/README.md) for backend setup instructions.

The API integration expects endpoints for product lookup and order saving. Configure the local web server and database before running the complete checkout workflow.

## Configuration

Important settings include GPIO pin assignments, the LCD I²C address, the confidence threshold, the camera-change threshold, the object-stability duration, and camera resolution. These settings are currently defined in the application code.

## Limitations and Future Improvements

- The first generation of a Bulgarian voice prompt requires an internet connection; generated audio is cached locally.
- The classifier recognises only the 15 product classes represented in its training data.
- Additional products require collecting labelled images and retraining the model.
- Potential improvements include model quantisation, support for multiple products in a frame, and moving configuration values into a separate configuration file.

## License

No license has been selected yet. Add a `LICENSE` file before presenting the repository as open source.
