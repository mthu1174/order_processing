# Order Processing Automation

This project is a desktop automation tool designed to streamline order processing workflows, daily reporting, and SAP integration. It features a graphical user interface built with CustomTkinter and utilizes Playwright for web automation and Win32COM for SAP GUI interactions.

## Features
- **Daily Reporting Automation**: Automates the generation and downloading of daily reports from Anchanto and formats them for PowerBI.
- **SAP Integration**: Automatically extracts data from SAP, creates deliveries (Confirm SO via VL10a), and manages file handling seamlessly.
- **E-commerce Sync**: Interacts with various e-commerce platforms (Shopee, Lazada, TikTok, GHN) for order and ticket management.
- **Modern GUI**: A sleek, dark-themed user interface to easily trigger workflows and configure settings.
- **Auto-Scheduling**: Includes a built-in scheduler to run specific automation tasks at regular intervals.

## Prerequisites
- Python 3.9+
- Windows OS (Required for SAP GUI Automation)
- Microsoft Edge or Chrome (for Playwright browser automation)
- SAP GUI installed and configured (if using SAP features)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/order-processing-automation.git
   cd order-processing-automation
   ```

2. **Create a virtual environment (Optional but recommended)**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install chromium edge
   ```

4. **Configuration**
   Before running the tool, create a `config.json` file in the root directory (based on `config_template.json` if available) and add your specific configurations, API keys, or paths.

## Usage
To start the application, run:
```bash
python main.py
```
Alternatively, you can use the provided batch files (`AutoRun.bat` or `Order Automation.bat`).

## Structure
- `main.py` / `gui/app.py`: The entry points for the Graphical User Interface.
- `automation/`: Contains the core logic for interacting with SAP, Anchanto, and e-commerce platforms.
- `gui/views/`: Contains the UI components and workflow definitions for different tabs.

## Security Note
Make sure **never** to commit your `config.json`, Excel data files, or any files containing real credentials. The `.gitignore` file is pre-configured to ignore these.
