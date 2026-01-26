# See No Evil: Semantic Context-Aware Privacy Risk Detection for AR

This repository contains the official implementation of the paper **"SEE NO EVIL: SEMANTIC CONTEXT-AWARE PRIVACY RISK DETECTION FOR AR"** (Accepted by **ICASSP 2026**).

**PrivAR** is a privacy-preserving framework designed for Augmented Reality (AR) systems. It addresses the "always-on" sensing privacy risks by leveraging Vision Language Models (VLMs) with Chain-of-Thought (CoT) prompting.

### Key Features:
* **Context-Aware Risk Detection:** Uses visual scene cues to infer potential sensitive information (e.g., identifying password notes in an office setting) rather than relying solely on object categories.
* **Privacy-Preserving Obfuscation:** Implements a "text obfuscation first" pipeline at the edge server using the EAST text detection model and a combination of Gaussian blur and elastic deformation. This prevents the VLM provider from accessing raw sensitive text.
* **Warning Interfaces:** Provides contextually-informed warning modes (Center-screen, Top-screen, Region Overlay) to enhance user privacy awareness in AR.

![System Architecture](https://github.com/jlliu2001/AR-Privacy-Detection/raw/main/docs/system_PrivAR.png)

## 🛠️ Prerequisites

### Unity Environment
* **Unity Version:** `2022.3.6f1`
* **Target Platform:** Android / iOS (AR Mobile)

### Python Environment
* **Python Version:** `3.7+`
* **Dependencies:**
    The core functionality (Edge Server processing and Cloud VLM inference) requires the following libraries.
    ```
    numpy
    opencv-python
    scipy
    openai
    requests
    torch
    torchvision
    shapely
    ```
## 🚀 Installation & Usage
### 1. Python Server Setup
Ensure your Python environment is ready and dependencies are installed.

1.1 Clone this repository.

1.2 Navigate to the python script directory.

1.3 Set up your OpenAI API Key in the configuration file or environment variable (for GPT-4o-mini inference).

1.4 Run the server script (e.g., python server.py).

### 2. Unity Project Setup
To integrate PrivAR into your Unity AR project, follow these steps:

#### Create New Project:

Open Unity Hub.

Create a new project using the AR Mobile template.


#### Import Scripts:

Navigate to your Unity project's assets folder: your_repo/Assets/MobileARTemplateAssets/

Create a new folder named Scripts.

Copy all .cs (C#) and .py (Python) files from this repository into: your_repo/Assets/MobileARTemplateAssets/Scripts/

#### Import Prefabs:

Navigate to your_repo/Assets/MobileARTemplateAssets/

Locate the existing Prefabs folder (or create it if it doesn't exist).

Copy the contents of the Prefabs folder from this repository into: your_repo/Assets/MobileARTemplateAssets/Prefabs/

#### Final Configuration:

Follow the detailed step-by-step configuration guide in ./docs/PrivAR_readme.pdf  to wire up the UI components and connect the AR Camera to the Python backend.

## 📂 Dataset
This repository includes the dataset collected for the PrivAR evaluation (Section 3.1 of the paper), covering:

4 Scenes: Office, Living room, Bedroom, buffet.

5 Information Types: ID cards, credit cards, password notes, screen text.


## 🔗 Citation
If you find this work useful in your research, please consider citing our paper:

